import json
import hashlib

from quixstreams import Application, State
import os

import logging
from dotenv import load_dotenv

from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("./.env", 'a+') as file: pass  # make sure the .env file exists
load_dotenv("./.env") # load environment variables from .env file for local dev

app = Application.Quix("transformation-v1" + str(uuid4()), auto_offset_reset="latest")

forecast_topic = os.environ["forecast_topic"]
alerts_topic = os.environ["alert_topic"]

# Alerts definitions
NO_ALERT = "no-alert"
UNDER_FORECAST = "under-forecast"
OVER_FORECAST = "over-forecast"
UNDER_NOW = "under-now"
OVER_NOW = "over-now"
PRINTER_FINISHED = "printer-finished"

low_threshold = 73
high_threshold = 75

def hash_json(json_obj):
    json_str = json.dumps(json_obj, sort_keys=True)  # Convert to string and sort keys for consistency
    return hashlib.sha256(json_str.encode()).hexdigest()  # Hash the string and get the hexadecimal representation


def on_forecast_received(message: dict, state: State):
    
    alert_status = state.get("alert_status", 
                             {  "status": NO_ALERT,
                                "parameter_name": "",
                                "alert_temperature": 0,
                                "alert_timestamp": "",
                                "message": ""
                             })
    
    forecast = message["forecast"]

    if forecast <= low_threshold and not forecast >= high_threshold:
        print(alert_status)
        if forecast < low_threshold and alert_status["status"] != UNDER_FORECAST:
            alert_status = {
                "status": UNDER_FORECAST,
                "parameter_name": "ambient_temperature",
                "alert_temperature": forecast,
                "alert_timestamp": message["timestamp"],
                "message": f"'Ambient temperature' is forecasted to fall below {low_threshold}ºC at {message['timestamp']}."
            }
            #break
        elif forecast > high_threshold and alert_status["status"] != OVER_FORECAST:
            alert_status = {
                "status": OVER_FORECAST,
                "parameter_name": "ambient_temperature",
                "alert_temperature": forecast,
                "alert_timestamp": message["timestamp"],
                "message": f"'Ambient temperature' is forecasted to go over {high_threshold}ºC at {message['timestamp']}."
            }
                #break
    else:
        alert_status = {
            "status": NO_ALERT,
            "parameter_name": "ambient_temperature",
            "alert_timestamp": message["timestamp"],
            "message": f"'Ambient temperature' is within specified parameters."
        }

    state.set("alert_status", alert_status)  # store the updated alert status in state for use next time

    alert_hash = hash_json(alert_status)  # calculate the unique hash of this alert, to avoid sending the same alert twice
    past_alerts = state.get("past_alerts", [])  # get the past alerts from state
    if past_alerts == None: past_alerts = []  # 

    if (alert_hash not in past_alerts and alert_status != {} and 
        alert_status['status'] in [UNDER_NOW, UNDER_FORECAST, OVER_NOW, OVER_FORECAST]):
        past_alerts.append(alert_hash)
        state.set("past_alerts", past_alerts)
        return {"alert_payload": alert_status}


def main():
    app = Application.Quix("transformation", auto_offset_reset="earliest", use_changelog_topics=False)

    logger.info("Opening input and output topics")

    input_topic = app.topic(forecast_topic, value_deserializer="json")
    producer_topic = app.topic(alerts_topic, value_serializer="json")

    sdf = app.dataframe(input_topic)
    sdf = sdf[sdf.contains("timestamp")]  # ensure the parameter_name column exists in the incomming data
    
    sdf = sdf.apply(on_forecast_received, stateful=True)

    # filter any rows that have no data
    # these are rows where there is no alert created for the inbound data
    sdf = sdf.filter(lambda row: row is not None)
    
    sdf = sdf.to_topic(producer_topic)  # publish to the desired output topic 

    try:
        app.run(sdf)
    except Exception as e:
        logger.exception("An error occurred while running the application.")

if __name__ == "__main__":
    main()