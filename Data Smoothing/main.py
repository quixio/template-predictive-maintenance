import quixstreams as qx
import pandas as pd
import os

# Quix injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient()

# Use Input / Output topics to stream data in or out of your service
consumer_topic = client.get_topic_consumer(os.environ["input"])
producer_topic = client.get_topic_producer(os.environ["output"])

def smooth_data(df):
    # Convert the timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')

    # Set the timestamp as the index
    df.set_index('timestamp', inplace=True)

    # Resample the data to 1 minute intervals and forward fill any missing data
    df = df.resample('1T').ffill()

    # Use a rolling window of 3 minutes and calculate the mean
    df_smooth = df.rolling('3T').mean()

    # Drop the rows with NaN values that were created by the rolling window
    df_smooth = df_smooth.dropna()

    return df_smooth

def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):

    # Transform data frame here in this method. You can filter data or add new features.
    # Pass modified data frame to output stream using stream producer.

    # transform the data by applying the smoothing algorithm
    df_smooth = smooth_data(df)
    
    # Print the smoothed data
    print(df_smooth)

    stream_producer = producer_topic.get_or_create_stream(stream_id = stream_consumer.stream_id)
    stream_producer.timeseries.buffer.publish(df)

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
