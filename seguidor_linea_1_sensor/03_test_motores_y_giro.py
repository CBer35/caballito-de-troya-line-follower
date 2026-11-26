#!/usr/bin/env pybricks-micropython
# ============================================================
# 03 - TEST DE MOTORES, RECTA Y FUERZA DE GIRO
# Proyecto: seguidor de lineas "El Caballito de Troya"
# ============================================================
#
# QUE HACE:
# 1. Prueba el motor izquierdo y el derecho por separado.
# 2. Avanza 300 mm en linea recta y mide el desvio con el giroscopio.
# 3. Gira 90 grados a la derecha y 90 a la izquierda.
# 4. Mide cuanto gira de verdad el robot para varios valores de
#    "turn_rate" (grados/segundo), en sitio y avanzando.
#
# COMO USARLO:
# - Para las pruebas de motor individual, levanta el robot.
# - Para las pruebas de avance y giro, ponlo en el piso con espacio.
# - Pulsa DERECHA para cada paso.
#
# INTERPRETACION:
# - Si una rueda gira al reves, cambia su Direction en este archivo
#   y en 05_seguidor_linea.py.
# - Si el robot se desvia mucho en recta, revisa la traccion.
# - Si el giro medido es mucho menor que el comando, sube KP o TURN_MAX.
# ============================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Direction, Button
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()

motor_left = Motor(Port.F, Direction.COUNTERCLOCKWISE)
motor_right = Motor(Port.B, Direction.CLOCKWISE)

robot = DriveBase(motor_left, motor_right, wheel_diameter=56, axle_track=200)

def beep(frecuencia=600, duracion=120):
    hub.speaker.beep(frecuencia, duracion)

def esperar_boton(boton=Button.RIGHT):
    while boton not in hub.buttons.pressed():
        wait(20)
    while boton in hub.buttons.pressed():
        wait(20)

def probar_motor(motor, nombre, letra):
    hub.display.char(letra)
    print("Prueba motor %s. Pulsa DERECHA." % nombre)
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    motor.run(300)
    wait(1000)
    motor.stop()
    wait(300)
    beep(900, 100)
    print("Motor %s: la rueda debe girar hacia adelante." % nombre)

def medir_giro_en_sitio(rate, tiempo_ms=1000):
    robot.stop()
    wait(300)
    hub.imu.reset_heading(0)
    robot.drive(0, rate)
    wait(tiempo_ms)
    robot.stop()
    wait(300)
    return hub.imu.heading()

def medir_giro_avanzando(rate, tiempo_ms=1000, velocidad=150):
    robot.stop()
    wait(300)
    hub.imu.reset_heading(0)
    robot.drive(velocidad, rate)
    wait(tiempo_ms)
    robot.stop()
    wait(300)
    return hub.imu.heading()

def prueba_fuerza_giro():
    print("")
    print("=== FUERZA DE GIRO (giroscopio) ===")
    print("Comando (deg/s) | En sitio (deg) | Avanzando (deg)")
    for rate in (60, 120, 180, 240):
        h1 = medir_giro_en_sitio(rate)
        h2 = medir_giro_avanzando(rate)
        print("  %4d          | %8.0f       | %8.0f" % (rate, h1, h2))
    print("")
    print("Si el valor medido es parecido al comando, el giro responde bien.")
    print("Si es muy distinto, ajusta axle_track (o revisa la bateria).")
    print("Si el signo es contrario, revisa las direcciones de los motores.")

def prueba_recta():
    print("")
    print("=== RECTA ===")
    hub.display.char("F")
    print("Pon el robot en el piso. Pulsa DERECHA para avanzar 300 mm.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    hub.imu.reset_heading(0)
    robot.straight(300)
    wait(300)
    desvio = hub.imu.heading()
    print("Desvio de rumbo en 300 mm: %.1f grados" % desvio)
    if abs(desvio) > 8:
        print("  AVISO: el robot se desvia. Revisa que las ruedas tengan la misma traccion.")
    beep(900, 100)

def prueba_giros():
    print("")
    print("=== GIROS DE 90 GRADOS ===")
    hub.display.char("D")
    print("Pulsa DERECHA para girar 90 grados a la DERECHA.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    hub.imu.reset_heading(0)
    robot.turn(90)
    wait(300)
    medido = hub.imu.heading()
    print("Giro a la derecha: comando 90, medido %.1f grados." % medido)
    if medido < 80 or medido > 100:
        print("  AVISO: ajusta axle_track. Si gira de menos, sube el valor; si gira de mas, bajalo.")
    beep(900, 100)

    hub.display.char("I")
    print("Pulsa DERECHA para girar 90 grados a la IZQUIERDA.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    hub.imu.reset_heading(0)
    robot.turn(-90)
    wait(300)
    medido = hub.imu.heading()
    print("Giro a la izquierda: comando -90, medido %.1f grados." % medido)
    beep(900, 100)

print("=== TEST DE MOTORES Y GIRO ===")
print("Para las pruebas individuales, levanta el robot.")
beep(700, 150)
wait(500)

while True:
    probar_motor(motor_left, "IZQUIERDO (F)", "L")
    probar_motor(motor_right, "DERECHO (B)", "R")

    print("")
    print("Ahora pon el robot en el piso, con espacio para moverse.")
    print("Pulsa DERECHA para continuar.")
    esperar_boton(Button.RIGHT)

    prueba_recta()
    prueba_giros()

    hub.display.char("G")
    print("")
    print("Pulsa DERECHA para medir la fuerza de giro con el giroscopio.")
    esperar_boton(Button.RIGHT)
    prueba_fuerza_giro()

    print("")
    print("Prueba terminada. Pulsa DERECHA para repetir o deten el programa.")
    hub.display.char("O")
    beep(900, 300)
    esperar_boton(Button.RIGHT)
