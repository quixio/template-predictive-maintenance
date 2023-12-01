import quixstreams as qx
import os
import pandas as pd


client = qx.QuixStreamingClient()

topic_consumer = client.get_topic_consumer(os.environ["input"], consumer_group = "empty-transformation")
topic_producer = client.get_topic_producer(os.environ["output"])


def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
    stream_producer = topic_producer.get_or_create_stream(stream_id = stream_consumer.stream_id)
    stream_producer.timeseries.buffer.publish(df)


# Handle event data from samples that emit event data
def on_event_data_received_handler(stream_consumer: qx.StreamConsumer, data: qx.EventData):
    if data.id == 'over-forecast' or data.id == 'under-forecast':
        print(data)

    if data.id == 'over-now' or data.id == 'under-now':
        print(data)



def on_stream_received_handler(stream_consumer: qx.StreamConsumer):
    # subscribe to new DataFrames being received
    # if you aren't familiar with DataFrames there are other callbacks available
    # refer to the docs here: https://docs.quix.io/sdk/subscribe.html
    stream_consumer.events.on_data_received = on_event_data_received_handler # register the event data callback
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_received_handler


# subscribe to new streams being received
topic_consumer.on_stream_received = on_stream_received_handler

print("Listening to streams. Press CTRL-C to exit.")

# Handle termination signals and provide a graceful exit
qx.App.run()