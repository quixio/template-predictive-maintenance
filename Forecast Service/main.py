import json
from collections import defaultdict

import quixstreams as qx
import os

from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

import logging
import sys

NO_ALERT = "no-alert"
UNDER_FORECAST = "under-forecast"
OVER_FORECAST = "over-forecast"
UNDER_NOW = "under-now"
OVER_NOW = "over-now"

# Assigning environ vars to local variables
topic_input = os.environ["input"]
topic_output = os.environ["output"]
topic_alerts = os.environ["output_alerts"]
parameter_name = os.environ["parameter_name"] if "parameter_name" in os.environ else "fluctuated_ambient_temperature"

window_type_env = os.environ["window_type"] if "window_type" in os.environ else "1"
window_type = 'Number of Observations' if window_type_env == 1 else "Time Period"
window_value = int(os.environ["window_value"])

if window_type == 'Number of Observations':
    window = int(window_value)
elif window_type == 'Time Period':
    window = pd.Timedelta(str(window_value))
else:
    window = None

debug = os.environ["debug"] == "1" if "debug" in os.environ else False
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO)


# Callback called for each incoming stream
def read_stream(stream_consumer: qx.StreamConsumer):
    # Create a new stream to output data
    stream_producer = get_or_create_forecast_stream(stream_consumer.stream_id, stream_consumer.properties.name)
    logging.info(f"Created stream '{stream_producer.stream_id}' ({stream_consumer.properties.name})")

    stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id, stream_consumer.properties.name)
    logging.info(f"Created stream '{stream_alerts_producer.stream_id}' ({stream_consumer.properties.name})")

    # React to new data received from input topic.
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_handler

    # When input stream closes, we close output stream as well.
    def on_stream_close(closed_stream_consumer: qx.StreamConsumer, end_type: qx.StreamEndType):
        global windows, alerts_triggered

        stream_id = closed_stream_consumer.stream_id
        if stream_id in windows:
            del windows[stream_id]
        else:
            logging.warning(f"Stream {stream_id} ({stream_consumer.properties.name}) was not found in windows dict.")

        if stream_id in alerts_triggered:
            del alerts_triggered[stream_id]
        else:
            logging.warning(
                f"Stream {stream_id} ({stream_consumer.properties.name}) was not found in alerts dict.")

        stream_producer.close()
        stream_alerts_producer.close()
        logging.info(f"Closing stream '{stream_consumer.properties.name}'")
        logging.info("Streams closed:" + stream_producer.stream_id + " , " + stream_alerts_producer.stream_id)

    stream_consumer.on_stream_closed = on_stream_close


def get_or_create_forecast_stream(stream_id: str, stream_name: str):
    stream_producer = producer_topic.get_or_create_stream(f"{stream_id}-forecast")

    if stream_id not in stream_producer.properties.parents:
        stream_producer.properties.parents.append(stream_id)

    if stream_name is not None:
        stream_producer.properties.name = f"{stream_name} - Forecast"

    stream_producer.timeseries.add_definition("forecast_" + parameter_name, "Forecasted " + parameter_name)
    return stream_producer


def get_or_create_alerts_stream(stream_id: str, stream_name: str):
    stream_alerts_producer = producer_alerts_topic.get_or_create_stream(f"{stream_id}-alerts")

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


