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

# Assigning environ vars to local variables
topic_input = os.environ["input"]
topic_output = os.environ["output"]
topic_alerts = os.environ["output_alerts"]
parameter_name = os.environ["parameter_name"] if "parameter_name" in os.environ else "fluctuated_ambient_temperature"

# TODO: define window type and window val
window_type = 'Number of Observations'  # os.environ["WindowType"] 'Number of Observations' OR 'Time Period'
window_value = 7200  # os.environ["WindowValue"] # The 5-minute sample for forecasts
# Set Window var based on window type
if window_type == 'Number of Observations':
    window = int(window_value)
elif window_type == 'Time Period':
    window = pd.Timedelta(str(window_value))
else:
    window = None

debug = os.environ["debug"] == 1 if "debug" in os.environ else False
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO)


# Callback called for each incoming stream
def read_stream(stream_consumer: qx.StreamConsumer):
    # Create a new stream to output data
    stream_producer = producer_topic.create_stream(f"{stream_consumer.stream_id}-forecast-{topic_output}")
    stream_producer.properties.parents.append(stream_consumer.stream_id)

    stream_alerts_producer = producer_topic.create_stream(f"{stream_consumer.stream_id}-forecast-{topic_alerts}")
    stream_alerts_producer.properties.parents.append(stream_consumer.stream_id)

    # React to new data received from input topic.
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_handler

    # When input stream closes, we close output stream as well.
    def on_stream_close(closed_stream_consumer: qx.StreamConsumer, end_type: qx.StreamEndType):
        stream_producer.close()
        stream_alerts_producer.close()
        logging.info("Streams closed:" + stream_producer.stream_id + " , " + stream_alerts_producer.stream_id)

    stream_consumer.on_stream_closed = on_stream_close


def generate_forecast(df):
    global window_value

    forecast_length = 14400  # 4 hours into the future
    window_range = 1300  # Window range used for smoothing (not forecasting), 36 secs
    smooth_label = "smoothed_" + str(parameter_name)
    forecast_label = "forecast_" + smooth_label

    # Make sure that the 'original_timestamp' column is datetime
    df['original_timestamp'] = pd.to_datetime(df['original_timestamp'])
    # Set the 'timestamp' column as the index
    df.set_index(pd.DatetimeIndex(df['original_timestamp']), inplace=True)

    # DEBUG LINE make sure that the data looks OK before smoothing
    logging.debug(f"PRE-SMOOTHED DATA:\n{df[parameter_name].tail(5)}")

    # Backfill NaNs with the first non-NaN value
    df[smooth_label] = df[parameter_name].rolling(window_range).mean()
    df[smooth_label] = df[smooth_label].bfill()
    data_smoov = df[smooth_label]

    # DEBUG LINE  make sure that the data looks OK after smoothing
    logging.debug(f"SMOOTHED DATA:\n{data_smoov.tail(1)}")

    forecast_input = data_smoov

    # TODO: Don't understand why NaNs need to be filled, why are there NaNs?!... previous "bfill" on line 33 should have worked.
    forecast_input = forecast_input.fillna(0)

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
    # Create a timestamp for the forecasted values
    forecast_timestamp = pd.date_range(start=forecast_input.index[-1], periods=forecast_length, freq='S')

    # Add the forecasted timestamps to the DataFrame - these are in the future
    fcast['forecast_timestamp'] = forecast_timestamp

    # Adding the timestamp that Quix needs to present in the df
    n = len(fcast)
    # Get the current time
    now = datetime.now()
    # Create a date range starting from 'now', for 'n' periods, with a frequency of 1 millisecond
    ntimestamps = pd.date_range(start=now, periods=n, freq='ms')
    # Add the timestamps to the DataFrame
    fcast['timestamp'] = ntimestamps

    lthreshold = 45
    alertstatus = {"status": "unknown", "message": "empty"}

    # Find the time it takes for the forecasted values to hit the lower threshold of 45
    for i in range(len(fcast[forecast_label])):
        if fcast[forecast_label].iloc[i] <= lthreshold and i == 0:
            alertstatus["status"] = "under-now"
            alertstatus["message"] = f"It looks like the value of '{smooth_label}' is already under the forecast range."
            logging.info(f"{alertstatus['status']}: {alertstatus['message']}")
            break
        elif fcast[forecast_label].iloc[i] <= lthreshold:
            alertstatus["status"] = "under-fcast"
            alertstatus[
                "message"] = f"The value of '{smooth_label}' is expected to hit the lower threshold of {lthreshold} degrees in {i} seconds ({i / 3600} hours)."
            logging.info(f"{alertstatus['status']}: {alertstatus['message']}")
            break
    else:
        alertstatus["status"] = "noalert"
        alertstatus[
            "message"] = f"The value of '{smooth_label}' is not expected to hit the lower threshold of {lthreshold} degrees within the forecast range of {forecast_length} seconds ({int(forecast_length / 3600)} hours)."
        print(f"{alertstatus['status']}: {alertstatus['message']}")
    return fcast, alertstatus


