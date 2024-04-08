import os
from quixstreams import Application
from dotenv import load_dotenv
import logging
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("./.env", 'a+') as file: pass  # make sure the .env file exists
load_dotenv("./.env")

# Quix platform injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument when working locally.
# Or set the relevant values in a .env file
app = Application.Quix("transformation", auto_offset_reset="latest")

# Open the topics for input and output of data
input_topic = app.topic(os.getenv("input", "3d-printer-data-json"), value_deserializer="json")
output_topic = app.topic(os.getenv("output", "downsampled-3d-printer-data-json"), value_serializer="json")

sdf = app.dataframe(input_topic)  # initialize the streaming dataframe
sdf = sdf[sdf.contains("printer")] # ensure the column "printer" exists in the incomming data


def reducer(state: dict, value: dict) -> dict:
    """
    'reducer' will be called for every message except the first.
    We add the values to sum them so we can later divide by the 
    count to get an average.
    """

    state['sum_hotend_temperature'] += value['hotend_temperature']
    state['sum_bed_temperature'] += value['bed_temperature']
    state['sum_ambient_temperature'] += value['ambient_temperature']
    state['sum_fluctuated_ambient_temperature'] += value['fluctuated_ambient_temperature']
    state['sum_count'] += 1
    return state

def initializer(value: dict) -> dict:
    """
    'initializer' will be called only for the first message.
    This is the time to create and initialize the state for 
    use in the reducer funciton.
    """

    return {
        'sum_hotend_temperature': value['hotend_temperature'],
        'sum_bed_temperature': value['bed_temperature'],
        'sum_ambient_temperature': value['ambient_temperature'],
        'sum_fluctuated_ambient_temperature': value['fluctuated_ambient_temperature'],
        'sum_timestamp': value['timestamp'],
        'sum_original_timestamp': value['original_timestamp'],
        'sum_printer': value['printer'],
        'sum_count': 1
    }

# create a tumbling window of 10 seconds
# use the reducer and initializer configured above
# get the 'final' values for the window once the window is closed.
sdf = (
    sdf.tumbling_window(timedelta(seconds=10))
    .reduce(reducer=reducer, initializer=initializer)
    .final()
)

def get_mean(row: dict, key: str):
    return row["value"][key] / row["value"]["sum_count"]


# use the reduced values
sdf = sdf.apply(lambda row: {
    "timestamp": row["start"],
    "mean_hotend_temperature": get_mean(row, "sum_hotend_temperature"),
    "mean_bed_temperature": get_mean(row, "sum_bed_temperature"),
    "mean_ambient_temperature": get_mean(row, "sum_ambient_temperature"),
    "mean_fluctuated_ambient_temperature": get_mean(row, "sum_fluctuated_ambient_temperature"),
    "original_timestamp": row["value"]["sum_original_timestamp"],
    "count": row["value"]["sum_count"],
    "printer": row["value"]["sum_printer"]
})

sdf = sdf.to_topic(output_topic)  # publish to the desired output topic 

if __name__ == "__main__":
    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")