def generate_forecast(df, printer_name):
    global window_value

    forecast_length = int(os.environ['forecast_length'])
    forecast_unit = os.environ['forecast_unit']
    forecast_label = "forecast_" + str(parameter_name)

    # Set the 'timestamp' column as the index
    if 'original_timestamp' not in df.columns:
        timestamp_column_name = 'timestamp'
    else:
        timestamp_column_name = 'original_timestamp'
        df[timestamp_column_name] = pd.to_datetime(df[timestamp_column_name])

    df.set_index(pd.DatetimeIndex(df[timestamp_column_name]), inplace=True)

    forecast_input = df[parameter_name]

    # Define the degree of the polynomial regression model
    degree = 2
    # Create a polynomial regression model
    model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
    # Fit the model to the data
    model.fit(np.array(range(len(forecast_input))).reshape(-1, 1), forecast_input)
    # Forecast the future values
    forecast_array = np.array(range(len(forecast_input), len(forecast_input) + forecast_length)).reshape(-1, 1)
    forecast_values = model.predict(forecast_array)
    # Create a DataFrame for the forecast
    fcast = pd.DataFrame(forecast_values, columns=[forecast_label])
    # Tag the data with the printer name for joining operations later
    fcast["TAG__printer"] = printer_name

    # Create a timestamp for the forecasted values
    forecast_timestamp = pd.date_range(start=forecast_input.index[-1], periods=forecast_length, freq=forecast_unit)

    # Add the forecasted timestamps to the DataFrame - these are in the future
    fcast['timestamp'] = forecast_timestamp

    lthreshold = THRESHOLDS[parameter_name][0]
    hthreshold = THRESHOLDS[parameter_name][1]

    if fcast[forecast_label].iloc[0] <= lthreshold:
        alertstatus = {
            "status": UNDER_NOW,
            "parameter_name": parameter_name,
            "alert_temperature": fcast[forecast_label].iloc[0],
            "alert_timestamp": datetime.timestamp(fcast['timestamp'].iloc[0]) * 1e9,
            "message": f"It looks like the value of '{parameter_name}' is already under the forecast range."
        }
    elif fcast[forecast_label].iloc[0] >= hthreshold:
        alertstatus = {
            "status": OVER_NOW,
            "parameter_name": parameter_name,
            "alert_temperature": fcast[forecast_label].iloc[0],
            "alert_timestamp": datetime.timestamp(fcast['timestamp'].iloc[0]) * 1e9,
            "message": f"It looks like the value of '{parameter_name}' is already over the forecast range."
        }
    else:
        # Find the time it takes for the forecasted values to hit the lower threshold of 45
        for i in range(len(fcast[forecast_label]) - 3):
            if all_are_smaller(list(fcast[forecast_label].iloc[i: i + 3]), [lthreshold, lthreshold, lthreshold]):
                # In order to trigger the alert, the forecasted values need to be under
                # the lower threshold for 3 consecutive seconds
                alertstatus = {
                    "status": UNDER_FORECAST,
                    "parameter_name": parameter_name,
                    "alert_temperature": fcast[forecast_label].iloc[i],
                    "alert_timestamp": datetime.timestamp(fcast['timestamp'].iloc[i]) * 1e9,
                    "message": f"The value of '{parameter_name}' is expected to hit the lower threshold of "
                               f"{lthreshold} degrees in {i}  {forecast_unit}."
                }
                break
            elif all_are_higher(list(fcast[forecast_label].iloc[i: i + 3]), [hthreshold, hthreshold, hthreshold]):
                # In order to trigger the alert, the forecasted values need to be under
                # the lower threshold for 3 consecutive seconds
                alertstatus = {
                    "status": OVER_FORECAST,
                    "parameter_name": parameter_name,
                    "alert_temperature": fcast[forecast_label].iloc[i],
                    "alert_timestamp": datetime.timestamp(fcast['timestamp'].iloc[i]) * 1e9,
                    "message": f"The value of '{parameter_name}' is expected to hit the higher threshold of "
                               f"{hthreshold} degrees in {i}  {forecast_unit}."
                }

                break
        else:
            alertstatus = {
                "status": NO_ALERT,
                "parameter_name": parameter_name,
                "message": f"The value of '{parameter_name}' is not expected to hit the lower threshold of "
                           f"{lthreshold} degrees within the forecast range of {forecast_length} {forecast_unit}."
            }

    logging.debug(f"{printer_name}:{alertstatus['status']}: {alertstatus['message']}")

    # Print first and last entries of df and the forecast

    first_timestamp = pd.to_datetime(df[timestamp_column_name].iloc[0])
    last_timestamp = pd.to_datetime(df[timestamp_column_name].iloc[-1])
    first_temperature = df[parameter_name].iloc[0]
    last_temperature = df[parameter_name].iloc[-1]

    first_forecast_timestamp = fcast['timestamp'].iloc[0]
    last_forecast_timestamp = fcast['timestamp'].iloc[-1]
    first_forecast_temperature = fcast[forecast_label].iloc[0]
    last_forecast_temperature = fcast[forecast_label].iloc[-1]

    logging.info("#######################################################")
    logging.info(f"{printer_name : 55^ }")
    logging.info("Current first ", first_timestamp, first_temperature)
    logging.info("Current last  ", last_timestamp, last_temperature)
    logging.info("Forecast first", first_forecast_timestamp, first_forecast_temperature)
    logging.info("Forecast last ", last_forecast_timestamp, last_forecast_temperature)
    logging.info("#######################################################")

    return fcast, alertstatus


