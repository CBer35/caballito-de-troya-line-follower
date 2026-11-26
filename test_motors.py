from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Direction
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()

motor_left = Motor(Port.F, Direction.COUNTERCLOCKWISE)
motor_right = Motor(Port.B, Direction.CLOCKWISE)

robot = DriveBase(motor_left, motor_right, wheel_diameter=56, axle_track=200)

hub.speaker.beep(frequency=500, duration=200)
wait(300)
print("Moving forward 100 mm...")
robot.straight(100)
hub.speaker.beep(frequency=800, duration=200)
