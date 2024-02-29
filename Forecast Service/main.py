from quixstreams import Application
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
topic_input = os.getenv("input", "downsampled-3d-printer-data-json")
topic_output = os.getenv("output", "forecast")

forecast_length = int(os.getenv('forecast_length', "5"))

debug = os.getenv("debug", False)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO)
logger = logging.getLogger(__name__)

# 
def on_message_handler(rows: List[dict]):
    """
    Run the prediciton using the sklearn
    Output a list of objects with timestamp and forecast
    """

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
   
    # Quix platform injects credentials automatically to the client.
    # Alternatively, you can always pass an SDK token manually as an argument when working locally.
    # Or set the relevant values in a .env file
    app = Application.Quix("transformation", auto_offset_reset="earliest")

    # Change consumer group to a different constant if you want to run model locally.
    logger.info("Opening input and output topics")

    # Open the topics for input and output of data
    input_topic = app.topic(topic_input, value_deserializer="json")
    producer_topic = app.topic(topic_output, value_serializer="json")

    # Hook up to termination signal (for docker image) and CTRL-C
    logger.info("Listening to streams. Press CTRL-C to exit.")

    sdf = app.dataframe(input_topic)  # initialize the streaming dataframe

    sdf = sdf[sdf.contains("mean_fluctuated_ambient_temperature")]  # ensure the column exists in the incomming data

    sdf = sdf[["timestamp", "mean_fluctuated_ambient_temperature"]]  # select only these coluns for processing

    # reducer appends all but first rows values (in this window) to state
    def reducer(state: list, row: dict):
        state.append(row)
        return state

    # init initializes the state arrays with the first value
    def reducer_init(row: dict):
        return [row]

    # apply the reducer funciton
    sdf = sdf.tumbling_window(5000).reduce(reducer, reducer_init).final()

    # now handle the output from the above stage which will be like {value: {key:value}}
    sdf = sdf.apply(lambda row: on_message_handler(row["value"]), expand=True)

    # convert the timestamps to human readable
    sdf["timestamp"] = sdf["timestamp"].apply(lambda epoch: str(datetime.fromtimestamp(epoch/1000)))

    # publish the data resulting from this pipline to the topic
    sdf = sdf.to_topic(producer_topic)

    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")