windows = {}
alerts_triggered = defaultdict(dict)
storage = qx.LocalFileStorage()


def alert_triggered(stream_id, parameter):
    global alerts_triggered

    if stream_id in alerts_triggered:
        return alerts_triggered[stream_id].get(parameter, False)

    return False


def check_other_parameters(stream_consumer, df):
    for parameter in ['bed_temperature', 'hotend_temperature']:
        # Check last value of df
        alert = None
        if df[parameter].iloc[-1] <= THRESHOLDS[parameter][0]:
            alert = {
                "status": UNDER_NOW,
                "parameter_name": parameter_name,
                "alert_timestamp": datetime.timestamp(df['timestamp'].iloc[-1]) * 1e9,
                "alert_temperature": df[parameter].iloc[-1],
                "message": f"It looks like the value of '{parameter}' is already under the forecast range."
            }
        elif df[parameter].iloc[-1] >= THRESHOLDS[parameter][1]:
            alert = {
                "status": OVER_NOW,
                "parameter_name": parameter_name,
                "alert_timestamp": datetime.timestamp(df['timestamp'].iloc[-1]) * 1e9,
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


def on_dataframe_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    global windows, alerts_triggered

    if parameter_name not in df.columns:
        return

    stream_id = stream_consumer.stream_id
    if stream_id not in windows:
        windows[stream_id] = pd.DataFrame()

    df_window = windows[stream_id]

    # Append latest data to df_window
    columns = ["timestamp", parameter_name]
    if 'original_timestamp' in df.columns:
        columns.append('original_timestamp')

    df_window = pd.concat([df_window, df[columns]])

    # Store in memory for each printer
    windows[stream_id] = df_window

    # Save to state before trimming
    storage.set("df_window", df_window.to_dict())

    # Trim out the (now) too old data in the df_window
    if window is int:
        df_window = df_window.iloc[-window:, :]
    if window is pd.Timedelta:
        min_date = df_window['timestamp'].iloc[-1] - window.delta
        df_window = df_window[df_window['timestamp'] > min_date]

    # PERFORM A OPERATION ON THE WINDOW
    # Check if df_window has at least windowval number of rows
    if len(df_window) >= window_value:
        # Last data point timestamp
        last_timestamp = df_window['timestamp'].iloc[-1] / 1e9

        # Warn if we are processing data that was generated more than 1 minute ago
        elapsed_time = datetime.now().timestamp() - last_timestamp
        if elapsed_time > 120:
            logging.warning(
                f"{stream_consumer.properties.name}: Processing data that was generated {elapsed_time} seconds ago")

        # Generate forecast
        start = datetime.now().timestamp()
        forecast, alert_status = generate_forecast(df_window, stream_consumer.properties.name)
        status = alert_status["status"]
        stream_producer = get_or_create_forecast_stream(stream_consumer.stream_id, stream_consumer.properties.name)
        stream_producer.timeseries.buffer.publish(forecast)
        logging.debug(
            f"{stream_consumer.properties.name}: Took {datetime.now().timestamp() - start} seconds to calculate the forecast")

        if status in [UNDER_NOW, UNDER_FORECAST, OVER_NOW, OVER_FORECAST]:
            logging.info(f"{stream_consumer.properties.name}: Triggering alert...")
            stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                                 stream_consumer.properties.name)

            event = qx.EventData(alert_status["status"], pd.Timestamp.utcnow(), json.dumps(alert_status))
            # Tag the data with the printer name for joining operations later
            event.add_tag("TAG__printer", stream_consumer.properties.name)
            stream_alerts_producer.events.publish(event)
            alerts_triggered[stream_id][parameter_name] = True

        elif status == "noalert" and alert_triggered(stream_id, parameter_name):
            # If it was triggered, and now it's not, send a "noalert" event
            logging.info(f"{stream_consumer.properties.name}: Setting to no alert...")
            stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                                 stream_consumer.properties.name)
            event = qx.EventData(alert_status["status"], pd.Timestamp.utcnow(), json.dumps(alert_status))
            stream_alerts_producer.events.publish(event)
            alerts_triggered[stream_id][parameter_name] = False

    else:
        logging.info(f"{stream_consumer.properties.name}: Not enough data for a forecast yet"
                     f" ({len(df_window)} {os.environ['forecast_unit']},"
                     f" forecast needs {window_value} {os.environ['forecast_unit']})")

    check_other_parameters(stream_consumer, df)

    send_fake_alert(stream_consumer, df)