df_window = pd.DataFrame()
storage = qx.LocalFileStorage()


def on_dataframe_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    global df_window

    if parameter_name not in df.columns:
        return

    # DEBUG LINE
    logging.debug(f"Received:\n{df}")
    # Append latest data to df_window
    df_window = pd.concat([df_window, df[["timestamp", "original_timestamp", parameter_name]]])

    # Save to state before trimming
    storage.set("df_window", df_window.to_dict())

    # Trim out the (now) too old data in the df_window
    if window is int:
        df_window = df_window.iloc[-window:, :]
    if window is pd.Timedelta:
        min_date = df_window['timestamp'].iloc[-1] - window.delta
        df_window = df_window[df_window['timestamp'] > min_date]

    # DEBUG LINE
    logging.debug(f"Loaded from state:\n{df_window['fluctuated_ambient_temperature'].tail(1)}")

    # Append latest data to df_window

    # PERFORM A OPERATION ON THE WINDOW
    # Check if df_window has at least windowval number of rows
    if len(df_window) >= window_value:
        # Generate forecast
        forecast, alert_status = generate_forecast(df)
        status = alert_status["status"]
        message = alert_status["message"]
        logging.info(f"Forecast generated — last 5 rows:\n {forecast.tail(5)}")
        stream_producer = producer_topic.get_or_create_stream(f"{stream_consumer.stream_id}-forecast-{topic_output}")
        stream_producer.timeseries.buffer.publish(forecast)

        if status in ["under-now", "under-fcast"]:
            logging.info("Triggering alert...")
            alertdf = pd.DataFrame([alert_status])
            # Get current date and time
            now = datetime.now()
            # Add new column with current timestamp
            alertdf['timestamp'] = now
            logging.debug(f"Triggering alert...{alertdf}")
            stream_alerts_producer = producer_topic.get_or_create_stream(
                f"{stream_consumer.stream_id}-forecast-{topic_alerts}")
            stream_alerts_producer.timeseries.buffer.publish(alertdf)

    else:
        logging.info(
            f"Not enough data for a forecast yet ({len(df_window)} seconds, forecast needs {window_value} seconds)")


if __name__ == "__main__":
    # Alternatively, you can always pass an SDK token manually as an argument.
    client = qx.QuixStreamingClient()

    # Change consumer group to a different constant if you want to run model locally.
    print("Opening input and output topics")

    if debug:
        consumer_topic = client.get_topic_consumer(topic_input, "forecast-" + parameter_name,
                                                   auto_offset_reset=qx.AutoOffsetReset.Earliest)
    else:
        consumer_topic = client.get_topic_consumer(topic_input, "forecast-" + parameter_name)

    producer_topic = client.get_topic_producer(topic_output)
    producer_alertstopic = client.get_topic_producer(topic_alerts)

    # Hook up events before initiating read to avoid losing out on any data
    consumer_topic.on_stream_received = read_stream

    # Hook up to termination signal (for docker image) and CTRL-C
    print("Listening to streams. Press CTRL-C to exit.")

    # Handle graceful exit of the model.
    qx.App.run()
