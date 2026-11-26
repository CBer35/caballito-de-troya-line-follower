#!/usr/bin/env pybricks-micropython
# ============================================================
# 04 - PRUEBA DE PERFILES DE CONTROL (SENSORES SEPARADOS)
# Proyecto: seguidor de lineas "El Caballito de Troya"
# ============================================================
#
# GEOMETRIA:
# - Sensores separados, linea entre ellos.
# - Centrado: los dos ven blanco.
# - Un sensor ve negro: la linea esta de ese lado.
#
# ESTRATEGIA "TODO BLANCO":
# - Se avanza recto y mas lento solo WHITE_GRACE_MS.
# - Si sigue todo blanco, se deja de avanzar y se gira en el sitio
#   barriendo a izquierda/derecha para reencontrar la linea.
# - Si no aparece en LOST_TIMEOUT_MS, se detiene y reporta perdida.
#
# PERFILES:
# 1 SUAVE      - lento y estable
# 2 MEDIO      - equilibrio
# 3 FUERTE     - mas rapido, corrige mas
# 4 MUY FUERTE - para lineas amplias y buena traccion
#
# BOTONES:
# IZQUIERDA: cambia de perfil
# DERECHA: inicia la prueba
# IZQUIERDA durante la prueba: detiene
#
# AL FINAL IMPRIME:
# - error medio y maximo (solo cuando la linea esta visible)
# - numero de cambios de direccion (zigzag)
# - giro maximo
# - tiempo buscando y si se perdio la linea
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

# --- Calibracion por defecto (se sobrescribe con la guardada) ---
BLACK_L = 10.8
WHITE_L = 97.4
BLACK_R = 10.2
WHITE_R = 90.0

# --- Parametros generales ---
LOOP_MS = 10
DEADBAND = 6.0
TURN_MAX = 400.0
SPEED_REDUCTION = 0.5
MIN_SPEED = 70
NEGRO_MAX = 35.0
BLANCO_MIN = 65.0

# --- Estrategia "todo blanco" ---
WHITE_GRACE_MS = 1500
WHITE_SPEED_FACTOR = 0.60
TURN_MEMORY = 0.7
SEARCH_SWEEP_MS = 800
SEARCH_TURN = 120
LOST_TIMEOUT_MS = 3000

DURACION_PRUEBA_MS = 12000

# --- Perfiles: nombre, velocidad mm/s, KP, KD ---
PERFILES = [
    ("SUAVE",      120, 1.0, 0.00),
    ("MEDIO",      160, 2.0, 0.60),
    ("FUERTE",     200, 3.0, 1.20),
    ("MUY FUERTE", 240, 4.0, 1.80),
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
    print("Coloca el robot centrado sobre la linea. Pulsa DERECHA.")
    print("Durante la prueba, IZQUIERDA detiene.")
    esperar_boton(Button.RIGHT)
    beep(800, 150)

    reloj = StopWatch()
    ultimo_print = 0
    ultimo_display = 0

    last_error = 0.0
    deriv_f = 0.0
    last_turn = 0.0
    ultimo_signo = 0

    blanco_ms = 0
    search_phase = 0
    search_dir = 1
    tiempo_buscando = 0

    muestras_linea = 0
    suma_abs = 0.0
    max_abs = 0.0
    max_turn = 0.0
    cambios = 0
    signo_previo = 0
    perdida = False

    robot.drive(velocidad_base, 0)

    while reloj.time() < DURACION_PRUEBA_MS:
        pressed = hub.buttons.pressed()
        if Button.LEFT in pressed:
            robot.stop()
            esperar_soltar(Button.LEFT)
            print("Prueba detenida por el usuario.")
            break

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
            tiempo_buscando += LOOP_MS
            if blanco_ms > LOST_TIMEOUT_MS:
                robot.stop()
                perdida = True
                print("LINEA PERDIDA. Prueba terminada.")
                break

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
                last_error = 0.0
                deriv_f = 0.0
                factor_velocidad = WHITE_SPEED_FACTOR
            else:
                # --- CONTROL NORMAL ---
                error = nl - nr
                if abs(error) < DEADBAND:
                    error = 0.0

                if todo_negro:
                    error = 0.0
                    deriv_f = 0.0

                deriv = error - last_error
                deriv_f = 0.6 * deriv_f + 0.4 * deriv
                turn = kp * error + kd * deriv_f
                turn = limitar(turn, -TURN_MAX, TURN_MAX)
                last_turn = turn
                last_error = error

                if error > 0.5:
                    ultimo_signo = 1
                elif error < -0.5:
                    ultimo_signo = -1

                # Estadisticas solo cuando la linea esta visible
                muestras_linea += 1
                ae = abs(error)
                suma_abs += ae
                if ae > max_abs:
                    max_abs = ae
                if abs(turn) > max_turn:
                    max_turn = abs(turn)

                signo = 0
                if error > 0:
                    signo = 1
                elif error < 0:
                    signo = -1
                if signo != 0 and signo_previo != 0 and signo != signo_previo:
                    cambios += 1
                if signo != 0:
                    signo_previo = signo

                factor_velocidad = 1.0

            velocidad = velocidad_base - abs(turn) * SPEED_REDUCTION
            velocidad = limitar(velocidad, MIN_SPEED, velocidad_base)
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

    robot.stop()

    # Resumen
    print("")
    print("=== RESULTADO %s ===" % nombre)
    if muestras_linea > 0:
        print("Muestras con linea visible: %d" % muestras_linea)
        print("Error medio: %.1f" % (suma_abs / muestras_linea))
        print("Error maximo: %.1f" % max_abs)
        print("Cambios de direccion (zigzag): %d" % cambios)
        print("Giro maximo: %.0f deg/s" % max_turn)
    else:
        print("No se tomaron muestras con la linea visible.")
    print("Tiempo buscando: %.1f s" % (tiempo_buscando / 1000.0))
    if perdida:
        print("Se perdio la linea.")
    print("Perfil: v=%d KP=%.2f KD=%.2f" % (velocidad_base, kp, kd))
    print("")
    print("Pulsa DERECHA para volver al menu.")
    hub.display.char("O")
    hub.light.off()
    beep(900, 200)
    esperar_boton(Button.RIGHT)

# --- Programa principal ---
print("=== PRUEBA DE PERFILES (SENSORES SEPARADOS) ===")
cal = cargar_calibracion()
if cal is None:
    print("Usando calibracion por defecto.")
    print("Si los valores no sirven, ejecuta 02_calibracion.py.")
else:
    BLACK_L, WHITE_L, BLACK_R, WHITE_R = cal
    print("Calibracion cargada del hub.")
print("Negro L=%.1f R=%.1f | Blanco L=%.1f R=%.1f" %
      (BLACK_L, BLACK_R, WHITE_L, WHITE_R))
print("Gracia en blanco=%d ms | Busqueda=%d ms" %
      (WHITE_GRACE_MS, LOST_TIMEOUT_MS - WHITE_GRACE_MS))

indice_actual = 0
while True:
    indice_actual = elegir_perfil(indice_actual)
    probar_perfil(indice_actual)
