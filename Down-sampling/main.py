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
app = Application.Quix("transformation-v2"+str(uid), auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"], value_deserializer="json")
output_topic = app.topic(os.environ["output"], value_serializer="json")

sdf = app.dataframe(input_topic)

# uncomment to log the raw data to console.
sdf = sdf.update(lambda message: logger.info(message))

def initializer(value: dict) -> dict:
    return {
        'mean_hotend_temperature': value['hotend_temperature'],
        'mean_bed_temperature': value['bed_temperature'],
        'mean_ambient_temperature': value['ambient_temperature'],
        'mean_fluctuated_ambient_temperature': value['fluctuated_ambient_temperature'],
        'max_timestamp': value['timestamp'],
        'max_original_timestamp': value['original_timestamp'],
        'max_TAG__printer': value['TAG__printer'],
        'count': 1,
    }

def reducer(aggregated: dict, value: dict) -> dict:
    return {
        'mean_hotend_temperature': min(aggregated['mean_hotend_temperature'], value['hotend_temperature']),
        'mean_bed_temperature': max(aggregated['mean_bed_temperature'], value['bed_temperature']),
        'mean_ambient_temperature': max(aggregated['mean_ambient_temperature'], value['ambient_temperature']),
        'mean_fluctuated_ambient_temperature': max(aggregated['mean_fluctuated_ambient_temperature'], value['fluctuated_ambient_temperature']),
        'max_timestamp': max(aggregated['max_timestamp'], value['timestamp']),
        'max_original_timestamp': max(aggregated['max_original_timestamp'], value['original_timestamp']),
        'max_TAG__printer': max(aggregated['max_TAG__printer'], value['TAG__printer']),
        'count': aggregated['count'] + 1,
    }

sdf = (
    sdf.tumbling_window(timedelta(seconds=10))
    .reduce(reducer=reducer, initializer=initializer)
    .final()
)

# uncomment to log the aggregated data to console.
# sdf = sdf.update(lambda message: logger.info(message))

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")