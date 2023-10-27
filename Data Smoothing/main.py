import quixstreams as qx
import pandas as pd
import os

# Customize Pandas display options for debugging
pd.set_option('display.max_rows', None)        # Display all rows
pd.set_option('display.max_columns', None)     # Display all columns
pd.set_option('display.max_colwidth', 1000)    # Set maximum width for columns
pd.set_option('display.float_format', '{:.2f}'.format)  # Display numeric values with 2 decimal places
pd.set_option('display.nan', 'NaN')            # Display NaN values as 'NaN'
pd.set_option('display.width', 1000)          # Set display width


# Quix injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient()

# Use Input / Output topics to stream data in or out of your service
consumer_topic = client.get_topic_consumer(os.environ["input"])
producer_topic = client.get_topic_producer(os.environ["output"])

def printer(label, df):
    print(label)
    print(df)
    print(f"end--{label}")

def smooth_data(df):
    printer("1", df)
    # Convert the timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')

    # Set the timestamp as the index
    df.set_index('timestamp', inplace=True)
    printer("2", df)

    # # Resample the data to 1 minute intervals and forward fill any missing data
    # df = df.resample('1S').ffill()
    # printer("3", df)

    # # Use a rolling window of 3 minutes and calculate the mean
    # df_smooth = df.rolling('3S').mean()
    # printer("4", df_smooth)

    # # Drop the rows with NaN values that were created by the rolling window
    # df_smooth = df_smooth.dropna()
    # printer("5", df_smooth)

    # Resample the data to 1 second intervals and forward fill any missing data
    df = df.resample('1S').ffill()
    # Use a rolling window of 3 seconds and calculate the mean
    df_smooth = df.rolling('3S').mean()
    printer("4", df_smooth)

    # Resample the data to 3-second intervals
    df_smooth = df_smooth.resample('3S').mean()
    printer("5", df_smooth)
    
    if len(df_smooth) == 0:
        print("No valid data after smoothing.")

    return df_smooth

def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):

    # Transform data frame here in this method. You can filter data or add new features.
    # Pass modified data frame to output stream using stream producer.

    # transform the data by applying the smoothing algorithm
    df_smooth = smooth_data(df)

    # Print the smoothed data
    print(df_smooth)

    # create a stream on the output topic using the streamid of the incoming stream
    #stream_producer = producer_topic.get_or_create_stream(stream_id = stream_consumer.stream_id)

    # publish the smoothed data to the putput topic
    #stream_producer.timeseries.buffer.publish(df_smooth)

def on_stream_received_handler(stream_consumer: qx.StreamConsumer):
    # subscribe to new DataFrames being received
    # if you aren't familiar with DataFrames there are other callbacks available
    # refer to the docs here: https://docs.quix.io/sdk/subscribe.html
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_received_handler

# subscribe to new streams being received
consumer_topic.on_stream_received = on_stream_received_handler

print("Listening to streams. Press CTRL-C to exit.")

# Handle termination signals and provide a graceful exit
qx.App.run()
