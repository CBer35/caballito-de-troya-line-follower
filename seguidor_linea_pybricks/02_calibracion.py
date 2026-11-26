#!/usr/bin/env pybricks-micropython
# ============================================================
# 02 - CALIBRACION GUIADA PARA SENSORES SEPARADOS
# Proyecto: seguidor de lineas "El Caballito de Troya"
# ============================================================
#
# GEOMETRIA:
# - Los sensores van separados y la linea pasa ENTRE ellos.
# - Centrado: los dos sensores ven BLANCO.
# - Si el robot se va a un lado, uno de los dos ve NEGRO.
#
# Por eso la calibracion se hace en 3 pasos:
#   1. Sensor IZQUIERDO (A) sobre la linea negra;
#      sensor DERECHO (E) sobre el piso blanco.
#   2. Sensor DERECHO (E) sobre la linea negra;
#      sensor IZQUIERDO (A) sobre el piso blanco.
#   3. Robot centrado, con la linea entre los dos sensores:
#      los dos sobre el piso blanco.
#
# La calibracion se guarda en la memoria del hub y la leen
# 04_prueba_control.py y 05_seguidor_linea.py.
# ============================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import ColorSensor
from pybricks.parameters import Port, Button, Color
from pybricks.tools import wait

hub = PrimeHub()
sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

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
    promedio = suma / len(valores)
    return promedio, min(valores), max(valores)

def medir_par():
    vl = []
    vr = []
    for _ in range(MUESTRAS):
        vl.append(sensor_left.reflection())
        vr.append(sensor_right.reflection())
        wait(PAUSA_MS)
    return resumen(vl), resumen(vr)

def guardar_calibracion(bl, wl, br, wr):
    texto = "v1,%.1f,%.1f,%.1f,%.1f" % (bl, wl, br, wr)
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
    print("=== CALIBRACION PARA SENSORES SEPARADOS ===")

    # --- Paso 1: izquierdo negro, derecho blanco ---
    hub.display.number(1)
    print("Paso 1: pon el sensor IZQUIERDO (A) sobre la LINEA NEGRA")
    print("y el sensor DERECHO (E) sobre el PISO BLANCO.")
    print("Pulsa DERECHA para medir.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    (bl, bl_min, bl_max), (wr_ref, wr_ref_min, wr_ref_max) = medir_par()
    beep(900, 100)
    print("Paso 1 -> Negro izquierdo: %.1f (%.1f..%.1f)" %
          (bl, bl_min, bl_max))
    print("           Blanco derecho de referencia: %.1f" % wr_ref)

    # --- Paso 2: derecho negro, izquierdo blanco ---
    hub.display.number(2)
    print("Paso 2: pon el sensor DERECHO (E) sobre la LINEA NEGRA")
    print("y el sensor IZQUIERDO (A) sobre el PISO BLANCO.")
    print("Pulsa DERECHA para medir.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    (wl_ref, wl_ref_min, wl_ref_max), (br, br_min, br_max) = medir_par()
    beep(900, 100)
    print("Paso 2 -> Negro derecho: %.1f (%.1f..%.1f)" %
          (br, br_min, br_max))
    print("           Blanco izquierdo de referencia: %.1f" % wl_ref)

    # --- Paso 3: los dos blancos, robot centrado ---
    hub.display.number(3)
    print("Paso 3: pon el robot CENTRADO, con la linea entre los dos")
    print("sensores. Los dos deben ver el PISO BLANCO.")
    print("Pulsa DERECHA para medir.")
    esperar_boton(Button.RIGHT)
    beep(700, 100)
    (wl, wl_min, wl_max), (wr, wr_min, wr_max) = medir_par()
    beep(900, 100)
    print("Paso 3 -> Blanco izquierdo: %.1f (%.1f..%.1f)" %
          (wl, wl_min, wl_max))
    print("           Blanco derecho: %.1f (%.1f..%.1f)" %
          (wr, wr_min, wr_max))

    # --- Validacion ---
    contraste_l = wl - bl
    contraste_r = wr - br
    print("")
    print("Contraste: L=%.1f | R=%.1f" % (contraste_l, contraste_r))

    if wr_ref < 40 or wl_ref < 40:
        print("AVISO: en el paso 1 o 2 el sensor que debia ver blanco no lo vio.")
        print("Revisa la posicion del robot antes de confiar en la calibracion.")

    if contraste_l < 15 or contraste_r < 15:
        print("ERROR: contraste muy bajo.")
        print("Revisa: sensor a 5-8 mm del piso, linea negra mate, luz estable.")
        hub.display.char("E")
        hub.light.on(Color.RED)
        beep(250, 600)
        return False

    if wl <= bl or wr <= br:
        print("ERROR: el blanco no es mayor que el negro. Revisa los pasos.")
        hub.display.char("E")
        hub.light.on(Color.RED)
        beep(250, 600)
        return False

    # --- Guardar e imprimir ---
    guardar_calibracion(bl, wl, br, wr)

    print("")
    print("=== VALORES PARA 04 Y 05 ===")
    print("BLACK_L = %.1f" % bl)
    print("WHITE_L = %.1f" % wl)
    print("BLACK_R = %.1f" % br)
    print("WHITE_R = %.1f" % wr)
    print("UMBRAL_L = %.1f" % ((bl + wl) / 2.0))
    print("UMBRAL_R = %.1f" % ((br + wr) / 2.0))
    print("")
    print("Calibracion lista. Deten este programa y ejecuta 05_seguidor_linea.py.")
    print("Si los valores no se cargan, apaga y enciende el hub normalmente.")
    hub.display.char("O")
    hub.light.off()
    beep(900, 300)
    return True

# Ejecutar
calibrar()
