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

print("CENTERED_READINGS:")
print("Left (A) avg:", round(avg_l, 1))
print("Right (E) avg:", round(avg_r, 1))

# Normalizar con la calibracion obtenida
# A: 10.8 - 97.4
# E: 10.2 - 90.0
norm_l = (avg_l - 10.8) * 100.0 / (97.4 - 10.8)
norm_r = (avg_r - 10.2) * 100.0 / (90.0 - 10.2)
error = norm_l - norm_r

print("Normalized Left (A):", round(norm_l, 1), "%")
print("Normalized Right (E):", round(norm_r, 1), "%")
print("Error diferencial:", round(error, 1))

hub.speaker.beep(frequency=900, duration=200)
