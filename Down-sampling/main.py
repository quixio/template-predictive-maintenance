import quixstreams as qx
import pandas as pd
import os
import numpy as np

# Quix injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient()

print("Opening input and output topics")
topic_consumer = client.get_topic_consumer(os.environ["input"], "down-sampling-consumer-group")
topic_producer = client.get_topic_producer(os.environ["output"])

# buffer 1 minute of data
buffer_configuration = qx.TimeseriesBufferConfiguration()
buffer_configuration.time_span_in_milliseconds = 1 * 60 * 1000


# called for each incoming stream
def on_stream_received_handler(stream_consumer: qx.StreamConsumer):
    # called for each incoming DataFrame
    def on_dataframe_received_handler(originating_stream: qx.StreamConsumer, df: pd.DataFrame):

        # look for the timestamp column
        # if yours is named differently please change this code as needed
        if "timestamp" in df:
            df["date_time"] = pd.to_datetime(df["timestamp"])
        elif "time" in df:
            df["date_time"] = pd.to_datetime(df["time"])
        else:
            raise Exception("A suitable timestamp was column not found in the dataset")

        # Identify numeric and string columns
        numeric_columns = [col for col in df.columns if not col.startswith('TAG__')]
        string_columns = [col for col in df.columns if col.startswith('TAG__')]

        # Create an aggregation dictionary for numeric columns
        numeric_aggregation = {col: 'mean' for col in numeric_columns}

        # Create an aggregation dictionary for string columns (keeping the last value)
        string_aggregation = {col: 'last' for col in string_columns}

        # Merge the two aggregation dictionaries
        aggregation_dict = {**numeric_aggregation, **string_aggregation}

        # resample and get the mean of the input data
        df = df.set_index("date_time").resample('1min').agg(aggregation_dict)

        print(df)

        # Send filtered data to output topic
        stream_producer.timeseries.buffer.publish(df)

    # create a new stream to output data
    stream_producer = topic_producer.get_or_create_stream(stream_consumer.stream_id + "-down-sampled")
    stream_producer.properties.parents.append(stream_consumer.stream_id)

    # create the buffer
    buffer = stream_consumer.timeseries.create_buffer(buffer_configuration=buffer_configuration)

    # React to new data received from input topics buffer.
    # Here we assign a callback to be called when data arrives.
    buffer.on_dataframe_released = on_dataframe_received_handler

    # When input stream closes, we close output stream as well.
    def on_stream_close(stream_consumer: qx.StreamConsumer, end_type: qx.StreamEndType):
        stream_producer.close()
        print("Stream closed:" + stream_producer.stream_id)

    stream_consumer.on_stream_closed = on_stream_close


# Hook up events before initiating read to avoid losing out on any data
topic_consumer.on_stream_received = on_stream_received_handler

# Hook up to termination signal (for docker image) and CTRL-C
print("Listening to streams. Press CTRL-C to exit.")

# Handle graceful exit of the model.
qx.App.run()
