from pybricks.hubs import PrimeHub
from pybricks.pupdevices import ColorSensor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = PrimeHub()
sensor_a = ColorSensor(Port.A)
sensor_e = ColorSensor(Port.E)

hub.speaker.beep(frequency=600, duration=100)

val_a = sensor_a.reflection()
val_e = sensor_e.reflection()

print("PORT_A:", round(val_a, 1))
print("PORT_E:", round(val_e, 1))
hub.speaker.beep(frequency=900, duration=150)
