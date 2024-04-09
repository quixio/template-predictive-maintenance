import asyncio
import logging
import math
import os
import random
import sys
from datetime import datetime, timedelta
import json
import dotenv

from quixstreams import Application
from quixstreams.models.topics import Topic
from quixstreams.kafka import Producer

dotenv.load_dotenv() # for local dev, load env vars from .env file d
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Replay speed
replay_speed = 10.0
anomaly_fluctuation = 20
hot_end_anomaly_min_duration = 30
hot_end_anomaly_max_duration = 35
bed_anomaly_min_duration = 30
bed_anomaly_max_duration = 35


def get_data_length() -> int:
    return int(os.getenv('datalength', 60000))


def temp(target, sigma, offset):
    return target + offset + random.gauss(0, sigma)


def generate_data():
    data = []
    target_ambient_t = 75
    hotend_t = 250
    bed_t = 110
    ambient_t = 50

    hotend_sigma = 0.5
    bed_sigma = 0.5
    ambient_sigma = 0.2

    datalength = int(os.getenv('datalength', 30000))  # 28800  # MAKE ENV VAR: Currently 8 hours

    # Generate 20 random anomaly timestamps
    number_of_anomalies = int(os.getenv("number_of_anomalies", "20"))
    hotend_anomaly_timestamps = [random.randint(0, datalength) for _ in range(number_of_anomalies)]
    bed_anomaly_timestamps = [random.randint(0, datalength) for _ in range(number_of_anomalies)]

    hotend_anomaly_end = -1
    bed_anomaly_end = -1

    fluctuated_ambient_temperatures = []

    # Start with the current time without milliseconds
    timestamp = datetime.now().replace(microsecond=0)
    next_fluctuation = timestamp + timedelta(seconds=random.randint(5, 300))
    fluctuation_end = timestamp
    fluctuation_amplitude = 0

    start_timestamp = datetime.now().replace(microsecond=0)
    elapsed_seconds = 0

    for i in range(datalength):
        hotend_temperature = temp(hotend_t, hotend_sigma, 0)
        bed_temperature = temp(bed_t, bed_sigma, 0)

        hotend_anomaly_start = 0
        bed_anomaly_start = 0

        # Check if current timestamp is an anomaly timestamp
        if i in hotend_anomaly_timestamps:
            # Start a new anomaly
            hotend_anomaly_start = i
            hotend_anomaly_end = i + random.randint(hot_end_anomaly_min_duration, hot_end_anomaly_max_duration)
            # Continue anomaly if within duration

        if i <= hotend_anomaly_end:
            hotend_temperature -= anomaly_fluctuation * math.sin(
                math.pi * (hotend_anomaly_end - i) / (hotend_anomaly_end - hotend_anomaly_start))

        if i in bed_anomaly_timestamps:
            # Start a new anomaly
            bed_anomaly_start = i
            bed_anomaly_end = i + random.randint(bed_anomaly_min_duration, bed_anomaly_max_duration)
            # Continue anomaly if within duration

        if i <= bed_anomaly_end:
            bed_temperature -= anomaly_fluctuation / 2 * math.sin(
                math.pi * (bed_anomaly_end - i) / (bed_anomaly_end - bed_anomaly_start))

        # Introduce a curve-like downward trend in the final half of the data range
        if i > datalength / 2:
            # Calculate the proportion of the way through the second half of the data
            proportion = 2 * (i - datalength / 2) / datalength
            # Use a quadratic function to calculate the decrease
            ambient_t = target_ambient_t - (target_ambient_t / 2) * (proportion ** 2)

        ambient_temperature = temp(ambient_t, ambient_sigma, 0)

        # Add fluctuations
        if next_fluctuation <= timestamp <= fluctuation_end:
            fluctuated_ambient_temperature = ambient_temperature + fluctuation_amplitude
        else:
            fluctuated_ambient_temperature = ambient_temperature
            if timestamp > fluctuation_end:
                next_fluctuation = timestamp + timedelta(seconds=random.randint(5, 300))
                fluctuation_duration = timedelta(seconds=random.randint(1, 4))
                fluctuation_end = next_fluctuation + fluctuation_duration
                fluctuation_amplitude = random.uniform(-2, 2)

        fluctuated_ambient_temperatures.append(fluctuated_ambient_temperature)

        data_dict = {
            'hotend_temperature': hotend_temperature,
            'bed_temperature': bed_temperature,
            'ambient_temperature': ambient_temperature,
            'fluctuated_ambient_temperature': fluctuated_ambient_temperature
        }

        data.append(data_dict)

        next_timestamp = start_timestamp + timedelta(seconds=elapsed_seconds)
        elapsed_seconds += 1
        timestamp = next_timestamp

    return data


async def publish_data(printer: str, topic_name: str, producer: Producer, data: list):
    start_timestamp = datetime.now()
    elapsed_seconds = 0

    for frame in data:
        next_timestamp = start_timestamp + timedelta(seconds=elapsed_seconds)
        elapsed_seconds += 1

        frame["timestamp"] = datetime.fromtimestamp(next_timestamp.timestamp()).isoformat()
        frame["original_timestamp"] = datetime.fromtimestamp(next_timestamp.timestamp()).isoformat()
        frame["printer"] = printer

        json_data = json.dumps(frame)  # convert the row to JSON
        producer.produce(topic_name, json_data, key=printer)  # publish with the producer

        # Dataframe should be sent at initial_timestamp + elapsed_seconds / replay_speed
        target_time = start_timestamp + timedelta(seconds=elapsed_seconds / replay_speed)
        delay_seconds = target_time.timestamp() - datetime.now().timestamp()

        if delay_seconds < 0:
            logging.warning(f"{printer : <10}: Not enough CPU to keep up with replay speed")
        else:
            logging.debug(f"{printer : <10}: Waiting {delay_seconds:.3f} seconds to send next data point.")
            await asyncio.sleep(delay_seconds)


async def generate_data_async(topic: Topic, producer: Producer, printer: str, printer_data: list, initial_delay: int):
    await asyncio.sleep(initial_delay)
    while True:
        print(f"{printer}: Sending values for {os.getenv('datalength')} seconds.")
        await publish_data(printer, topic.name, producer, printer_data)

        print(f"{printer}: Closing stream")

        # Wait 10 seconds before starting again
        await asyncio.sleep(10)


async def main():
    # Quix platform injects credentials automatically to the client.
    # Alternatively, you can always pass an SDK token manually as an argument when working locally.
    # Or set the relevant values in a .env file
    app = Application.Quix("consumer-group-1", use_changelog_topics=False)
    producer = app.get_producer()

    # Open the output topic where to write data out
    topic = app.topic(os.getenv("output", "3d-printer-data-json"))  # serialize with json by default
    
    number_of_printers = int(os.getenv("number_of_printers", 1)) # we will create a new stream for each printer

    tasks = []
    printer_data = generate_data()

    # Distribute all printers over the data length (defaults to 60 seconds)
    delay_seconds = get_data_length() / replay_speed / number_of_printers

    for i in range(number_of_printers):
        # Set MessageKey/StreamID or leave parameters empty to get a generated message key.
        name = f"Printer {i + 1}"  # We don't want a Printer 0, so start at 1

        # Start sending data, each printer will start with some delay after the previous one
        tasks.append(asyncio.create_task(generate_data_async(topic, producer, name, printer_data.copy(), int(delay_seconds * i))))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.exception("An error occurred while running the application.")
