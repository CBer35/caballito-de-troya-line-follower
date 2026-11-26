from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()
print("Hub initialized successfully!")
print("Battery voltage:", hub.battery.voltage(), "mV")

sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

print("Left reflection (A):", sensor_left.reflection())
print("Right reflection (E):", sensor_right.reflection())
hub.speaker.beep(frequency=500, duration=200)
