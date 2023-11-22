import json
from collections import defaultdict
from datetime import datetime

import quixstreams as qx
import os
import pandas as pd

client = qx.QuixStreamingClient()

forecast_consumer = client.get_topic_consumer(os.environ["forecast_data"])
printer_consumer = client.get_topic_consumer(os.environ["printer_data"])
alerts_producer = client.get_topic_producer(os.environ["alerts"])

# Alerts definitions
NO_ALERT = "no-alert"
UNDER_FORECAST = "under-forecast"
OVER_FORECAST = "over-forecast"
UNDER_NOW = "under-now"
OVER_NOW = "over-now"


def all_are_smaller(param1: list, param2: list):
    for i in range(len(param1)):
        if param1[i] >= param2[i]:
            return False

    return True


def all_are_higher(param1: list, param2: list):
    for i in range(len(param1)):
        if param1[i] <= param2[i]:
            return False

    return True


THRESHOLDS = {'ambient_temperature': (45, 55),
              'fluctuated_ambient_temperature': (45, 55),
              'bed_temperature': (105, 115),
              'hotend_temperature': (245, 255)}

alerts_triggered = defaultdict(dict)


def alert_triggered(stream_id, parameter):
    global alerts_triggered

    if stream_id in alerts_triggered:
        return alerts_triggered[stream_id].get(parameter, False)

    return False


def on_printer_dataframe_received(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    for parameter in ['bed_temperature', 'hotend_temperature', 'fluctuated_ambient_temperature']:
        # Check last value of df
        alert = None
        if df[parameter].iloc[-1] <= THRESHOLDS[parameter][0]:
            alert = {
                "status": UNDER_NOW,
                "parameter_name": parameter,
                "alert_timestamp": datetime.timestamp(pd.to_datetime(df['timestamp'].iloc[-1])) * 1e9,
                "alert_temperature": df[parameter].iloc[-1],
                "message": f"It looks like the value of '{parameter}' is already under the forecast range."
            }
        elif df[parameter].iloc[-1] >= THRESHOLDS[parameter][1]:
            alert = {
                "status": OVER_NOW,
                "parameter_name": parameter,
                "alert_timestamp": datetime.timestamp(pd.to_datetime(df['timestamp'].iloc[-1])) * 1e9,
                "alert_temperature": df[parameter].iloc[-1],
                "message": f"It looks like the value of '{parameter}' is already over the forecast range."
            }

        if alert is not None and not alert_triggered(stream_consumer.stream_id, parameter):
            stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                                 stream_consumer.properties.name)
            event = qx.EventData(alert["status"], pd.Timestamp.utcnow(), json.dumps(alert))
            stream_alerts_producer.events.publish(event)
            alerts_triggered[stream_consumer.stream_id][parameter] = True

        if alert is None and alert_triggered(stream_consumer.stream_id, parameter):
            stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                                 stream_consumer.properties.name)
            alert = {
                "status": NO_ALERT
            }
            event = qx.EventData(NO_ALERT, pd.Timestamp.utcnow(), json.dumps(alert))
            stream_alerts_producer.events.publish(event)
            alerts_triggered[stream_consumer.stream_id][parameter] = False


def get_or_create_alerts_stream(stream_id: str, stream_name: str):
    stream_alerts_producer = alerts_producer.get_or_create_stream(f"{stream_id}-alerts")

    if stream_id not in stream_alerts_producer.properties.parents:
        stream_alerts_producer.properties.parents.append(stream_id)

    if stream_name is not None:
        stream_alerts_producer.properties.name = f"{stream_name} - Alerts"

    stream_alerts_producer.events.add_definition(UNDER_NOW, "Under lower threshold now")
    stream_alerts_producer.events.add_definition(UNDER_FORECAST, "Under lower threshold in forecast")
    stream_alerts_producer.events.add_definition(NO_ALERT, "No alert")
    stream_alerts_producer.events.add_definition(OVER_FORECAST, "Over upper threshold in forecast")
    stream_alerts_producer.events.add_definition(OVER_NOW, "Over upper threshold now")
    return stream_alerts_producer


def on_printer_stream_received_handler(stream_consumer: qx.StreamConsumer):
    stream_consumer.timeseries.on_dataframe_received = on_printer_dataframe_received
    stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id, stream_consumer.properties.name)

    def on_stream_close(closed_stream_consumer: qx.StreamConsumer, end_type: qx.StreamEndType):
        global alerts_triggered

        stream_id = closed_stream_consumer.stream_id
        if stream_id in alerts_triggered:
            del alerts_triggered[stream_id]

        stream_alerts_producer.close()
        print(f"Closing stream '{closed_stream_consumer.properties.name}'")

    stream_consumer.on_stream_closed = on_stream_close


