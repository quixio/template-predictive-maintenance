import os
from uuid import uuid4
from quixstreams import Application, message_context
from dotenv import load_dotenv
import logging
from datetime import timedelta
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("./.env", 'a+') as file: pass  # make sure the .env file exists
load_dotenv("./.env")

uid = uuid.uuid4()
app = Application.Quix("transformation-v2"+str(uid), auto_offset_reset="latest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"], value_deserializer="json")
output_topic = app.topic(os.environ["output"], value_serializer="json")

sdf = app.dataframe(input_topic)
# sdf = sdf.update(lambda message: logger.info(message))

sdf = sdf[sdf.contains("printer")] # ensure the column "printer" exists in the incomming data

# uncomment to log the raw data to console.
# sdf = sdf.update(lambda message: logger.info(message))

def reducer(state: dict, value: dict) -> dict:
    state['sum_hotend_temperature'] += value['hotend_temperature']
    state['sum_bed_temperature'] += value['bed_temperature']
    state['sum_ambient_temperature'] += value['ambient_temperature']
    state['sum_fluctuated_ambient_temperature'] += value['fluctuated_ambient_temperature']
    state['sum_count'] += 1

    # only the first is needed so don't add any others
    # state['original_timestamp'] += value['original_timestamp']
    # state['printer'] += value['printer']
    # state['sum_timestamp'] += value['timestamp']
    
    return state

def initializer(value: dict) -> dict:
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

# apply the reducer
sdf = (
    sdf.tumbling_window(timedelta(seconds=10))
    .reduce(reducer=reducer, initializer=initializer)
    .final()
)
# sdf = sdf.update(lambda message: logger.info(message))

# todo remove
def get_row_value(row: dict, key: str):
    return row["value"][key]

def get_mean(row: dict, key: str):
    return row["value"][key] / get_row_value(row, "sum_count")


# use the reduced values
sdf = sdf.apply(lambda row: {
    "timestamp": row["start"],
    "mean_hotend_temperature": get_mean(row, "sum_hotend_temperature"),
    "mean_bed_temperature": get_mean(row, "sum_bed_temperature"),
    "mean_ambient_temperature": get_mean(row, "sum_ambient_temperature"),
    "mean_fluctuated_ambient_temperature": get_mean(row, "sum_fluctuated_ambient_temperature"),
    "original_timestamp": get_row_value(row, "sum_original_timestamp"),
    "count": get_row_value(row, "sum_count"),
    "printer": get_row_value(row, "sum_printer")
})

# uncomment to log the aggregated data to console.
# sdf = sdf.update(lambda message: logger.info(message))

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")