# region Fake alert
# TODO: To be removed
force_alert = 0


def send_fake_alert(stream_consumer, df: pd.DataFrame):
    # For debug purposes
    global force_alert
    force_alert += 1
    fake_alert = {
        "parameter_name": "fluctuated_ambient_temperature",
        "message": "fake alert",
    }
    if force_alert < 10:
        fake_alert["status"] = UNDER_FORECAST
        fake_alert["alert_timestamp"] = datetime.timestamp(datetime.utcnow() + timedelta(minutes=10)) * 1e9
        fake_alert["alert_temperature"] = 44.9
    if force_alert < 20:
        fake_alert["status"] = UNDER_NOW
        fake_alert["alert_timestamp"] = int(df["timestamp"].iloc[-1])
        fake_alert["alert_temperature"] = 44.9
    else:
        fake_alert["status"] = NO_ALERT
        if force_alert > 30:
            force_alert = 0

    force_alert += 1
    stream_alerts_producer = get_or_create_alerts_stream(stream_consumer.stream_id,
                                                         stream_consumer.properties.name)
    event = qx.EventData(fake_alert["status"], pd.Timestamp.utcnow(), json.dumps(fake_alert))
    stream_alerts_producer.events.publish(event)


# endregion


if __name__ == "__main__":
    # Alternatively, you can always pass an SDK token manually as an argument.
    client = qx.QuixStreamingClient()

    # Change consumer group to a different constant if you want to run model locally.
    logging.info("Opening input and output topics")

    if debug:
        consumer_topic = client.get_topic_consumer(topic_input, "forecast-" + parameter_name,
                                                   auto_offset_reset=qx.AutoOffsetReset.Earliest)
    else:
        consumer_topic = client.get_topic_consumer(topic_input, "forecast-" + parameter_name)

    producer_topic = client.get_topic_producer(topic_output)
    producer_alerts_topic = client.get_topic_producer(topic_alerts)

    # Hook up events before initiating read to avoid losing out on any data
    consumer_topic.on_stream_received = read_stream

    # Hook up to termination signal (for docker image) and CTRL-C
    logging.info("Listening to streams. Press CTRL-C to exit.")

    # Handle graceful exit of the model.
    qx.App.run()
