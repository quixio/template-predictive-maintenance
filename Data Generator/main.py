import asyncio
import logging
import math
import os
import random
import sys
from datetime import datetime, timedelta

import pandas as pd
import quixstreams as qx

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Display all columns
pd.set_option('display.max_columns', None)

# Replay speed
replay_speed = 10.0
anomaly_fluctuation = 20  # was 3
hot_end_anomaly_min_duration = 30  # 3
hot_end_anomaly_max_duration = 35  # 5
bed_anomaly_min_duration = 30  # 9
bed_anomaly_max_duration = 35  # 12


def temp(target, sigma, offset):
    return target + offset + random.gauss(0, sigma)


def generate_data():
    data = []
    target_ambient_t = int(os.environ['target_ambient_t'])  # 50  # MAKE ENV VAR i.e. value of target_ambient
    hotend_t = int(os.environ['hotend_t'])  # 250  # MAKE ENV VAR: target temperature for the hotend
    bed_t = int(os.environ['bed_t'])  # 110  # MAKE ENV VAR: target temperature for the bed
    ambient_t = target_ambient_t  # 50 target ambient temperature

    hotend_sigma = 0.5
    bed_sigma = 0.5
    ambient_sigma = 0.2

    datalength = int(os.environ['datalength'])  # 28800  # MAKE ENV VAR: Currently 8 hours

    # Generate 20 random anomaly timestamps
    number_of_anomalies = int(os.environ["number_of_anomalies"])
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

        df = pd.DataFrame(
            [[hotend_temperature, bed_temperature, ambient_temperature,
              fluctuated_ambient_temperature]],
            columns=['hotend_temperature', 'bed_temperature', 'ambient_temperature',
                     'fluctuated_ambient_temperature'])

        data.append(df)

        next_timestamp = start_timestamp + timedelta(seconds=elapsed_seconds)
        elapsed_seconds += 1
        timestamp = next_timestamp

    return data


async def publish_data(printer: str, stream: qx.StreamProducer, data: list):
    start_timestamp = datetime.now()
    elapsed_seconds = 0

    for frame in data:
        next_timestamp = start_timestamp + timedelta(seconds=elapsed_seconds)
        elapsed_seconds += 1

        frame["timestamp"] = pd.to_datetime(next_timestamp)
        frame["original_timestamp"] = pd.to_datetime(next_timestamp)
        frame["TAG__printer"] = printer

        stream.timeseries.buffer.publish(frame)

        # Dataframe should be sent at initial_timestamp + elapsed_seconds / replay_speed
        target_time = start_timestamp + timedelta(seconds=elapsed_seconds / replay_speed)
        delay_seconds = target_time.timestamp() - datetime.now().timestamp()

        if delay_seconds < 0:
            logging.warning(f"{printer : <10}: Not enough CPU to keep up with replay speed")
        else:
            logging.debug(f"{printer : <10}: Waiting {delay_seconds:.3f} seconds to send next data point.")
            await asyncio.sleep(delay_seconds)



async def generate_data_and_close_stream_async(topic_producer: qx.TopicProducer, printer: str, printer_data: list, initial_delay: int):
    await asyncio.sleep(initial_delay)
    while True:
        stream = topic_producer.create_stream()
        stream.properties.name = printer
        
        stream.timeseries.buffer.time_span_in_milliseconds = 500

        # Add metadata about time series data you are about to send.
        stream.timeseries.add_definition("hotend_temperature", "Hot end temperature")
        stream.timeseries.add_definition("bed_temperature", "Bed temperature")
        stream.timeseries.add_definition("ambient_temperature", "Ambient temperature")
        stream.timeseries.add_definition("fluctuated_ambient_temperature", "Ambient temperature with fluctuations")

        # Add metadata about printer
        stream.properties.metadata["start_time"] = str(int(datetime.utcnow().timestamp()) * 1000000000)
        stream.properties.metadata["end_time"] = str(int(datetime.utcnow().timestamp() + int(os.environ['datalength']) / replay_speed) * 1000000000)

        # Temperature will drop below threshold in second 20839
        failure_timestamps = [int(datetime.utcnow().timestamp() + 20839) * 1000000000]
        failure_replay_speed_timestamps = [
            int(datetime.utcnow().timestamp() + 20839 / replay_speed) * 1000000000]

        stream.properties.metadata["failures"] = str(failure_timestamps)
        stream.properties.metadata["failures_replay_speed"] = str(failure_replay_speed_timestamps)

        print(f"{printer}: Sending values for {os.environ['datalength']} seconds.")
        await publish_data(printer, stream, printer_data)

        print(f"{printer}: Closing stream")
        stream.close()

        # Wait 10 seconds before starting again
        await asyncio.sleep(10)


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
    printer_data = generate_data()

    # Distribute all printers over the data length
    delay_seconds = int(os.environ['datalength']) / replay_speed / number_of_printers

    for i in range(number_of_printers):
        # Set stream ID or leave parameters empty to get stream ID generated.
        name = f"Printer {i + 1}"  # We don't want a Printer 0, so start at 1

        # Start sending data, each printer will start with some delay after the previous one
        tasks.append(asyncio.create_task(generate_data_and_close_stream_async(topic_producer, name, printer_data.copy(), delay_seconds * i)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
