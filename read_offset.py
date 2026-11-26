from pybricks.hubs import PrimeHub
from pybricks.pupdevices import ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()
sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

hub.speaker.beep(frequency=700, duration=150)

avg_l = sensor_left.reflection()
avg_r = sensor_right.reflection()

norm_l = (avg_l - 10.8) * 100.0 / (97.4 - 10.8)
norm_r = (avg_r - 10.2) * 100.0 / (90.0 - 10.2)
error = norm_l - norm_r

print("Left (A):", round(avg_l, 1), "-> Norm:", round(norm_l, 1), "%")
print("Right (E):", round(avg_r, 1), "-> Norm:", round(norm_r, 1), "%")
print("Error:", round(error, 1))

hub.speaker.beep(frequency=900, duration=200)
