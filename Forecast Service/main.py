from uuid import uuid4
from quixstreams import Application, message_context
from dotenv import load_dotenv

import logging
import os
import sys
from datetime import datetime

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

from typing import List

with open("./.env", 'a+') as file: pass  # make sure the .env file exists
load_dotenv("./.env") # load environment variables from .env file for local dev

# Assigning environ vars to local variables
topic_input = os.environ["input"]
topic_output = os.environ["output"]
parameter_name = os.environ["parameter_name"] if "parameter_name" in os.environ else "fluctuated_ambient_temperature"

forecast_length = int(os.environ['forecast_length'])

debug = os.environ["debug"] == "1" if "debug" in os.environ else False
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO)
logger = logging.getLogger(__name__)

# 
def on_message_handler(rows: List[dict]):
    
    print(rows)

    forecast_input = list(map(lambda row: row["mean_fluctuated_ambient_temperature"], rows))

    # Define the degree of the polynomial regression model
    degree = 2
    # Create a polynomial regression model
    model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
    # Fit the model to the data
    model.fit(np.array(range(len(forecast_input))).reshape(-1, 1), forecast_input)
    # Forecast the future values
    forecast_array = np.array(range(len(forecast_input), len(forecast_input) + forecast_length)).reshape(-1, 1)
    forecast_values = model.predict(forecast_array)

    result = []
    timestamp = rows[-1]["timestamp"]

    for value in forecast_values:
        timestamp += 60 * 1000
        result.append({
            "timestamp": timestamp,
            "forecast": float(value)
        })
    return result


if __name__ == "__main__":
    
    app = Application.Quix("transformation-v3"+str(uuid4()), auto_offset_reset="earliest", use_changelog_topics=False)

    # Change consumer group to a different constant if you want to run model locally.
    logger.info("Opening input and output topics")

    input_topic = app.topic(topic_input, value_deserializer="json")
    producer_topic = app.topic(topic_output, value_serializer="json")

    # Hook up to termination signal (for docker image) and CTRL-C
    logger.info("Listening to streams. Press CTRL-C to exit.")

    sdf = app.dataframe(input_topic)

    sdf = sdf[sdf.contains("mean_fluctuated_ambient_temperature")]  # ensure the parameter_name column exists in the incomming data

    sdf = sdf[["timestamp", "mean_fluctuated_ambient_temperature"]]

    # reducer appends all row values (in this window) to state
    def reducer(state: list, row: dict):
        state.append(row)
        return state

    # init initializes the state. Arrays with the first value
    def reducer_init(row: dict):
        return [row]

    # apply the reducer funciton
    sdf = sdf.tumbling_window(5000).reduce(reducer, reducer_init).final()
    #sdf = sdf.update(lambda message: print(message))

    # sdf = sdf.update(lambda message: print(message))


    # sdf = sdf.update(lambda message: logger.info(message))

    # now handle the output from the above stage which will be like {value: {key:value}}
    sdf = sdf.apply(lambda row: on_message_handler(row["value"]), expand=True)
    # uncomment to log the raw data to console.

    sdf["timestamp"] = sdf["timestamp"].apply(lambda epoch: str(datetime.fromtimestamp(epoch/1000)))
    sdf = sdf.update(lambda message: print(message))

    sdf = sdf.to_topic(producer_topic)

    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")