def get_time_left(timestamp: float):
    return datetime.timestamp(pd.to_datetime(timestamp)) - datetime.timestamp(pd.Timestamp.utcnow())


def on_forecast_dataframe_received(stream_consumer: qx.StreamConsumer, fcast: pd.DataFrame):
    parameter_name = "fluctuated_ambient_temperature"
    forecast_label = f"forecast_{parameter_name}"

    low_threshold = THRESHOLDS[parameter_name][0]
    high_threshold = THRESHOLDS[parameter_name][1]

    alert_status = None
    stream_id = stream_consumer.stream_id

    # Check if the value is already under the lower threshold or over the upper threshold
    # If so, the alert will be triggered by the printer data stream
    if not fcast[forecast_label].iloc[0] <= low_threshold and not fcast[forecast_label].iloc[0] >= high_threshold:
        # Find the time it takes for the forecasted values to hit the lower threshold of 45
        for i in range(len(fcast[forecast_label]) - 3):
            if all_are_smaller(list(fcast[forecast_label].iloc[i: i + 3]),
                               [low_threshold, low_threshold, low_threshold]):
                # In order to trigger the alert, the forecasted values need to be under
                # the lower threshold for 3 consecutive seconds
                alert_status = {
                    "status": UNDER_FORECAST,
                    "parameter_name": parameter_name,
                    "alert_temperature": fcast[forecast_label].iloc[i],
                    "alert_timestamp": datetime.timestamp(pd.to_datetime(fcast['timestamp'].iloc[i])) * 1e9,
                    "message": f"The value of '{parameter_name}' is expected to hit the lower threshold of "
                               f"{low_threshold} degrees in {get_time_left(fcast['timestamp'].iloc[i])}."
                }
                break
            elif all_are_higher(list(fcast[forecast_label].iloc[i: i + 3]),
                                [high_threshold, high_threshold, high_threshold]):
                # In order to trigger the alert, the forecasted values need to be under
                # the lower threshold for 3 consecutive seconds
                alert_status = {
                    "status": OVER_FORECAST,
                    "parameter_name": parameter_name,
                    "alert_temperature": fcast[forecast_label].iloc[i],
                    "alert_timestamp": datetime.timestamp(pd.to_datetime(fcast['timestamp'].iloc[i])) * 1e9,
                    "message": f"The value of '{parameter_name}' is expected to hit the higher threshold of "
                               f"{high_threshold} degrees in {get_time_left(fcast['timestamp'].iloc[i])}."
                }
                break
        else:
            alert_status = {
                "status": NO_ALERT,
                "parameter_name": parameter_name,
                "message": f"The value of '{parameter_name}' is not expected to hit the lower threshold of "
                           f"{low_threshold} degrees within the forecast range."
            }
    else:
        # If the value is already under the lower threshold, or over the upper threshold,
        return

    if alert_status["status"] in [UNDER_NOW, UNDER_FORECAST, OVER_NOW, OVER_FORECAST]:
        print(f"{stream_consumer.properties.name}: Triggering alert...")
        stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                             stream_consumer.properties.name)

        event = qx.EventData(alert_status["status"], pd.Timestamp.utcnow(), json.dumps(alert_status))
        # Tag the data with the printer name for joining operations later
        event.add_tag("TAG__printer", stream_consumer.properties.name)
        stream_alerts_producer.events.publish(event)
        alerts_triggered[stream_id][parameter_name] = True

    elif alert_status["status"] == "noalert" and alert_triggered(stream_id, parameter_name):
        # If it was triggered, and now it's not, send a "noalert" event
        print(f"{stream_consumer.properties.name}: Setting to no alert...")
        stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                             stream_consumer.properties.name)
        event = qx.EventData(alert_status["status"], pd.Timestamp.utcnow(), json.dumps(alert_status))
        stream_alerts_producer.events.publish(event)
        alerts_triggered[stream_id][parameter_name] = False


def on_forecast_stream_received_handler(stream_consumer: qx.StreamConsumer):
    stream_consumer.timeseries.on_dataframe_received = on_forecast_dataframe_received
    stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id, stream_consumer.properties.name)

    def on_stream_close(closed_stream_consumer: qx.StreamConsumer, end_type: qx.StreamEndType):
        global alerts_triggered

        stream_id = closed_stream_consumer.stream_id
        if stream_id in alerts_triggered:
            del alerts_triggered[stream_id]

        stream_alerts_producer.close()
        print(f"Closing stream '{closed_stream_consumer.properties.name}'")

    stream_consumer.on_stream_closed = on_stream_close


# subscribe to new streams being received
printer_consumer.on_stream_received = on_printer_stream_received_handler
forecast_consumer.on_stream_received = on_forecast_stream_received_handler

print("Listening to streams. Press CTRL-C to exit.")

# Handle termination signals and provide a graceful exit
qx.App.run()
