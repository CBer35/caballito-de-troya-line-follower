from pybricks.hubs import PrimeHub
from pybricks.pupdevices import ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()
sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

hub.speaker.beep(frequency=700, duration=150)

samples_l = []
samples_r = []

for _ in range(10):
    samples_l.append(sensor_left.reflection())
    samples_r.append(sensor_right.reflection())
    wait(50)

avg_l = sum(samples_l) / len(samples_l)
avg_r = sum(samples_r) / len(samples_r)

print("WHITE_READINGS:")
print("Left (A) avg:", round(avg_l, 1), "min:", min(samples_l), "max:", max(samples_l))
print("Right (E) avg:", round(avg_r, 1), "min:", min(samples_r), "max:", max(samples_r))

hub.speaker.beep(frequency=900, duration=200)
