import quixstreams as qx

import os
import random
from datetime import datetime, timedelta

import pandas as pd
import logging
import sys
import time

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Display all columns
pd.set_option('display.max_columns', 6)


def temp(target, sigma, offset):
    return target + offset + random.gauss(0, sigma)


def generate_data(stream: qx.StreamProducer):
    target_ambient_t = int(os.environ['target_ambient_t'])  # 50  # MAKE ENV VAR i.e. value of target_ambient
    hotend_t = int(os.environ['hotend_t'])  # 250  # MAKE ENV VAR: target temperature for the hotend
    bed_t = int(os.environ['bed_t'])  # 110  # MAKE ENV VAR: target temperature for the bed
    ambient_t = target_ambient_t  # 50 target ambient temperature

    hotend_sigma = 0.5
    bed_sigma = 0.5

    datalength = int(os.environ['datalength'])  # 28800  # MAKE ENV VAR: Currently 8 hours

    fluctuated_ambient_temperatures = []
    timestamp = datetime.now()
    next_fluctuation = timestamp + timedelta(seconds=random.randint(5, 300))
    fluctuation_end = timestamp
    fluctuation_amplitude = 0

    for i in range(datalength):
        timestamp = datetime.now()
        hotend_temperature = temp(hotend_t, hotend_sigma, 0)
        bed_temperature = temp(bed_t, bed_sigma, 0)

        # Introduce a curve-like downward trend in the final half of the data range
        if i > datalength / 2:
            # Calculate the proportion of the way through the second half of the data
            proportion = 2 * (i - datalength / 2) / datalength
            # Use a quadratic function to calculate the decrease
            ambient_t = target_ambient_t - (target_ambient_t / 2) * (proportion ** 2)

        ambient_temperature = ambient_t

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
              fluctuated_ambient_temperature]],
            columns=['timestamp', 'original_timestamp', 'hotend_temperature', 'bed_temperature', 'ambient_temperature',
                     'fluctuated_ambient_temperature'])
        stream.timeseries.buffer.publish(df)
        logging.debug(f"Published:\n{df}")

        next_timestamp = timestamp + timedelta(seconds=1)
        time_difference = next_timestamp - timestamp
        delay_seconds = time_difference.total_seconds()
        logging.debug(f"Waiting {delay_seconds} seconds to send next data point.")
        time.sleep(delay_seconds)


if __name__ == "__main__":
    # Quix injects credentials automatically to the client.
    # Alternatively, you can always pass an SDK token manually as an argument.
    client = qx.QuixStreamingClient()

    # Open the output topic where to write data out
    topic_producer = client.get_topic_producer(topic_id_or_name=os.environ["output"])

    # Set stream ID or leave parameters empty to get stream ID generated.
    stream = topic_producer.create_stream()
    stream.properties.name = "Generated 3D printer data"

    # Add metadata about time series data you are about to send.
    stream.timeseries.add_definition("hotend_temperature", "Hot end temperature")
    stream.timeseries.add_definition("bed_temperature", "Bed temperature")
    stream.timeseries.add_definition("ambient_temperature", "Ambient temperature")
    stream.timeseries.add_definition("fluctuated_ambient_temperature", "Ambient temperature with fluctuations")

    print(f"Sending values for {os.environ['datalength']} seconds.")
    generate_data(stream)

    print("Closing stream")
    stream.close()
