import quixstreams as qx

import logging
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

# Assigning environ vars to local variables
topic_input = os.environ["input"]
topic_output = os.environ["output"]
parameter_name = os.environ["parameter_name"] if "parameter_name" in os.environ else "fluctuated_ambient_temperature"
forecast_label = str(parameter_name)

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

    # React to new data received from input topic.
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_handler

    # When input stream closes, we close output stream as well.
    def on_stream_close(closed_stream_consumer: qx.StreamConsumer, end_type: qx.StreamEndType):
        global windows

        stream_id = closed_stream_consumer.stream_id
        if stream_id in windows:
            del windows[stream_id]
        else:
            logging.warning(f"Stream {stream_id} ({stream_consumer.properties.name}) was not found in windows dict.")

        stream_producer.close()
        logging.info(f"Closing stream '{stream_consumer.properties.name}'")

    stream_consumer.on_stream_closed = on_stream_close


def get_or_create_forecast_stream(stream_id: str, stream_name: str):
    stream_producer = producer_topic.get_or_create_stream(f"{stream_id}-forecast")

    if stream_id not in stream_producer.properties.parents:
        stream_producer.properties.parents.append(stream_id)

    if stream_name is not None:
        stream_producer.properties.name = f"{stream_name} - Forecast"

    stream_producer.timeseries.add_definition(forecast_label, "Forecasted " + parameter_name)
    return stream_producer


def generate_forecast(df, printer_name):
    global window_value

    forecast_length = int(os.environ['forecast_length'])
    forecast_unit = os.environ['forecast_unit']

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
    forecast_timestamp = pd.date_range(start=forecast_input.index[-1] + pd.Timedelta(value=1, unit=forecast_unit),
                                       periods=forecast_length, freq=forecast_unit)

    # Add the forecasted timestamps to the DataFrame - these are in the future
    fcast['timestamp'] = forecast_timestamp

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
    logging.info(f"{printer_name : ^55}")
    logging.info(f"Current first  {first_timestamp} {first_temperature}")
    logging.info(f"Current last   {last_timestamp} {last_temperature}")
    logging.info(f"Forecast first {first_forecast_timestamp} {first_forecast_temperature}")
    logging.info(f"Forecast last  {last_forecast_timestamp} {last_forecast_temperature}")
    logging.info("#######################################################")

    return fcast


windows = {}
storage = qx.LocalFileStorage()


def on_dataframe_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    global windows

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
        forecast = generate_forecast(df_window, stream_consumer.properties.name or "Unknown")
        stream_producer = get_or_create_forecast_stream(stream_consumer.stream_id, stream_consumer.properties.name)
        stream_producer.timeseries.buffer.publish(forecast)
        logging.debug(
            f"{stream_consumer.properties.name}: Took {datetime.now().timestamp() - start} seconds to calculate the forecast")


    else:
        logging.info(f"{stream_consumer.properties.name}: Not enough data for a forecast yet"
                     f" ({len(df_window)} {os.environ['forecast_unit']},"
                     f" forecast needs {window_value} {os.environ['forecast_unit']})")


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

    # Hook up events before initiating read to avoid losing out on any data
    consumer_topic.on_stream_received = read_stream

    # Hook up to termination signal (for docker image) and CTRL-C
    logging.info("Listening to streams. Press CTRL-C to exit.")

    # Handle graceful exit of the model.
    qx.App.run()
