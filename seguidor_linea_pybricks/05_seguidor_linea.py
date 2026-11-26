#!/usr/bin/env pybricks-micropython
# ============================================================
# 05 - SEGUIDOR DE LINEA FINAL (SENSORES SEPARADOS)
# Proyecto: seguidor de lineas "El Caballito de Troya"
# Hub: LEGO SPIKE Prime + Pybricks
# Motores: F (izquierdo) y B (derecho)
# Sensores: A (izquierdo) y E (derecho)
# ============================================================
#
# GEOMETRIA:
# - Los sensores van separados y la linea pasa ENTRE ellos.
# - Centrado: los dos sensores ven BLANCO.
# - Si el robot se va a la izquierda, el sensor DERECHO ve NEGRO:
#   error = nL - nR > 0 -> girar a la DERECHA.
# - Si se va a la derecha, el sensor IZQUIERDO ve NEGRO:
#   error < 0 -> girar a la IZQUIERDA.
# - Si los dos ven NEGRO: cruce o linea muy ancha -> seguir recto.
#
# EL PROBLEMA DE "TODO BLANCO":
# Con dos sensores separados, "todo blanco" puede significar:
#   a) el robot esta centrado y la linea pasa entre los sensores, o
#   b) el robot se salio de la linea y esta perdido.
# Con solo dos sensores NO se puede distinguir de inmediato.
#
# ESTRATEGIA:
# 1. Si hay al menos un sensor viendo negro, se corrige con PD normal.
# 2. Si los dos ven blanco, se avanza recto pero MAS LENTO y solo
#    WHITE_GRACE_MS (porque probablemente esta centrado). Se conserva
#    un poco el ultimo giro para no perder las curvas.
# 3. Si sigue todo blanco, se deja de avanzar y se gira en el sitio
#    barriendo a izquierda y derecha para volver a encontrar la linea.
# 4. Si no la encuentra en LOST_TIMEOUT_MS, se detiene y muestra "E".
#
# Asi el robot solo avanza a ciegas un tiempo limitado y, si no
# recupera la linea, se detiene en lugar de escaparse.
#
# BOTONES:
# DERECHA: iniciar
# IZQUIERDA: detener
# CENTRAL: detener el programa (comportamiento normal de Pybricks)
# ============================================================

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port, Direction, Button, Color
from pybricks.robotics import DriveBase
from pybricks.tools import wait, StopWatch

hub = PrimeHub()

motor_left = Motor(Port.F, Direction.COUNTERCLOCKWISE)
motor_right = Motor(Port.B, Direction.CLOCKWISE)
robot = DriveBase(motor_left, motor_right, wheel_diameter=56, axle_track=200)

sensor_left = ColorSensor(Port.A)
sensor_right = ColorSensor(Port.E)

# ============================================================
# CONFIGURACION
# ============================================================

# Calibracion por defecto (se reemplaza por la guardada en el hub)
BLACK_L = 10.8
WHITE_L = 97.4
BLACK_R = 10.2
WHITE_R = 90.0

# Control
BASE_SPEED = 160       # mm/s
KP = 2.5               # fuerza de giro por unidad de error
KD = 0.80              # amortiguacion (derivada filtrada)
TURN_MAX = 400         # limite de giro, deg/s
SPEED_REDUCTION = 0.5  # cuanto baja la velocidad al girar
MIN_SPEED = 70         # velocidad minima en curvas, mm/s
DEADBAND = 6.0         # error pequeno que se ignora
LOOP_MS = 10

# Clasificacion de superficies (normalizado: 0=negro, 100=blanco)
NEGRO_MAX = 35.0
BLANCO_MIN = 65.0

# Estrategia para "todo blanco"
WHITE_GRACE_MS = 1500  # tiempo que puede avanzar si los dos ven blanco
WHITE_SPEED_FACTOR = 0.60  # avanza mas lento mientras esta "a ciegas"
TURN_MEMORY = 0.7      # cuanto conserva el ultimo giro durante la gracia
SEARCH_SWEEP_MS = 800  # tiempo de giro en cada direccion al buscar
SEARCH_TURN = 120      # deg/s girando en el sitio
LOST_TIMEOUT_MS = 3000 # tiempo total en blanco antes de rendirse

# ============================================================

def beep(frecuencia=600, duracion=120):
    hub.speaker.beep(frecuencia, duracion)

def limitar(valor, minimo, maximo):
    if valor < minimo:
        return minimo
    if valor > maximo:
        return maximo
    return valor

def normalizar(valor, negro, blanco):
    if blanco <= negro + 1:
        return 50.0
    n = (valor - negro) * 100.0 / (blanco - negro)
    return limitar(n, 0.0, 100.0)

def cargar_calibracion():
    try:
        datos = hub.system.storage(0, read=64)
        texto = datos.split(b"\x00")[0].decode()
        partes = texto.split(",")
        if len(partes) == 5 and partes[0] == "v1":
            bl = float(partes[1])
            wl = float(partes[2])
            br = float(partes[3])
            wr = float(partes[4])
            if wl - bl >= 10 and wr - br >= 10:
                return bl, wl, br, wr
    except Exception as error:
        print("No hay calibracion guardada: %s" % error)
    return None

def esperar_soltar(boton):
    while boton in hub.buttons.pressed():
        wait(20)

def esperar_boton(boton=Button.RIGHT):
    while boton not in hub.buttons.pressed():
        wait(20)
    esperar_soltar(boton)

