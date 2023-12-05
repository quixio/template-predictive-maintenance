import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer


app = Application.Quix("transformation-v2", auto_offset_reset="latest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
# output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(input_topic)

try:
    # Here put transformation logic.
    sdf = sdf[sdf["Speed"] > 250]

    sdf = sdf[["Timestamp","Speed","Gear"]]

    # def rolling_speed(row: dict, state: State)


    sdf = sdf.update(lambda row: print(row))
except Exception as e:
    print(f"Exception {e}")

# sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)