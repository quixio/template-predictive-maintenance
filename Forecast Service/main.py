import quixstreams as qx
import os
import pandas as pd
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
import numpy as np

client = qx.QuixStreamingClient()

topic_consumer = client.get_topic_consumer(os.environ["input"])
topic_producer = client.get_topic_producer(os.environ["output"])

# Configuration
headsortails = 'head'  # Switch to experiment with generating the forecast from the first chunk of data (head) vs the last chunk of data (tail)
seasonalrange = 62
forecastlength = 14400
windowrange = 1300
segmentsize = 7200  # use the last 5 minutes for our forecast

seasonal_periods = seasonalrange  # Adjust this value as needed

# We will store all the data in a single DataFrame
all_df = pd.DataFrame()


def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    global all_df

    # Convert the 'timestamp' column to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Set the 'timestamp' column as the index
    df.set_index(pd.DatetimeIndex(df['timestamp'], freq='S'), inplace=True)

    all_df = pd.concat([all_df, df], ignore_index=True)

    print("-------------------------")
    print(df)
    print("-------------------------")
    print(all_df)
    print("-------------------------")


    data = all_df['fluctuated_ambient_temperature']
    data_fluct = all_df['fluctuated_ambient_temperature']
    # Backfill NaNs with the first non-NaN value
    #df['smoothed_fluctuated_ambient_temperature'] = all_df['fluctuated_ambient_temperature'].rolling(windowrange).mean()
    #df['smoothed_fluctuated_ambient_temperature'] = df['smoothed_fluctuated_ambient_temperature'].bfill()
    data_smoov = data['smoothed_fluctuated_ambient_temperature']

    if headsortails == 'tail':
        tail_range = int(len(data) * 0.5)
        # tailrange = 300
        print(tail_range)
        data_smoov = data_smoov.tail(tail_range)
        # data_smoov = data_smoov[:-5]
        data_fluct = data_fluct.tail(tail_range)
    else:
        headrange = int(len(data) * 0.65)  # Start the forecast in just after the middle of the data for testing
        data_smoov = data_smoov.head(headrange)
        data_smoov = data_smoov.tail(segmentsize)

        data_fluct = data_fluct.head(headrange)
        data_fluct = data_fluct.tail(segmentsize)
        print(headrange)

    print(data_smoov)
    forecasttarget = data_smoov

    # Define the degree of the polynomial regression model
    degree = 2

    # Create a polynomial regression model
    model = make_pipeline(PolynomialFeatures(degree), LinearRegression())

    # Fit the model to the data
    model.fit(np.array(range(len(forecasttarget))).reshape(-1, 1), forecasttarget)

    # Forecast the future values
    forecast_values = model.predict(
        np.array(range(len(forecasttarget), len(forecasttarget) + forecastlength)).reshape(-1, 1))

    # Create a DataFrame for the forecast
    fcast_upper = pd.DataFrame(forecast_values, columns=['Upper range forecast'])

    # Create a timestamp for the forecasted values
    forecast_timestamp = pd.date_range(start=forecasttarget.index[-1], periods=forecastlength, freq='S')

    # Add the timestamp to the DataFrame
    fcast_upper['timestamp'] = forecast_timestamp

    lthreshold = 45
    # Find the time it takes for the forecasted values to hit the lower threshold of 105
    for i in range(len(fcast_upper['Upper range forecast'])):
        if fcast_upper['Upper range forecast'].iloc[i] <= lthreshold and i == 0:
            print("It looks like the value of 'data_smoov' is already under the forecast range.")
            break
        elif fcast_upper['Upper range forecast'].iloc[i] <= lthreshold:
            print(
                f"The value of 'data_smoov' is expected to hit the lower threshold of {lthreshold} degrees in {i} seconds ({i / 3600} hours).")
            break
    else:
        print(
            f"The value of 'data_smoov' is not expected to hit the lower threshold of {lthreshold} degrees within the forecast range of {forecastlength} seconds ({int(forecastlength / 3600)} hours).")

    # Transform data frame here in this method. You can filter data or add new features.
    # Pass modified data frame to output stream using stream producer.
    # Set the output stream id to the same as the input stream or change it,
    # if you grouped or merged data with different key.
    stream_producer = topic_producer.get_or_create_stream(stream_id=stream_consumer.stream_id)
    stream_producer.timeseries.buffer.publish(fcast_upper)


def on_stream_received_handler(stream_consumer: qx.StreamConsumer):
    # subscribe to new DataFrames being received
    # if you aren't familiar with DataFrames there are other callbacks available
    # refer to the docs here: https://docs.quix.io/sdk/subscribe.html
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_received_handler


# subscribe to new streams being received
topic_consumer.on_stream_received = on_stream_received_handler

print("Listening to streams. Press CTRL-C to exit.")

# Handle termination signals and provide a graceful exit
qx.App.run()