def seguir_linea():
    reloj = StopWatch()
    last_error = 0.0
    deriv_f = 0.0
    last_turn = 0.0
    ultimo_signo = 0

    blanco_ms = 0
    search_phase = 0
    search_dir = 1

    ultimo_print = 0
    ultimo_display = 0

    while True:
        pressed = hub.buttons.pressed()
        if Button.LEFT in pressed:
            robot.stop()
            esperar_soltar(Button.LEFT)
            return "usuario"

        rl = sensor_left.reflection()
        rr = sensor_right.reflection()
        nl = normalizar(rl, BLACK_L, WHITE_L)
        nr = normalizar(rr, BLACK_R, WHITE_R)

        todo_blanco = nl > BLANCO_MIN and nr > BLANCO_MIN
        todo_negro = nl < NEGRO_MAX and nr < NEGRO_MAX

        if todo_blanco:
            blanco_ms += LOOP_MS
        else:
            blanco_ms = 0
            search_phase = 0
            if ultimo_signo != 0:
                search_dir = ultimo_signo

        buscando = todo_blanco and blanco_ms > WHITE_GRACE_MS

        if buscando:
            # --- BUSQUEDA: no avanza, gira en el sitio ---
            if blanco_ms > LOST_TIMEOUT_MS:
                robot.stop()
                return "perdido"

            fase = (blanco_ms - WHITE_GRACE_MS) // SEARCH_SWEEP_MS
            if fase != search_phase:
                search_phase = fase
                search_dir = -search_dir

            error = 0.0
            turn = search_dir * SEARCH_TURN
            last_turn = 0.0
            robot.drive(0, turn)
        else:
            if todo_blanco:
                # --- GRACIA: probablemente centrado ---
                error = 0.0
                turn = last_turn * TURN_MEMORY
                last_turn = turn
                # Reiniciar el derivativo para que la proxima correccion
                # sea limpia cuando un sensor vuelva a ver negro.
                last_error = 0.0
                deriv_f = 0.0
                factor_velocidad = WHITE_SPEED_FACTOR
            else:
                # --- CONTROL NORMAL: al menos un sensor ve negro/gris ---
                error = nl - nr
                if abs(error) < DEADBAND:
                    error = 0.0

                if todo_negro:
                    # Cruce o linea ancha: seguir recto.
                    error = 0.0
                    deriv_f = 0.0

                deriv = error - last_error
                deriv_f = 0.6 * deriv_f + 0.4 * deriv
                turn = KP * error + KD * deriv_f
                turn = limitar(turn, -TURN_MAX, TURN_MAX)
                last_turn = turn
                last_error = error

                if error > 0.5:
                    ultimo_signo = 1
                elif error < -0.5:
                    ultimo_signo = -1

                factor_velocidad = 1.0

            velocidad = BASE_SPEED - abs(turn) * SPEED_REDUCTION
            velocidad = limitar(velocidad, MIN_SPEED, BASE_SPEED)
            robot.drive(velocidad * factor_velocidad, turn)

        t = reloj.time()

        if t - ultimo_display >= 100:
            if buscando:
                hub.display.char("!")
                hub.light.on(Color.RED)
            elif todo_blanco or todo_negro:
                hub.display.char("^")
                hub.light.on(Color.GREEN)
            elif abs(error) < DEADBAND:
                hub.display.char("^")
                hub.light.on(Color.GREEN)
            elif error > 0:
                hub.display.char(">")
                hub.light.on(Color.YELLOW)
            else:
                hub.display.char("<")
                hub.light.on(Color.YELLOW)
            ultimo_display = t

        if t - ultimo_print >= 250:
            if buscando:
                estado = "BUSCANDO"
            elif todo_blanco:
                estado = "BLANCO"
            elif todo_negro:
                estado = "NEGRO"
            else:
                estado = "LINEA"
            print("L=%3d R=%3d | nL=%3d nR=%3d | err=%4d turn=%4d | %s" %
                  (rl, rr, int(nl), int(nr), int(error), int(turn), estado))
            ultimo_print = t

        wait(LOOP_MS)

# --- Cargar calibracion ---
cal = cargar_calibracion()
if cal is None:
    print("Usando calibracion por defecto.")
    print("Ejecuta 02_calibracion.py si cambias de piso o de linea.")
else:
    BLACK_L, WHITE_L, BLACK_R, WHITE_R = cal
    print("Calibracion cargada del hub.")

print("=== SEGUIDOR DE LINEA (SENSORES SEPARADOS) ===")
print("Negro L=%.1f R=%.1f | Blanco L=%.1f R=%.1f" %
      (BLACK_L, BLACK_R, WHITE_L, WHITE_R))
print("Velocidad=%d mm/s | KP=%.2f | KD=%.2f" % (BASE_SPEED, KP, KD))
print("Gracia en blanco=%d ms | Busqueda=%d ms" %
      (WHITE_GRACE_MS, LOST_TIMEOUT_MS - WHITE_GRACE_MS))

while True:
    robot.stop()
    hub.display.char("R")
    hub.light.on(Color.GREEN)
    print("")
    print("Pulsa DERECHA para empezar. IZQUIERDA para detener.")
    esperar_boton(Button.RIGHT)

    beep(800, 150)
    motivo = seguir_linea()
    robot.stop()
    hub.light.off()

    if motivo == "perdido":
        hub.display.char("E")
        beep(250, 500)
        print("Linea perdida: estuvo demasiado tiempo sin ver negro.")
        print("Revisa la calibracion, acerca los sensores o sube WHITE_GRACE_MS.")
    else:
        hub.display.char("S")
        beep(500, 200)
        print("Detenido por el usuario.")

    wait(500)
