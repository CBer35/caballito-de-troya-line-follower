#!/usr/bin/env pybricks-micropython
# ============================================================
# 04 - PRUEBA DE PERFILES (UN SOLO SENSOR, CONTROL ESTABLE)
# Proyecto: seguidor de lineas "El Caballito de Troya"
# ============================================================
#
# GEOMETRIA:
# - Un solo sensor A, centrado en el robot, mirando la linea.
# - Se sigue UN BORDE de la linea (transicion negro/blanco).
#
# CONTROL ESTABLE:
# - Filtro de lectura, banda muerta amplia y limite de velocidad
#   de cambio del giro (slew rate).
# - Estados NORMAL / BUSCAR / RECUPERAR.
# - Si se pierde muchas veces seguidas, la prueba lo reporta.
#
# PERFILES:
# 1 SUAVE      - lento y muy estable
# 2 MEDIO      - equilibrio (recomendado para empezar)
# 3 FUERTE     - mas rapido, corrige mas
# 4 MUY FUERTE - solo si los anteriores van sobrados
#
# BOTONES:
# IZQUIERDA: cambia de perfil
# DERECHA: inicia la prueba
# IZQUIERDA durante la prueba: detiene
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

# --- Calibracion por defecto (se sobrescribe con la guardada) ---
BLACK = 17.3
WHITE = 98.4

# --- Parametros generales ---
LOOP_MS = 10
TARGET_N = 50.0
LADO = 1
DEADBAND = 10.0
FILTRO = 0.6
TURN_MAX = 250.0
TURN_SLEW = 18
SPEED_REDUCTION = 0.5
MIN_SPEED = 45
NEGRO_MAX = 35.0
BLANCO_MIN = 65.0

# --- Perdida, busqueda y recuperacion ---
WHITE_LOST = 88.0
LOST_GRACE_MS = 800
SEARCH_TURN = 90
SEARCH_SWEEP_MS = 900
SEARCH_TIMEOUT_MS = 4000
RECOVER_SPEED = 55
RECOVER_TURN = 90
RECOVER_BAND = 10.0
RECOVER_TIMEOUT_MS = 1500

MAX_PERDIDAS = 8
DURACION_PRUEBA_MS = 15000

# --- Perfiles: nombre, velocidad mm/s, KP, KD ---
PERFILES = [
    ("SUAVE",       80, 1.0, 0.00),
    ("MEDIO",      100, 1.5, 0.15),
    ("FUERTE",     130, 2.0, 0.30),
    ("MUY FUERTE", 160, 2.5, 0.45),
]

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

def elegir_perfil(indice_inicial=0):
    indice = indice_inicial
    while True:
        nombre, velocidad, kp, kd = PERFILES[indice]
        hub.display.number(indice + 1)
        print("")
        print("Perfil %d: %s | v=%d mm/s | KP=%.2f | KD=%.2f" %
              (indice + 1, nombre, velocidad, kp, kd))
        print("IZQUIERDA: cambiar | DERECHA: probar")
        while True:
            pressed = hub.buttons.pressed()
            if Button.RIGHT in pressed:
                esperar_soltar(Button.RIGHT)
                return indice
            if Button.LEFT in pressed:
                esperar_soltar(Button.LEFT)
                indice = (indice + 1) % len(PERFILES)
                break
            wait(20)

