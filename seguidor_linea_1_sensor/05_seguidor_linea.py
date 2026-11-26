#!/usr/bin/env pybricks-micropython
# ============================================================
# 05 - SEGUIDOR DE LINEA FINAL (UN SOLO SENSOR)
# Proyecto: seguidor de lineas "El Caballito de Troya"
# Hub: LEGO SPIKE Prime + Pybricks
# Motores: F (izquierdo) y B (derecho)
# Sensor: A (centrado en el robot)
# ============================================================
#
# GEOMETRIA:
# - Un solo sensor A, centrado en el robot, mirando la linea.
#
# POR QUE SE SIGUE UN BORDE Y NO EL CENTRO:
# - La reflectancia es baja (negro) en el centro de la linea y alta
#   (blanco) fuera de ella.
# - Si el sensor va por el CENTRO, al desviarse un poco hacia
#   cualquier lado la lectura sube igual. El robot no puede saber
#   hacia donde corregir: el centro es una zona "ciega".
# - En el BORDE la lectura es monotona y el control es estable.
#
# CONTROL ESTABLE (evita el "circulo sin sentido"):
# 1. Se filtra la lectura para quitar ruido.
# 2. Se normaliza: 0 = negro, 100 = blanco.
# 3. Banda muerta amplia: si el sensor esta cerca del borde, no
#    corrige. Asi no reacciona a cada pequena variacion.
# 4. Giro limitado por velocidad de cambio (slew rate): el volante
#    no puede pasar de un extremo al otro de golpe.
# 5. Freno sobre blanco: si ve blanco, baja la velocidad para no
#    escaparse mientras corrige.
# 6. Estados:
#       NORMAL    -> sigue el borde con PD suave
#       BUSCAR    -> se perdio: gira en el sitio hasta reencontrarla
#       RECUPERAR -> encontro la linea: vuelve despacio al borde
# 7. Si se pierde demasiadas veces seguidas, se detiene y avisa.
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

sensor = ColorSensor(Port.A)

# ============================================================
# CONFIGURACION
# ============================================================

# Calibracion por defecto (se reemplaza por la guardada en el hub)
BLACK = 17.3
WHITE = 98.4

# Control (valores conservadores para que no se descontrole)
BASE_SPEED = 90        # mm/s (empezar lento; subir solo si sigue bien)
KP = 1.2               # ganancia proporcional (suave)
KD = 0.10              # amortiguacion
TARGET_N = 50.0        # 50 = transicion negro/blanco
LADO = 1               # 1 = borde izquierdo, -1 = borde derecho
TURN_MAX = 250         # limite de giro, deg/s
TURN_SLEW = 15         # cambio maximo de giro por ciclo (deg/s)
SPEED_REDUCTION = 0.5  # cuanto baja la velocidad al girar
MIN_SPEED = 40         # velocidad minima en curvas, mm/s
DEADBAND = 12.0        # banda muerta: no corrige cerca del borde
FILTRO = 0.6           # peso de la lectura nueva (0..1)
LOOP_MS = 10

# Clasificacion de superficies (normalizado: 0=negro, 100=blanco)
NEGRO_MAX = 35.0
BLANCO_MIN = 65.0

# Freno sobre blanco: si el sensor ve blanco, baja la velocidad para que
# no se escape mientras corrige y pueda reencontrar el borde.
FRENO_GRIS = 0.60      # factor entre BLANCO_MIN y WHITE_LOST
FRENO_BLANCO = 0.35    # factor casi en blanco
MIN_SPEED_BLANCO = 25  # suelo de velocidad al frenar

# Deteccion de perdida
WHITE_LOST = 88.0      # casi blanco = posible perdida
LOST_GRACE_MS = 800    # tiempo que sigue corrigiendo antes de buscar

# Busqueda girando en el sitio hasta reencontrar la linea
SEARCH_TURN = 90       # deg/s
SEARCH_TIMEOUT_MS = 4000  # a 90 deg/s, una vuelta completa son 4 s

# Recuperacion despues de encontrar la linea
RECOVER_SPEED = 55     # mm/s
RECOVER_TURN = 90      # deg/s hacia el borde elegido
RECOVER_BAND = 10.0    # sale de recuperar cuando n supera TARGET - banda
RECOVER_TIMEOUT_MS = 1500

