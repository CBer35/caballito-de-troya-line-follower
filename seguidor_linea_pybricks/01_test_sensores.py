#!/usr/bin/env pybricks-micropython
# ============================================================
# 01 - TEST DE SENSORES DE COLOR
# Proyecto: seguidor de lineas "El Caballito de Troya"
# Hub: LEGO SPIKE Prime + Pybricks
# Sensores: A (izquierdo) y E (derecho)
# ============================================================
#
# QUE HACE:
# - Muestra en consola la reflectancia cruda de cada sensor (0-100).
# - Guarda el minimo y el maximo vistos para calcular el contraste.
# - Muestra en la pantalla del hub el valor del sensor que toca.
# - Cambia el color de la luz del hub segun la superficie:
#       VERDE    = al menos un sensor ve negro (linea detectada)
#       ROJO     = los dos ven blanco (linea entre los sensores, o perdido)
#       AMARILLO = ambos negros (cruce/linea ancha) o zona de borde
#
# GEOMETRIA:
# - Sensores separados, con la linea pasando entre ellos.
# - Centrado: los dos ven blanco.
# - Si el robot se va a un lado, uno de los dos ve negro.
#
# COMO USARLO:
# 1. Ejecuta este programa.
# 2. Pasa el robot despacio sobre la linea negra y sobre el piso blanco.
# 3. Mira la consola de Pybricks Code.
# 4. Boton IZQUIERDA: reinicia los minimos y maximos.
# 5. Boton DERECHA: termina y muestra el resumen.
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

sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

# Limites para clasificar rapidamente (se pueden ajustar)
NEGRO_MAX = 35
BLANCO_MIN = 65

# Minimos y maximos observados
min_l = 100.0
max_l = 0.0
min_r = 100.0
max_r = 0.0

reloj = StopWatch()
ultimo_print = 0
ultimo_color = 0
ultimo_display = 0
mostrar_izquierda = True

def beep(frecuencia=600, duracion=120):
    hub.speaker.beep(frecuencia, duracion)

def reiniciar_limites():
    global min_l, max_l, min_r, max_r
    min_l = 100.0
    max_l = 0.0
    min_r = 100.0
    max_r = 0.0

def resumen(nombre, minimo, maximo):
    contraste = maximo - minimo
    umbral = (minimo + maximo) / 2.0
    print("%s: min=%.1f max=%.1f contraste=%.1f umbral=%.1f" %
          (nombre, minimo, maximo, contraste, umbral))
    if contraste < 20:
        print("  AVISO: contraste bajo. Acerca el sensor al piso (5-8 mm) o mejora la luz.")

print("=== TEST DE SENSORES ===")
print("Mueve el robot sobre la linea negra y el piso blanco.")
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

    rl = sensor_left.reflection()
    rr = sensor_right.reflection()

    if rl < min_l:
        min_l = rl
    if rl > max_l:
        max_l = rl
    if rr < min_r:
        min_r = rr
    if rr > max_r:
        max_r = rr

    t = reloj.time()

    # Luz del hub: estado de los dos sensores
    if rl < NEGRO_MAX or rr < NEGRO_MAX:
        hub.light.on(Color.GREEN)      # al menos uno ve la linea
    elif rl > BLANCO_MIN and rr > BLANCO_MIN:
        hub.light.on(Color.RED)        # los dos blancos: centrado o perdido
    else:
        hub.light.on(Color.YELLOW)     # borde/gris

    # Pantalla: alterna el valor crudo de cada sensor cada 500 ms
    if t - ultimo_display >= 500:
        if mostrar_izquierda:
            hub.display.number(min(99, int(rl)))
        else:
            hub.display.number(min(99, int(rr)))
        mostrar_izquierda = not mostrar_izquierda
        ultimo_display = t

    # Consola: valores cada 250 ms
    if t - ultimo_print >= 250:
        print("L(A)=%3d [%3d..%3d] | R(E)=%3d [%3d..%3d]" %
              (rl, min_l, max_l, rr, min_r, max_r))
        ultimo_print = t

    # Color/HSV cada 1000 ms (no hace falta en cada lectura)
    if t - ultimo_color >= 1000:
        print("  color: L=%s R=%s | HSV: L=%s R=%s" %
              (sensor_left.color(), sensor_right.color(),
               sensor_left.hsv(), sensor_right.hsv()))
        ultimo_color = t

    wait(50)

# Resumen final
print("")
print("=== RESUMEN ===")
resumen("Sensor izquierdo (A)", min_l, max_l)
resumen("Sensor derecho  (E)", min_r, max_r)
print("")
print("Si el contraste es bueno, ejecuta 02_calibracion.py.")
print("Copia estos valores si quieres usarlos a mano en 05_seguidor_linea.py:")
print("BLACK_L = %.1f" % min_l)
print("WHITE_L = %.1f" % max_l)
print("BLACK_R = %.1f" % min_r)
print("WHITE_R = %.1f" % max_r)

hub.display.char("O")
hub.light.off()
beep(900, 200)
wait(1000)
