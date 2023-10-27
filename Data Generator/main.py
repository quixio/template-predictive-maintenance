import quixstreams as qx
import DataFrame as pd
import random
import time
import csv
import os

# should the main loop run?
shutting_down = False

# Quix injects credentials automatically to the client.
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient()

# output topic to stream data out of your service
producer_topic = client.get_topic_producer(os.environ["output"])
stream_producer = producer_topic.get_or_create_stream("3D Printer 1")

# Initial temperatures in Fahrenheit
hotend = 70  # Starting at room temperature (room temperature in Fahrenheit)
bed = 90
air = 70

# Simulation parameters
hotend_target = 280
hotend_spike_min = 230
hotend_spike_max = 280
initial_spike_frequency = 0.01  # Initial spike frequency (adjust as needed)
max_spike_frequency = 0.05  # Maximum spike frequency (adjust as needed)
time_elapsed = 0
hotend_spiking = False
seconds_till_spike_end = 0
spike = 0
seconds_elapsed = 0


def log_to_csv(filename, *args):
    # Print the arguments
    for arg in args:
        print(arg)
    
    # Save the arguments to a CSV file
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(args)

# log column headers if needed
# log_to_csv("log.csv", "Elapsed", "hotend", "bed", "air")

# Simulation loop
start_time = time.time()
while not shutting_down and seconds_elapsed < 2 * 24 * 60 * 60:  # 2 days in seconds

    # If shutdown has been requested, exit the loop.
    if shutting_down:
        break

    # Periodically increase the hot end temperature
    if seconds_elapsed % random.randint(3600, 7200) == 0 and hotend < hotend_target:
        hotend += random.uniform(5, 10)  # Spike in hot end temperature

    # Air temperature rises gradually
    if air < 100:
        air += (1 / 3600)  # 1°F increase in 1 hour

    # Bed temperature fluctuates within a range
    bed += random.uniform(-0.01, 1)

    if hotend_spiking:
        if seconds_till_spike_end == 0:
            hotend -= spike
            hotend_spiking = False
            print("Hotend cooling down")
            # increase the spike frequency
            max_spike_frequency += 0.01
        else:
            seconds_till_spike_end -= 1
            print(f"{seconds_till_spike_end} till spike ends")

    # Check if it's time for a spike
    if random.random() < initial_spike_frequency + (seconds_elapsed / (2 * 24 * 60 * 60)) * (max_spike_frequency - initial_spike_frequency) and not hotend_spiking:
        spike = random.uniform(5, 10)
        hotend += spike  # Spike in hot end temperature
        hotend_spiking = True
        seconds_till_spike_end = random.randint(0, 60)  # end the spike in 0-60 seconds
        print(f"HOT END SPIKE {spike} for {seconds_till_spike_end} seconds")
        
    # Ensure the hot end stays within the desired range (220°F to 400°F)
    hotend = max(220, min(hotend, 400))

    # log_to_csv("log.csv", int(seconds_elapsed), f"{hotend:.2f}", f"{bed:.2f}", f"{air:.2f}")

    # Get the current time in nanoseconds
    current_time_ns = int(time.time() * 1e9)

    # Create a DataFrame with one row
    data = {
        'timestamp': [current_time_ns],
        'hotend': [hotend],  # Replace with your hotend value
        'bed': [bed],     # Replace with your bed value
        'air': [air]      # Replace with your air value
    }

     # publish the data to the Quix stream created earlier
    stream_producer.timeseries.publish(pd.DataFrame(data))

    seconds_elapsed += 1

    # sleep for 1 second
    # this ensures 1 row per second
    # decrease sleep for faster generation
    time.sleep(1)

# Final temperature report
print("Print finished. Final temperatures:")
print(f"Hot End: {hotend:.2f}°F, Bed: {bed:.2f}°F, Air: {air:.2f}°F")

def before_shutdown():
    global shutting_down

    print("Shutting down")
    # set the flag to True to stop the app as soon as possible.
    shutting_down = True

# keep the app running and handle termination signals.
qx.App.run(before_shutdown=before_shutdown)

print("Exiting")
