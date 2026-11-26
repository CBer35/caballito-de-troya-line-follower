#!/usr/bin/env pybricks-micropython
# ============================================================
# 01 - TEST DEL SENSOR DE COLOR (UN SOLO SENSOR)
# Proyecto: seguidor de lineas "El Caballito de Troya"
# Hub: LEGO SPIKE Prime + Pybricks
# Sensor: A (centrado en el robot)
# ============================================================
#
# QUE HACE:
# - Muestra la reflectancia cruda del sensor A (0-100).
# - Guarda el minimo y el maximo vistos para calcular el contraste.
# - Muestra el valor en la pantalla del hub.
# - Cambia el color de la luz del hub:
#       VERDE    = negro (sensor sobre la linea)
#       ROJO     = blanco (sensor fuera de la linea)
#       AMARILLO = borde / gris (transicion)
#
# COMO USARLO:
# 1. Ejecuta este programa.
# 2. Pasa el sensor despacio sobre la linea negra y sobre el piso blanco.
# 3. Mira la consola de Pybricks Code.
# 4. IZQUIERDA: reinicia minimos y maximos.
# 5. DERECHA: termina y muestra el resumen.
#
# VALORES TIPICOS EN SPIKE PRIME:
#   Negro: 5 - 15
#   Blanco: 85 - 100
#   Contraste bueno: mas de 50
# ============================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import ColorSensor
from pybricks.parameters import Port, Button, Color
from pybricks.tools import wait, StopWatch

hub = PrimeHub()
sensor = ColorSensor(Port.A)

# Limites para clasificar rapidamente (se pueden ajustar)
NEGRO_MAX = 35
BLANCO_MIN = 65

minimo = 100.0
maximo = 0.0

reloj = StopWatch()
ultimo_print = 0
ultimo_color = 0
ultimo_display = 0

def beep(frecuencia=600, duracion=120):
    hub.speaker.beep(frecuencia, duracion)

def reiniciar_limites():
    global minimo, maximo
    minimo = 100.0
    maximo = 0.0

print("=== TEST DEL SENSOR A ===")
print("Mueve el sensor sobre la linea negra y el piso blanco.")
print("IZQUIERDA: reiniciar limites | DERECHA: salir")
beep(700, 150)

while True:
    pressed = hub.buttons.pressed()

    if Button.RIGHT in pressed:
        break

    if Button.LEFT in pressed:
        reiniciar_limites()
        beep(500, 120)
        while Button.LEFT in hub.buttons.pressed():
            wait(20)

    r = sensor.reflection()

    if r < minimo:
        minimo = r
    if r > maximo:
        maximo = r

    t = reloj.time()

    # Luz del hub: estado del sensor
    if r < NEGRO_MAX:
        hub.light.on(Color.GREEN)      # sobre la linea
    elif r > BLANCO_MIN:
        hub.light.on(Color.RED)        # fuera de la linea
    else:
        hub.light.on(Color.YELLOW)     # borde / transicion

    # Pantalla: valor crudo
    if t - ultimo_display >= 300:
        hub.display.number(min(99, int(r)))
        ultimo_display = t

    # Consola: valor y contraste
    if t - ultimo_print >= 250:
        print("A=%3d [%3d..%3d] contraste=%3d" %
              (r, minimo, maximo, maximo - minimo))
        ultimo_print = t

    # Color/HSV cada 1000 ms (diagnostico)
    if t - ultimo_color >= 1000:
        print("  color=%s HSV=%s" % (sensor.color(), sensor.hsv()))
        ultimo_color = t

    wait(50)

# Resumen final
print("")
print("=== RESUMEN ===")
contraste = maximo - minimo
print("Sensor A: min=%.1f max=%.1f contraste=%.1f" %
      (minimo, maximo, contraste))
print("UMBRAL = %.1f" % ((minimo + maximo) / 2.0))
if contraste < 20:
    print("  AVISO: contraste bajo. Acerca el sensor al piso (5-8 mm).")
print("")
print("Si el contraste es bueno, ejecuta 02_calibracion.py.")

hub.display.char("O")
hub.light.off()
beep(900, 200)
wait(1000)