def probar_perfil(indice):
    nombre, velocidad_base, kp, kd = PERFILES[indice]

    robot.stop()
    hub.display.char("R")
    hub.light.on(Color.GREEN)
    print("")
    print("=== PERFIL %s ===" % nombre)
    print("Coloca el sensor sobre la linea. Pulsa DERECHA.")
    print("Durante la prueba, IZQUIERDA detiene.")
    esperar_boton(Button.RIGHT)
    beep(800, 150)

    reloj = StopWatch()
    raw_f = sensor.reflection()

    ultimo_print = 0
    ultimo_display = 0

    last_e = 0.0
    deriv_f = 0.0
    last_turn = 0.0

    estado = "NORMAL"
    blanco_ms = 0
    perdidas = 0

    search_ms = 0
    search_phase = 0
    search_dir = 1
    recuperar_ms = 0

    tiempo_buscando = 0
    muestras = 0
    suma_abs = 0.0
    max_abs = 0.0
    max_turn = 0.0
    cambios = 0
    signo_previo = 0
    perdida = False
    inestable = False

    while reloj.time() < DURACION_PRUEBA_MS:
        pressed = hub.buttons.pressed()
        if Button.LEFT in pressed:
            robot.stop()
            esperar_soltar(Button.LEFT)
            print("Prueba detenida por el usuario.")
            break

        raw = sensor.reflection()
        raw_f = (1.0 - FILTRO) * raw_f + FILTRO * raw
        n = normalizar(raw_f, BLACK, WHITE)

        e = 0.0
        turn = 0.0

        if estado == "NORMAL":
            if n > WHITE_LOST:
                blanco_ms += LOOP_MS
            else:
                blanco_ms = 0

            if blanco_ms > LOST_GRACE_MS:
                perdidas += 1
                if perdidas > MAX_PERDIDAS:
                    robot.stop()
                    inestable = True
                    print("DEMASIADAS PERDIDAS. Prueba terminada.")
                    break

                estado = "BUSCAR"
                search_ms = 0
                search_phase = 0
                if last_turn > 0:
                    search_dir = 1
                elif last_turn < 0:
                    search_dir = -1
                robot.stop()
            else:
                e = n - TARGET_N
                if abs(e) < DEADBAND:
                    e = 0.0

                deriv = e - last_e
                deriv_f = 0.6 * deriv_f + 0.4 * deriv
                turn_obj = LADO * (kp * e + kd * deriv_f)
                turn_obj = limitar(turn_obj, -TURN_MAX, TURN_MAX)
                turn = last_turn + limitar(turn_obj - last_turn,
                                           -TURN_SLEW, TURN_SLEW)

                last_e = e
                last_turn = turn

                # Estadisticas solo cuando la linea esta a la vista
                if n < WHITE_LOST:
                    muestras += 1
                    ae = abs(e)
                    suma_abs += ae
                    if ae > max_abs:
                        max_abs = ae
                    if abs(turn) > max_turn:
                        max_turn = abs(turn)

                    signo = 0
                    if e > 0:
                        signo = 1
                    elif e < 0:
                        signo = -1
                    if signo != 0 and signo_previo != 0 and signo != signo_previo:
                        cambios += 1
                    if signo != 0:
                        signo_previo = signo

                velocidad = velocidad_base - abs(turn) * SPEED_REDUCTION
                velocidad = limitar(velocidad, MIN_SPEED, velocidad_base)
                robot.drive(velocidad, turn)

        elif estado == "BUSCAR":
            tiempo_buscando += LOOP_MS
            search_ms += LOOP_MS
            if search_ms > SEARCH_TIMEOUT_MS:
                robot.stop()
                perdida = True
                print("LINEA PERDIDA. Prueba terminada.")
                break

            fase = search_ms // SEARCH_SWEEP_MS
            if fase != search_phase:
                search_phase = fase
                search_dir = -search_dir

            turn = search_dir * SEARCH_TURN
            last_turn = turn
            robot.drive(0, turn)

            if n < TARGET_N + 10.0:
                estado = "RECUPERAR"
                recuperar_ms = 0
                robot.stop()

        else:  # RECUPERAR
            tiempo_buscando += LOOP_MS
            recuperar_ms += LOOP_MS
            turn = -LADO * RECOVER_TURN
            last_turn = turn
            robot.drive(RECOVER_SPEED, turn)

            if n > TARGET_N - RECOVER_BAND or recuperar_ms > RECOVER_TIMEOUT_MS:
                estado = "NORMAL"
                last_e = 0.0
                deriv_f = 0.0
                blanco_ms = 0

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

    robot.stop()

    # Resumen
    print("")
    print("=== RESULTADO %s ===" % nombre)
    if muestras > 0:
        print("Muestras con linea visible: %d" % muestras)
        print("Error medio: %.1f" % (suma_abs / muestras))
        print("Error maximo: %.1f" % max_abs)
        print("Cambios de direccion (zigzag): %d" % cambios)
        print("Giro maximo: %.0f deg/s" % max_turn)
    else:
        print("No se tomaron muestras con la linea visible.")
    print("Perdidas: %d" % perdidas)
    print("Tiempo buscando: %.1f s" % (tiempo_buscando / 1000.0))
    if perdida:
        print("Se perdio la linea.")
    if inestable:
        print("Control inestable: demasiadas perdidas.")
    print("Perfil: v=%d KP=%.2f KD=%.2f" % (velocidad_base, kp, kd))
    print("")
    print("Pulsa DERECHA para volver al menu.")
    hub.display.char("O")
    hub.light.off()
    beep(900, 200)
    esperar_boton(Button.RIGHT)

# --- Programa principal ---
print("=== PRUEBA DE PERFILES (UN SENSOR) ===")
cal = cargar_calibracion()
if cal is None:
    print("Usando calibracion por defecto.")
    print("Si los valores no sirven, ejecuta 02_calibracion.py.")
else:
    BLACK, WHITE = cal
    print("Calibracion cargada del hub.")
print("Negro=%.1f Blanco=%.1f | TARGET=%.1f | LADO=%d" %
      (BLACK, WHITE, TARGET_N, LADO))
print("Gracia=%d ms | Busqueda=%d ms" % (LOST_GRACE_MS, SEARCH_TIMEOUT_MS))

indice_actual = 0
while True:
    indice_actual = elegir_perfil(indice_actual)
    probar_perfil(indice_actual)
