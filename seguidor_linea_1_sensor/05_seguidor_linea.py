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
# CAMBIO v1.1 (huecos y esquinas, SIN tocar el control):
# - Se agregaron SALTAR y RETROCESO para lineas discontinuas:
#   al ver blanco, avanza SALTO_MM recto; si la linea no aparece,
#   retrocede RETRO_MM; si aun no aparece, recien busca.
# - BUSCAR usa el rumbo y el giro CON SIGNO que traia el robot justo
#   antes del blanco, y barre 90 grados a cada lado (180 en total,
#   sin vuelta completa). Si no la ve, vuelve a ese rumbo, avanza un
#   poco y repite el barrido, sin detenerse, hasta encontrarla.
#   Asi tambien cubre las esquinas antihorarias y no se vuelve por
#   donde vino en las colinas. Antes el PD giraba a la derecha
#   durante la espera, la busqueda era de 360 y siempre terminaba
#   yendo hacia la derecha.
# - El control NORMAL (90 mm/s, KP 1.2, KD 0.10, banda 12) es el
#   mismo de antes: la precision en recta y curvas no cambia.
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
#       SALTAR    -> hueco: avanza recto SALTO_MM (" > " en pantalla)
#       RETROCESO -> no aparecio: retrocede RETRO_MM (" < " en pantalla)
#       BUSCAR    -> barre 180; si no ve, vuelve al rumbo, avanza y repite
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

# Busqueda de 180 grados: barre medio giro a cada lado del rumbo
# en que se perdio. No da la vuelta completa, asi no se vuelve por
# donde vino cuando la linea sigue adelante (colinas, esquinas, huecos).
# Si no la encuentra, vuelve a ese rumbo, avanza un poco y repite.
SEARCH_TURN = 90       # deg/s durante el barrido
SEARCH_ANGLE = 180.0   # arco total barrido (90 a cada lado)
SEARCH_AVANCE_MM = 120 # avance recto entre un barrido y el siguiente
SEARCH_AVANCE_SPEED = 60  # mm/s durante ese avance
SEARCH_VUELTA_KP = 3.0 # para volver al rumbo previo
SEARCH_MAX_MS = 0      # 0 = buscar sin limite hasta encontrar la linea

# Recuperacion despues de encontrar la linea
RECOVER_SPEED = 55     # mm/s
RECOVER_TURN = 90      # deg/s hacia el borde elegido
RECOVER_BAND = 10.0    # sale de recuperar cuando n supera TARGET - banda
RECOVER_TIMEOUT_MS = 1500

