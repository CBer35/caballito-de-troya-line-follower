from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port, Direction, Button
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()

motor_left = Motor(Port.F, Direction.COUNTERCLOCKWISE)
motor_right = Motor(Port.B, Direction.CLOCKWISE)

robot = DriveBase(motor_left, motor_right, wheel_diameter=56, axle_track=200)

sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

SPEED = 120
KP = 1.3
KD = 2.2

black_l = 10.8
white_l = 97.4
black_r = 10.2
white_r = 90.0

def normalizar(val, v_min, v_max):
    if v_max <= v_min:
        return 50.0
    n = (val - v_min) * 100.0 / (v_max - v_min)
    if n < 0.0:
        return 0.0
    if n > 100.0:
        return 100.0
    return n

def esperar_boton():
    while not (Button.RIGHT in hub.buttons.pressed()):
        wait(20)
    while Button.RIGHT in hub.buttons.pressed():
        wait(20)
    hub.speaker.beep(800, 100)
    wait(200)

def seguir_linea():
    last_error = 0.0
    hub.display.char(">")

    while True:
        botones = hub.buttons.pressed()
        if Button.RIGHT in botones or Button.LEFT in botones:
            robot.stop()
            while Button.RIGHT in hub.buttons.pressed() or Button.LEFT in hub.buttons.pressed():
                wait(20)
            hub.speaker.beep(400, 200)
            break

        rl = sensor_left.reflection()
        rr = sensor_right.reflection()

        nl = normalizar(rl, black_l, white_l)
        nr = normalizar(rr, black_r, white_r)

        error = nl - nr

        derivative = error - last_error
        turn = (KP * error) + (KD * derivative)
        last_error = error

        robot.drive(SPEED, turn)
        wait(10)

hub.display.off()
hub.display.char("L")
hub.speaker.beep(600, 150)

while True:
    esperar_boton()
    seguir_linea()
    hub.display.char("L")
