import os
import uu
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

#sdf = sdf.update(lambda row: logger.info(row))

# mean over 60 seconds

# sdf = sdf.update(lambda value: print(f'message_key: {message_context().key}'))


# one value
# sdf = (
#     sdf.apply(lambda value: value["hotend_temperature"])
#     .tumbling_window(duration_ms=timedelta(seconds=60))
#     .sum()
#     .current()
# )


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

sdf = sdf.update(lambda message: logger.info(message))

# {'hotend_temperature': 247.8174720120197, 
#  'bed_temperature': 110.12438003417356,
#  'ambient_temperature': 50.17978441953371,
#  'fluctuated_ambient_temperature': 50.17978441953371,
#  'timestamp': '2024-02-27T13:41:36.338654',
#  'original_timestamp': '2024-02-27T13:41:36.338654',
#  'TAG__printer': 'Printer 1'}


# Put transformation logic.here

#sdf = sdf.filter(lambda message: "m" in message)



# 1 * 60 * 1000

# Identify numeric and string columns
# numeric_columns = [col for col in df.columns if not col.startswith('TAG__') and
#                     col not in ['time', 'timestamp', 'original_timestamp', 'date_time']]
# string_columns = [col for col in df.columns if col.startswith('TAG__')]

# # Create an aggregation dictionary for numeric columns
# numeric_aggregation = {col: 'mean' for col in numeric_columns}
# Create an aggregation dictionary for string columns (keeping the last value)
# string_aggregation = {col: 'last' for col in string_columns}


#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")