# --- Linea discontinua: avanzar un poco y, si no hay linea, retroceder ---
# No cambia el control NORMAL: solo actua cuando el sensor ve blanco.
GAP_CONFIRM_MS = 80      # blanco continuo antes de intentar el salto
GAP_CERCA_MS = 100       # venia siguiendo el borde (no en plena curva)
GAP_CERCA_ERROR = 30.0   # "cerca del borde" = |error| menor que esto
GAP_TURN_MAX = 35.0      # giro medio maximo para considerar que iba recto
SALTO_MM = 45            # primer avance recto para pasar el hueco, mm
SALTO_EXTRA_MM = 20      # cuanto mas avanza en cada reintento
SALTO_MAX_MM = 90        # tope del avance progresivo
SALTO_SPEED = 85         # mm/s durante el avance
SALTO_TIMEOUT_MS = 2000  # seguridad del avance
RETRO_MM = 50            # retroceso maximo si no aparece la linea
RETRO_SPEED = 50         # mm/s durante el retroceso
RETRO_TIMEOUT_MS = 2000  # seguridad del retroceso
MAX_INTENTOS_SALTO = 3   # reintentos antes de buscar
GAP_OK_RESET_MS = 1200   # linea solida: se olvida que venia de huecos
CORNER_TURN_MIN = 15.0   # giro previo que delata una esquina (no un hueco)





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
    search_base = 0.0
    search_objetivo = 0.0
    search_fase = "INICIO"
    search_paso = 1
    search_avance_inicio = 0.0

    recuperar_ms = 0

    # Linea discontinua / esquinas
    salto_inicio = 0.0
    salto_ms = 0
    salto_dist = SALTO_MM
    intentos_salto = 0
    gap_ok = False
    gap_ok_ms = 0
    retry_gap_ms = 0
    retro_inicio = 0.0
    retro_ms = 0
    cerca_ms = 0
    turn_medio = 0.0
    giro_previo = 0.0
    giro_onset = 0.0
    angulo_onset = 0.0
    estaba_blanco = False
    no_saltar_ms = 0
    e_res = 0.0

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

        # --- Informacion para distinguir hueco / esquina / curva ---
        # turn_medio y cerca_ms se congelan apenas hay blanco: interesa
        # como venia el robot ANTES del hueco.
        if n < BLANCO_MIN:
            turn_medio = 0.90 * turn_medio + 0.10 * abs(last_turn)
            # Giro CON SIGNO antes del blanco: dice hacia donde iba la
            # linea (izquierda/derecha) cuando se perdio.
            giro_previo = 0.90 * giro_previo + 0.10 * last_turn
            if abs(n - TARGET_N) <= GAP_CERCA_ERROR:
                cerca_ms += LOOP_MS
                if cerca_ms > 2000:
                    cerca_ms = 2000
            else:
                cerca_ms = 0

        # Se guarda el giro que traia justo al entrar al blanco.
        if n > BLANCO_MIN:
            if not estaba_blanco:
                giro_onset = giro_previo
                angulo_onset = robot.angle()
            estaba_blanco = True
        else:
            estaba_blanco = False

        if no_saltar_ms > 0:
            no_saltar_ms -= LOOP_MS
        if retry_gap_ms > 0:
            retry_gap_ms -= LOOP_MS

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

            # Si lleva un rato sin huecos, se olvida del modo discontinuo.
            if n < WHITE_LOST:
                gap_ok_ms += LOOP_MS
                if gap_ok_ms > GAP_OK_RESET_MS:
                    gap_ok = False
                    intentos_salto = 0
                    retry_gap_ms = 0
            else:
                gap_ok_ms = 0

            # 1) Hueco en recta: avanzar un poco sin cambiar el control
            #    normal. No se activa en curvas/esquinas (turn_medio alto).
            if (blanco_ms > GAP_CONFIRM_MS and no_saltar_ms <= 0 and
                    (cerca_ms >= GAP_CERCA_MS or retry_gap_ms > 0) and
                    turn_medio <= GAP_TURN_MAX):
                estado = "SALTAR"
                salto_inicio = robot.distance()
                salto_ms = 0
                blanco_ms = 0
                if gap_ok:
                    salto_dist = SALTO_MM + intentos_salto * SALTO_EXTRA_MM
                    if salto_dist > SALTO_MAX_MM:
                        salto_dist = SALTO_MAX_MM
                else:
                    salto_dist = SALTO_MM
                # Direccion de respaldo: la del giro que traia antes del
                # blanco; si iba recto, hacia el lado de la linea (LADO).
                if giro_onset < -CORNER_TURN_MIN:
                    search_dir = -1
                elif giro_onset > CORNER_TURN_MIN:
                    search_dir = 1
                else:
                    search_dir = LADO

            # 2) Perdida sostenida: buscar. La direccion inicial sale
            #    del giro previo; luego el barrido cubre los dos lados.
            elif blanco_ms > LOST_GRACE_MS:
                perdidas += 1
                if perdidas > MAX_PERDIDAS:
                    robot.stop()
                    return "inestable"

                estado = "BUSCAR"
                search_ms = 0
                search_fase = "INICIO"
                normal_ms = 0
                cerca_ms = 0
                gap_ok = False
                retry_gap_ms = 0
                intentos_salto = 0
                if giro_onset < -CORNER_TURN_MIN:
                    search_dir = -1
                elif giro_onset > CORNER_TURN_MIN:
                    search_dir = 1
                elif last_turn > 5:
                    search_dir = 1
                elif last_turn < -5:
                    search_dir = -1
                else:
                    search_dir = LADO
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

        elif estado == "SALTAR":
            # --- Hueco: avanzar recto un poco y mirar si reaparece ---
            salto_ms += LOOP_MS
            turn = last_turn + limitar(0.0 - last_turn,
                                       -TURN_SLEW, TURN_SLEW)
            last_turn = turn
            robot.drive(SALTO_SPEED, turn)

            if n <= TARGET_N + 10.0:
                estado = "NORMAL"
                e_res = n - TARGET_N
                if abs(e_res) < DEADBAND:
                    e_res = 0.0
                last_e = e_res
                deriv_f = 0.0
                last_turn = 0.0
                blanco_ms = 0
                normal_ms = 0
                cerca_ms = 0
                gap_ok = True
                gap_ok_ms = 0
                retry_gap_ms = 0
                intentos_salto = 0
            elif (robot.distance() - salto_inicio >= salto_dist or
                    salto_ms > SALTO_TIMEOUT_MS):
                estado = "RETROCESO"
                retro_inicio = robot.distance()
                retro_ms = 0
                intentos_salto += 1
                robot.stop()

        elif estado == "RETROCESO":
            # --- No aparecio: volver hacia atras sin perder la linea ---
            retro_ms += LOOP_MS
            last_turn = 0.0
            robot.drive(-RETRO_SPEED, 0)

            if n <= TARGET_N + 10.0:
                # Encontro la linea anterior. Si ya intento varias veces,
                # el hueco es demasiado largo: buscar. Si no, volver a
                # NORMAL para reintentar con un avance mas largo.
                if intentos_salto >= MAX_INTENTOS_SALTO:
                    perdidas += 1
                    if perdidas > MAX_PERDIDAS:
                        robot.stop()
                        return "inestable"
                    estado = "BUSCAR"
                    search_ms = 0
                    search_fase = "INICIO"
                    cerca_ms = 0
                    gap_ok = False
                    retry_gap_ms = 0
                    intentos_salto = 0
                else:
                    estado = "NORMAL"
                    e_res = n - TARGET_N
                    if abs(e_res) < DEADBAND:
                        e_res = 0.0
                    last_e = e_res
                    deriv_f = 0.0
                    blanco_ms = 0
                    normal_ms = 0
                    turn_medio = 0.0
                    if gap_ok:
                        # Venia de una seccion discontinua: reintentar
                        # el hueco con un salto mas largo.
                        cerca_ms = GAP_CERCA_MS
                        retry_gap_ms = 1000
                        no_saltar_ms = 0
                    else:
                        # Era una esquina/curva: dejar que el PD la siga.
                        cerca_ms = 0
                        retry_gap_ms = 0
                        no_saltar_ms = 1500
                robot.stop()
            elif (retro_inicio - robot.distance() >= RETRO_MM or
                    retro_ms > RETRO_TIMEOUT_MS):
                perdidas += 1
                if perdidas > MAX_PERDIDAS:
                    robot.stop()
                    return "inestable"
                estado = "BUSCAR"
                search_ms = 0
                search_fase = "INICIO"
                cerca_ms = 0
                gap_ok = False
                retry_gap_ms = 0
                intentos_salto = 0
                robot.stop()

        elif estado == "BUSCAR":
            # --- Ciclo: barrido 180 -> volver al rumbo -> avanzar ---
            search_ms += LOOP_MS
            if SEARCH_MAX_MS > 0 and search_ms > SEARCH_MAX_MS:
                robot.stop()
                return "perdido"

            if search_fase == "INICIO":
                # Rumbo que traia ANTES del blanco: es hacia donde
                # conviene avanzar si el barrido no encuentra nada.
                search_base = angulo_onset
                search_paso = 1
                search_fase = "BARRIDO"
                search_objetivo = (search_base +
                                   search_dir * (SEARCH_ANGLE / 2.0))
                search_avance_inicio = robot.distance()

            angulo = robot.angle()

            if search_fase == "BARRIDO":
                if (angulo - search_objetivo) * search_dir >= 0.0:
                    if search_paso == 1:
                        # Termino el primer lado: barrer el otro.
                        search_paso = 2
                        search_dir = -search_dir
                        search_objetivo = (search_base +
                                           search_dir * (SEARCH_ANGLE / 2.0))
                    else:
                        # Termino el barrido de 180: volver al rumbo.
                        search_fase = "VOLVER"
                        search_objetivo = search_base
                        last_turn = 0.0
                        turn = 0.0
                        robot.stop()
                else:
                    turn_obj = search_dir * SEARCH_TURN
                    turn = last_turn + limitar(turn_obj - last_turn,
                                               -TURN_SLEW, TURN_SLEW)
                    last_turn = turn
                    robot.drive(0, turn)

            elif search_fase == "VOLVER":
                restante = search_objetivo - angulo
                if abs(restante) <= 3.0:
                    # Ya mira hacia el rumbo previo: avanzar un poco.
                    search_fase = "AVANZAR"
                    search_avance_inicio = robot.distance()
                    last_turn = 0.0
                    turn = 0.0
                    robot.drive(SEARCH_AVANCE_SPEED, 0)
                else:
                    turn_obj = limitar(SEARCH_VUELTA_KP * restante,
                                       -SEARCH_TURN, SEARCH_TURN)
                    turn = last_turn + limitar(turn_obj - last_turn,
                                               -TURN_SLEW, TURN_SLEW)
                    last_turn = turn
                    robot.drive(0, turn)

            else:  # AVANZAR
                last_turn = 0.0
                turn = 0.0
                robot.drive(SEARCH_AVANCE_SPEED, 0)
                if (robot.distance() - search_avance_inicio >=
                        SEARCH_AVANCE_MM):
                    # Avanzo lo suficiente: repetir el barrido, esta vez
                    # empezando por el otro lado.
                    search_fase = "BARRIDO"
                    search_paso = 1
                    search_dir = -search_dir
                    search_objetivo = (search_base +
                                       search_dir * (SEARCH_ANGLE / 2.0))
                    search_avance_inicio = robot.distance()
                    robot.stop()

            # Si ya ve negro o el borde, pasar a recuperar (en
            # cualquiera de las tres fases).
            if n < TARGET_N + 10.0:
                estado = "RECUPERAR"
                recuperar_ms = 0
                last_turn = 0.0
                turn = 0.0
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
                cerca_ms = 0
                turn_medio = 0.0

        t = reloj.time()

        if t - ultimo_display >= 100:
            if estado == "SALTAR":
                hub.display.char(">")
                hub.light.on(Color.BLUE)
            elif estado == "RETROCESO":
                hub.display.char("<")
                hub.light.on(Color.BLUE)
            elif estado == "BUSCAR":
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
print("Gracia=%d ms | Busqueda: 180 grados, avance %d mm por ciclo" %
      (LOST_GRACE_MS, SEARCH_AVANCE_MM))
print("Huecos: salto=%d mm (+%d por reintento) | retroceso=%d mm" %
      (SALTO_MM, SALTO_EXTRA_MM, RETRO_MM))
print("Busqueda: 180 grados (90 a cada lado), sin vuelta completa.")
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
        print("Busqueda detenida por SEARCH_MAX_MS.")
        print("Pon SEARCH_MAX_MS = 0 para buscar sin limite.")
        print("Sube SALTO_MM o SEARCH_AVANCE_MM si se pierde seguido.")
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
