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
    state['hotend_temperature'] += value['hotend_temperature']
    state['bed_temperature'] += value['bed_temperature']
    state['ambient_temperature'] += value['ambient_temperature']
    state['fluctuated_ambient_temperature'] += value['fluctuated_ambient_temperature']
    state['timestamp'] += value['timestamp']
    state['count'] += 1

    # only the first is needed so don't add any others
    # state['original_timestamp'] += value['original_timestamp']
    # state['printer'] += value['printer']
    
    return state

def initializer(value: dict) -> dict:
    return {
        'hotend_temperature': value['hotend_temperature'],
        'bed_temperature': value['bed_temperature'],
        'ambient_temperature': value['ambient_temperature'],
        'fluctuated_ambient_temperature': value['fluctuated_ambient_temperature'],
        'timestamp': value['timestamp'],
        'original_timestamp': value['original_timestamp'],
        'printer': value['printer'],
        'count': 1
    }

# apply the reducer
sdf = (
    sdf.tumbling_window(timedelta(seconds=10))
    .reduce(reducer=reducer, initializer=initializer)
    .final()
)

def get_row_value(row: dict, key: str):
    return row["value"][key]

# use the reduced values
sdf = sdf.apply(lambda row: {
    "timestamp": row["start"],
    "mean_hotend_temperature": get_row_value(row, "hotend_temperature") / get_row_value(row, "count"),
    "mean_bed_temperature": get_row_value(row, "bed_temperature") / get_row_value(row, "count"),
    "mean_ambient_temperature": get_row_value(row, "ambient_temperature") / get_row_value(row, "count"),
    "mean_fluctuated_ambient_temperature": get_row_value(row, "fluctuated_ambient_temperature") / get_row_value(row, "count"),
    "original_timestamp": get_row_value(row, "original_timestamp"),
    "count": get_row_value(row, "count"),
    "printer": get_row_value(row, "printer")
})

# uncomment to log the aggregated data to console.
sdf = sdf.update(lambda message: logger.info(message))

# sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")