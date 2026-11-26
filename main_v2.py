#!/usr/bin/env pybricks-micropython
# Seguidor de Líneas - "El Caballito de Troya" (versión 2)
# 2 motores, 2 sensores de color (Puerto A y E)
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port, Direction, Button
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()

# --- Motores ---
motor_left = Motor(Port.F, Direction.COUNTERCLOCKWISE)
motor_right = Motor(Port.B, Direction.CLOCKWISE)

# --- Robot ---
robot = DriveBase(motor_left, motor_right, wheel_diameter=56, axle_track=200)

# --- Sensores de color ---
sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

# --- Parámetros PID del controlador proporcional ---
BASE_SPEED = 200      # mm/s (velocidad base de avance)
KP = 2.5              # proporcional (giro por diferencia de reflectancia)
KI = 0.01             # integral (anti-windup)
KD = 4.0              # derivativo

# Valores de referencia (reflectancia normalizada) obtenidos desde read_centered.py
BLACK_L, WHITE_L = 10.8, 97.4
BLACK_R, WHITE_R = 10.2, 90.0


def normalizar(val, v_min, v_max):
    """Convierte la reflectancia cruda a un valor normalizado 0..100."""
    if v_max <= v_min:
        return 50.0
    n = (val - v_min) * 100.0 / (v_max - v_min)
    if n < 0.0:
        return 0.0
    if n > 100.0:
        return 100.0
    return n


def calibrar_sensores():
    """
    Realiza una calibración rápida leyendo 20 muestras mientras el robot está sobre la línea.
    Devuelve las reflectancias promedio normalizadas de cada sensor.
    """
    vals_l = []
    vals_r = []
    for _ in range(20):
        vals_l.append(sensor_left.reflection())
        vals_r.append(sensor_right.reflection())
        wait(50)
    avg_l = sum(vals_l) / len(vals_l)
    avg_r = sum(vals_r) / len(vals_r)
    norm_l = normalizar(avg_l, BLACK_L, WHITE_L)
    norm_r = normalizar(avg_r, BLACK_R, WHITE_R)
    return norm_l, norm_r


# Calibrar al iniciar (tarda unos segundos hasta que el robot esté sobre la línea)
norm_l, norm_r = calibrar_sensores()

# Estado interno
last_error = 0.0
turn_rate = 0.0
speed = BASE_SPEED

print("=== Seguidor de línea v2 ===")
print(f"Sensores calibrados: A={norm_l:.1f}%  E={norm_r:.1f}%")

while True:
    # Detectar pulsaciones de botones (parar el robot)
    pressed = hub.buttons.pressed()
    if Button.RIGHT in pressed or Button.LEFT in pressed:
        robot.stop()
        while Button.RIGHT in hub.buttons.pressed() or Button.LEFT in hub.buttons.pressed():
            wait(20)
        hub.speaker.beep(400, 200)
        print("Botón R/L pulsado -> robot detenido.")
        continue

    # Lectura de los sensores de color
    rl = sensor_left.reflection()
    rr = sensor_right.reflection()

    # Normalización
    nl = normalizar(rl, BLACK_L, WHITE_L)
    nr = normalizar(rr, BLACK_R, WHITE_R)

    error = nl - nr
    derivative = error - last_error
    turn_rate = KP * error + KD * derivative
    last_error = error

    # Control de velocidad: velocidad base reducida proporcionalmente al giro
    speed = max(BASE_SPEED - abs(turn_rate) * 0.6, 0)

    # Dirigir
    robot.drive(speed, turn_rate)
    wait(10)

    # Mensajes en pantalla y sonido
    hub.display.char(">")
    hub.display.char("L")
    hub.speaker.beep(600, 150)