import asyncio
import websockets
import quixstreams as qx
import os
import pandas as pd

# Quix client
client = qx.QuixStreamingClient()
# the topic consumer, configured to read only the latest data
topic_consumer = client.get_topic_consumer(
                        topic_id_or_name=os.environ["input"], 
                        consumer_group="websocket-1", 
                        auto_offset_reset=qx.AutoOffsetReset.Latest)

# track the connections to our websocket
websocket_connections = []

# this is the handler for new data streams on the broker
def on_stream_received_handler(stream_consumer: qx.StreamConsumer):
    
    # this is the handler for new data in the topic
    def on_dataframe_received_handler(_: qx.StreamConsumer, df: pd.DataFrame):
        global websocket_connections

        # setup the event loop
        loop = asyncio.new_event_loop()

        # check for and remove closed connections
        websocket_connections = [ws for ws in websocket_connections if ws.open]

        for websocket in websocket_connections:

            # belt and braces to make sure we don't try to 
            # send data to a closed connection
            if not websocket.open:
                continue
            
            # Convert the 'timestamp' column to a datetime object
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ns')

            # Convert the datetime object to a UTC timestamp
            df['datetime'] = df['datetime'].dt.tz_localize('UTC')

            # Now you can convert the first record to JSON
            data = df.iloc[0].to_json()

            try:
                # attempt to send data to the client
                loop.run_until_complete(websocket.send(data))
            except websockets.exceptions.ConnectionClosed as e:
                # handle the connection being closed due to an issue
                print(f"Client disconnected with error: {e}")
            except websockets.exceptions.ConnectionClosedOK:
                # handle the connection being closed normally
                print("Client disconnected")

    # connect the data handler
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_received_handler

# connect the stream received handler
topic_consumer.on_stream_received = on_stream_received_handler


# handle new websocket connections
async def handle_websocket(websocket, path):
    # Store the WebSocket connection for later use
    print(f"Client connected to socket. Path={path}")
    websocket_connections.append(websocket)
    print(F"{len(websocket_connections)} active connection")
    try:
        # Keep the connection open and wait for messages if needed
        print("Keep the connection open and wait for messages if needed")
        await asyncio.sleep(3600)
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Client {path} disconnected with error: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client {path} disconnected normally.")
    finally:
        # Remove the connection from the list when it's closed
        print("Removing client from connection list")
        websocket_connections.remove(websocket)

# start the server. Listen on port 80
async def start_websocket_server():
    print("listening for websocket connections..")
    server = await websockets.serve(handle_websocket, '0.0.0.0', 80)
    await server.wait_closed()

# Main function to run the application
async def main():
    # subscribe to data arriving at the topic_consumer
    topic_consumer.subscribe()

    # start the server
    await start_websocket_server()

# Run the application
asyncio.run(main())

# disconnect from the topic
topic_consumer.unsubscribe()