# Seguridad: demasiadas perdidas seguidas
MAX_PERDIDAS = 8
RESET_PERDIDAS_MS = 4000

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
        if len(partes) == 3 and partes[0] == "v1":
            negro = float(partes[1])
            blanco = float(partes[2])
            if blanco - negro >= 10:
                return negro, blanco
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
    raw_f = sensor.reflection()

    last_e = 0.0
    deriv_f = 0.0
    last_turn = 0.0

    estado = "NORMAL"
    blanco_ms = 0
    normal_ms = 0
    perdidas = 0

    search_ms = 0
    search_dir = 1

    recuperar_ms = 0

    ultimo_print = 0
    ultimo_display = 0

    while True:
        pressed = hub.buttons.pressed()
        if Button.LEFT in pressed:
            robot.stop()
            esperar_soltar(Button.LEFT)
            return "usuario"

        raw = sensor.reflection()
        raw_f = (1.0 - FILTRO) * raw_f + FILTRO * raw
        n = normalizar(raw_f, BLACK, WHITE)

        e = 0.0
        turn = 0.0

        if estado == "NORMAL":
            normal_ms += LOOP_MS
            if normal_ms > RESET_PERDIDAS_MS:
                normal_ms = RESET_PERDIDAS_MS
                perdidas = 0

            if n > WHITE_LOST:
                blanco_ms += LOOP_MS
            else:
                blanco_ms = 0

            if blanco_ms > LOST_GRACE_MS:
                # --- Se perdio: pasar a buscar ---
                perdidas += 1
                if perdidas > MAX_PERDIDAS:
                    robot.stop()
                    return "inestable"

                estado = "BUSCAR"
                search_ms = 0
                normal_ms = 0
                if last_turn > 0:
                    search_dir = 1
                elif last_turn < 0:
                    search_dir = -1
                robot.stop()
            else:
                # --- PD suave sobre el borde ---
                e = n - TARGET_N
                if abs(e) < DEADBAND:
                    e = 0.0

                deriv = e - last_e
                deriv_f = 0.6 * deriv_f + 0.4 * deriv
                turn_obj = LADO * (KP * e + KD * deriv_f)
                turn_obj = limitar(turn_obj, -TURN_MAX, TURN_MAX)

                # Limitar la velocidad de cambio del giro
                turn = last_turn + limitar(turn_obj - last_turn,
                                           -TURN_SLEW, TURN_SLEW)

                last_e = e
                last_turn = turn

                velocidad = BASE_SPEED - abs(turn) * SPEED_REDUCTION
                velocidad = limitar(velocidad, MIN_SPEED, BASE_SPEED)

                # Freno sobre blanco: evita que se escape al perder el borde
                if n > BLANCO_MIN:
                    if n > WHITE_LOST:
                        velocidad *= FRENO_BLANCO
                    else:
                        velocidad *= FRENO_GRIS
                    if velocidad < MIN_SPEED_BLANCO:
                        velocidad = MIN_SPEED_BLANCO

                robot.drive(velocidad, turn)

        elif estado == "BUSCAR":
            # --- Gira en el sitio hasta reencontrar la linea ---
            search_ms += LOOP_MS
            if search_ms > SEARCH_TIMEOUT_MS:
                robot.stop()
                return "perdido"

            turn = search_dir * SEARCH_TURN
            last_turn = turn
            robot.drive(0, turn)

            # Si ya ve negro o el borde, pasar a recuperar
            if n < TARGET_N + 10.0:
                estado = "RECUPERAR"
                recuperar_ms = 0
                robot.stop()

        else:  # RECUPERAR
            # --- Avanza despacio y vuelve al borde elegido ---
            recuperar_ms += LOOP_MS
            turn = -LADO * RECOVER_TURN
            last_turn = turn
            robot.drive(RECOVER_SPEED, turn)

            # Sale cuando llega al borde (desde el lado negro) o por tiempo
            if n > TARGET_N - RECOVER_BAND or recuperar_ms > RECOVER_TIMEOUT_MS:
                estado = "NORMAL"
                last_e = 0.0
                deriv_f = 0.0
                blanco_ms = 0
                normal_ms = 0

        t = reloj.time()

        if t - ultimo_display >= 100:
            if estado == "BUSCAR":
                hub.display.char("!")
                hub.light.on(Color.RED)
            elif estado == "RECUPERAR":
                hub.display.char("+")
                hub.light.on(Color.YELLOW)
            elif n < NEGRO_MAX:
                hub.display.char("N")
                hub.light.on(Color.GREEN)
            elif n > BLANCO_MIN:
                hub.display.char("B")
                hub.light.on(Color.YELLOW)
            else:
                hub.display.char("|")
                hub.light.on(Color.GREEN)
            ultimo_display = t

        if t - ultimo_print >= 250:
            print("A=%3d n=%3d | err=%4d turn=%4d | %s" %
                  (raw, int(n), int(e), int(turn), estado))
            ultimo_print = t

        wait(LOOP_MS)

# --- Cargar calibracion ---
cal = cargar_calibracion()
if cal is None:
    print("Usando calibracion por defecto.")
    print("Ejecuta 02_calibracion.py si cambias de piso o de linea.")
else:
    BLACK, WHITE = cal
    print("Calibracion cargada del hub.")

print("=== SEGUIDOR DE LINEA (UN SENSOR) ===")
print("Negro=%.1f Blanco=%.1f | TARGET=%.1f | LADO=%d" %
      (BLACK, WHITE, TARGET_N, LADO))
print("Velocidad=%d mm/s | KP=%.2f | KD=%.2f | Banda=%.1f" %
      (BASE_SPEED, KP, KD, DEADBAND))
print("Gracia=%d ms | Busqueda=%d ms" % (LOST_GRACE_MS, SEARCH_TIMEOUT_MS))
print("Si el robot gira ALEJANDOSE de la linea, cambia LADO a -1.")

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
        print("Linea perdida: demasiado tiempo sin ver el borde.")
        print("Revisa la calibracion, acerca el sensor o sube SEARCH_TIMEOUT_MS.")
    elif motivo == "inestable":
        hub.display.char("E")
        beep(250, 600)
        print("Demasiadas perdidas seguidas: el control esta inestable.")
        print("Baja KP, baja BASE_SPEED o cambia LADO de 1 a -1.")
    else:
        hub.display.char("S")
        beep(500, 200)
        print("Detenido por el usuario.")

    wait(500)
