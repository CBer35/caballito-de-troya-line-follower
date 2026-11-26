#!/usr/bin/env pybricks-micropython
# ============================================================
# 02 - CALIBRACION DEL SENSOR A (UN SOLO SENSOR)
# Proyecto: seguidor de lineas "El Caballito de Troya"
# ============================================================
#
# GEOMETRIA:
# - Un solo sensor A, centrado en el robot, mirando la linea.
#
# La calibracion se hace en 2 pasos:
#   1. Sensor A sobre la LINEA NEGRA.
#   2. Sensor A sobre el PISO BLANCO.
#
# Se guarda "v1,BLACK,WHITE" en la memoria del hub y la leen
# 04_prueba_control.py y 05_seguidor_linea.py.
# ============================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import ColorSensor
from pybricks.parameters import Port, Button, Color
from pybricks.tools import wait

hub = PrimeHub()
sensor = ColorSensor(Port.A)

MUESTRAS = 50
PAUSA_MS = 20

def beep(frecuencia=600, duracion=120):
    hub.speaker.beep(frecuencia, duracion)

def esperar_boton(boton=Button.RIGHT):
    while boton not in hub.buttons.pressed():
        wait(20)
    while boton in hub.buttons.pressed():
        wait(20)

def resumen(valores):
    valores.sort()
    recorte = len(valores) // 10
    if recorte > 0:
        valores = valores[recorte:-recorte]
    suma = 0
    for v in valores:
        suma += v
    return suma / len(valores), min(valores), max(valores)

def medir():
    valores = []
    for _ in range(MUESTRAS):
        valores.append(sensor.reflection())
        wait(PAUSA_MS)
    return resumen(valores)

def guardar_calibracion(negro, blanco):
    texto = "v1,%.1f,%.1f" % (negro, blanco)
    try:
        # El byte 0 final hace que la lectura se detenga en el lugar correcto.
        hub.system.storage(0, write=texto.encode() + b"\x00")
        print("Calibracion guardada en el hub: %s" % texto)
        return True
    except Exception as error:
        print("No se pudo guardar en el hub: %s" % error)
        print("Anota los valores y ponlos a mano en 05_seguidor_linea.py.")
        return False

def calibrar():
    print("")
    print("=== CALIBRACION DEL SENSOR A ===")

    # --- Paso 1: negro ---
    hub.display.number(1)
    print("Paso 1: pon el sensor A sobre la LINEA NEGRA.")
    print("Pulsa DERECHA para medir.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    negro, negro_min, negro_max = medir()
    beep(900, 100)
    print("Negro: %.1f (%.1f..%.1f)" % (negro, negro_min, negro_max))

    # --- Paso 2: blanco ---
    hub.display.number(2)
    print("Paso 2: pon el sensor A sobre el PISO BLANCO.")
    print("Pulsa DERECHA para medir.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    blanco, blanco_min, blanco_max = medir()
    beep(900, 100)
    print("Blanco: %.1f (%.1f..%.1f)" % (blanco, blanco_min, blanco_max))

    # --- Validacion ---
    contraste = blanco - negro
    print("")
    print("Contraste: %.1f" % contraste)

    if contraste < 15:
        print("ERROR: contraste muy bajo.")
        print("Revisa: sensor a 5-8 mm del piso, linea negra mate, luz estable.")
        hub.display.char("E")
        hub.light.on(Color.RED)
        beep(250, 600)
        return False

    if blanco <= negro:
        print("ERROR: el blanco no es mayor que el negro. Revisa los pasos.")
        hub.display.char("E")
        hub.light.on(Color.RED)
        beep(250, 600)
        return False

    # --- Guardar e imprimir ---
    guardar_calibracion(negro, blanco)

    print("")
    print("=== VALORES PARA 04 Y 05 ===")
    print("BLACK = %.1f" % negro)
    print("WHITE = %.1f" % blanco)
    print("TARGET = %.1f" % ((negro + blanco) / 2.0))
    print("")
    print("Calibracion lista. Deten este programa y ejecuta 05_seguidor_linea.py.")
    print("Si los valores no se cargan, apaga y enciende el hub normalmente.")
    hub.display.char("O")
    hub.light.off()
    beep(900, 300)
    return True

# Ejecutar
calibrar()
