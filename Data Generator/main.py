import asyncio

import quixstreams as qx

import os
import random
from datetime import datetime, timedelta

import pandas as pd
import logging
import sys

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Display all columns
pd.set_option('display.max_columns', 6)

# Replay speed
replay_speed = 1.0


def temp(target, sigma, offset):
    return target + offset + random.gauss(0, sigma)


async def generate_data(printer: str, stream: qx.StreamProducer):
    target_ambient_t = int(os.environ['target_ambient_t'])  # 50  # MAKE ENV VAR i.e. value of target_ambient
    hotend_t = int(os.environ['hotend_t'])  # 250  # MAKE ENV VAR: target temperature for the hotend
    bed_t = int(os.environ['bed_t'])  # 110  # MAKE ENV VAR: target temperature for the bed
    ambient_t = target_ambient_t  # 50 target ambient temperature

    hotend_sigma = 0.5
    bed_sigma = 0.5
    ambient_sigma = 0.1

    datalength = int(os.environ['datalength'])  # 28800  # MAKE ENV VAR: Currently 8 hours

    # Generate 20 random anomaly timestamps
    number_of_anomalies = int(os.environ["number_of_anomalies"])
    anomaly_timestamps = [random.randint(0, datalength) for _ in range(number_of_anomalies)]
    anomaly_end = -1

    fluctuated_ambient_temperatures = []

    # Start with the current time without milliseconds
    timestamp = datetime.now().replace(microsecond=0)
    next_fluctuation = timestamp + timedelta(seconds=random.randint(5, 300))
    fluctuation_end = timestamp
    fluctuation_amplitude = 0

    for i in range(datalength):
        hotend_temperature = temp(hotend_t, hotend_sigma, 0)
        bed_temperature = temp(bed_t, bed_sigma, 0)

        # Check if current timestamp is an anomaly timestamp
        if i in anomaly_timestamps:
            # Start a new anomaly
            hotend_temperature -= 3
            anomaly_end = i + random.randint(3, 5)
            # Continue anomaly if within duration
        elif i <= anomaly_end:
            hotend_temperature -= 3

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
                fluctuation_amplitude = random.uniform(-3, 3)

        fluctuated_ambient_temperatures.append(fluctuated_ambient_temperature)

        df = pd.DataFrame(
            [[timestamp, timestamp, hotend_temperature, bed_temperature, ambient_temperature,
              fluctuated_ambient_temperature, printer]],
            columns=['timestamp', 'original_timestamp', 'hotend_temperature', 'bed_temperature', 'ambient_temperature',
                     'fluctuated_ambient_temperature', 'TAG__printer'])

        stream.timeseries.buffer.publish(df)
        logging.debug(f"{printer}: Published:\n{df}")

        next_timestamp = timestamp + timedelta(seconds=1)
        time_difference = next_timestamp - timestamp
        delay_seconds = time_difference.total_seconds() / replay_speed
        logging.debug(f"{printer}: Waiting {delay_seconds} seconds to send next data point.")
        await asyncio.sleep(delay_seconds)
        timestamp = next_timestamp


async def generate_data_and_close_stream_async(topic_producer: qx.TopicProducer, printer: str, initial_delay: int):
    await asyncio.sleep(initial_delay)
    while True:
        stream = topic_producer.create_stream()
        stream.properties.name = printer

        # Add metadata about time series data you are about to send.
        stream.timeseries.add_definition("hotend_temperature", "Hot end temperature")
        stream.timeseries.add_definition("bed_temperature", "Bed temperature")
        stream.timeseries.add_definition("ambient_temperature", "Ambient temperature")
        stream.timeseries.add_definition("fluctuated_ambient_temperature", "Ambient temperature with fluctuations")
        stream.properties.metadata["start_time"] = str(int(datetime.now().timestamp()) * 1000000000)

        print(f"{printer}: Sending values for {os.environ['datalength']} seconds.")
        await generate_data(printer, stream)

        print(f"{printer}: Closing stream")
        stream.close()

        # Wait 5 minutes before starting again
        await asyncio.sleep(5 * 60)


async def main():
    # Quix injects credentials automatically to the client.
    # Alternatively, you can always pass an SDK token manually as an argument.
    client = qx.QuixStreamingClient()

    # Open the output topic where to write data out
    topic_producer = client.get_topic_producer(topic_id_or_name=os.environ["output"])

    # Create a stream for each printer
    if 'number_of_printers' not in os.environ:
        number_of_printers = 1
    else:
        number_of_printers = int(os.environ['number_of_printers'])

    tasks = []

    for i in range(number_of_printers):
        # Set stream ID or leave parameters empty to get stream ID generated.
        name = f"Printer {i + 1}"  # We don't want a Printer 0, so start at 1

        # Start sending data, each printer will start 5 minutes after the previous one
        tasks.append(asyncio.create_task(generate_data_and_close_stream_async(topic_producer, name, i * 300)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

