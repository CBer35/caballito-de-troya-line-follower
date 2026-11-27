"""Simulador offline del seguidor de linea de 1 sensor.

Herramienta de PC (NO se sube al hub). Sirve para comparar el programa
actual con la version nueva sin gastar bateria ni pista: crea modulos
falsos de ``pybricks``, modela la pista, el robot y el sensor, y ejecuta
el archivo .py real tal cual (con su ``while True`` y sus botones).

Uso:
    python sim/simular_seguidor.py
    python sim/simular_seguidor.py 05_seguidor_linea.py
    python sim/simular_seguidor.py sim/_baseline_05.py

Variables de entorno opcionales:
    SIM_ESC=recta,curvas     solo esos escenarios
    SIM_TRAZA=discontinua    muestra la traza de ese escenario

El programa simulado NO ve diferencias con Pybricks salvo que los motores
responden con una constante de tiempo, hay una deriva de rumbo (ruedas no
perfectas) y el sensor tiene ruido. Las metricas se calculan con la
posicion real del sensor sobre la pista.
"""

import contextlib
import io
import math
import os
import random
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Pista
# ---------------------------------------------------------------------------
class Pista:
    """Pista formada por rectas y arcos, con huecos (linea discontinua)."""

    def __init__(self, tramos, huecos=(), ancho=19.0, borde_suave=1.5,
                 ruido=1.2, semilla=7):
        self.ancho = ancho
        self.hw = ancho / 2.0
        self.borde_suave = borde_suave
        self.ruido = ruido
        self.rnd = random.Random(semilla)
        self.huecos = list(huecos)
        self.pts = []          # (x, y, theta, s)
        self.largo = 0.0
        self._construir(tramos)
        self._marcar_huecos()

    # -- construccion -------------------------------------------------------
    def _construir(self, tramos):
        x = y = th = s = 0.0
        for tramo in tramos:
            tipo = tramo[0]
            if tipo == "recta":
                largo = float(tramo[1])
            else:
                radio = float(tramo[1])
                grados = float(tramo[2])
                largo = abs(math.radians(grados)) * abs(radio)
            pasos = max(1, int(round(largo)))
            ds = largo / pasos
            if tipo == "recta":
                curv = 0.0
            else:
                curv = math.radians(float(tramo[2])) / largo
            for _ in range(pasos):
                self.pts.append((x, y, th, s))
                x += math.cos(th) * ds
                y += math.sin(th) * ds
                th += curv * ds
                s += ds
        self.pts.append((x, y, th, s))
        self.largo = s

    def _marcar_huecos(self):
        self.hueco_en = [False] * len(self.pts)
        for i, p in enumerate(self.pts):
            s = p[3]
            self.hueco_en[i] = any(a <= s < b for a, b in self.huecos)

    # -- consultas ----------------------------------------------------------
    def punto(self, s):
        """Punto de la linea central en la longitud de arco s."""
        i = int(round(s))
        i = max(0, min(len(self.pts) - 1, i))
        return self.pts[i]

    def cercano(self, x, y, cache=0, ventana=180):
        """Punto de la pista mas cercano y distancia lateral con signo.

        d > 0 significa a la IZQUIERDA del sentido de avance.
        """
        n = len(self.pts)
        lo = max(0, cache - ventana)
        hi = min(n, cache + ventana)
        mejor = 0
        mejor_d2 = 1e30
        for i in range(lo, hi):
            px, py, _th, _s = self.pts[i]
            dx = x - px
            dy = y - py
            d2 = dx * dx + dy * dy
            if d2 < mejor_d2:
                mejor_d2 = d2
                mejor = i
        if mejor_d2 > 40.0 * 40.0:
            for i in range(0, n, 3):
                px, py, _th, _s = self.pts[i]
                dx = x - px
                dy = y - py
                d2 = dx * dx + dy * dy
                if d2 < mejor_d2:
                    mejor_d2 = d2
                    mejor = i

        px, py, th, s = self.pts[mejor]
        dx = x - px
        dy = y - py
        # normal izquierda = (-sin, cos)
        d = -math.sin(th) * dx + math.cos(th) * dy
        along = math.cos(th) * dx + math.sin(th) * dy

        fuera = False
        if mejor == n - 1 and along > 0.0:
            fuera = True
        elif mejor == 0 and along < -0.5:
            fuera = True

        if fuera:
            hueco = True
        else:
            hueco = self.hueco_en[mejor]
        return mejor, s, d, hueco, fuera

    def reflectancia(self, x, y, cache=0):
        idx, s, d, hueco, fuera = self.cercano(x, y, cache)
        if fuera or hueco:
            n = 100.0
        else:
            a = abs(d)
            lo = self.hw - self.borde_suave
            hi = self.hw + self.borde_suave
            if a <= lo:
                n = 0.0
            elif a >= hi:
                n = 100.0
            else:
                t = (a - lo) / (hi - lo)
                n = 100.0 * (3.0 * t * t - 2.0 * t * t * t)
        if self.ruido > 0.0:
            n += self.rnd.gauss(0.0, self.ruido)
        return max(0.0, min(100.0, n)), idx, s, d, hueco, fuera


# ---------------------------------------------------------------------------
# Robot
# ---------------------------------------------------------------------------
class RobotSim:
    TAU_V = 0.060     # respuesta de la velocidad (s)
    TAU_W = 0.085     # respuesta del giro (s)
    AVANCE_SENSOR = 30.0
    DERIVA_W = -1.8   # deg/s de giro parasito (ruedas no perfectas)

    def __init__(self, pista, s0=60.0, d0=9.5, giro0=0.0):
        self.pista = pista
        px, py, th, _s = pista.punto(s0)
        th += math.radians(giro0)
        # Sensor en el borde: centro de la linea + normal * d0
        sx = px - math.sin(th) * d0
        sy = py + math.cos(th) * d0
        # El centro del robot queda AVANCE_SENSOR detras del sensor.
        self.x = sx - math.cos(th) * self.AVANCE_SENSOR
        self.y = sy - math.sin(th) * self.AVANCE_SENSOR
        self.th = th
        self.th0 = th
        self.v = 0.0
        self.w = 0.0
        self.v_cmd = 0.0
        self.w_cmd = 0.0
        self.dist = 0.0
        self.cache = int(round(s0))

    def avanzar(self, dt):
        self.v += (self.v_cmd - self.v) * min(1.0, dt / self.TAU_V)
        self.w += (self.w_cmd - self.w) * min(1.0, dt / self.TAU_W)
        # w positivo = derecha. La deriva simula ruedas que no son iguales.
        self.th += -math.radians(self.w + self.DERIVA_W) * dt
        self.x += self.v * math.cos(self.th) * dt
        self.y += self.v * math.sin(self.th) * dt
        self.dist += self.v * dt

    def sensor(self):
        return (self.x + math.cos(self.th) * self.AVANCE_SENSOR,
                self.y + math.sin(self.th) * self.AVANCE_SENSOR)

    def angulo(self):
        """Angulo de DriveBase: positivo a la derecha, acumulado."""
        return -math.degrees(self.th - self.th0)


# ---------------------------------------------------------------------------
# Fin de simulacion
# ---------------------------------------------------------------------------
class FinSimulacion(Exception):
    pass


# ---------------------------------------------------------------------------
# Escenario
# ---------------------------------------------------------------------------
class Escenario:
    def __init__(self, nombre, pista, s0=60.0, d0=9.5, lado=1, giro0=0.0,
                 meta_dist=None, max_ms=20000, descripcion=""):
        self.nombre = nombre
        self.pista = pista
        self.s0 = s0
        self.d0 = d0
        self.lado = lado
        self.giro0 = giro0
        self.meta_dist = meta_dist
        self.max_ms = max_ms
        self.descripcion = descripcion


def pista_recta():
    return Pista([("recta", 1600.0)])


def pista_curvas():
    return Pista([("recta", 250.0),
                  ("arco", 250.0, 90.0),
                  ("recta", 250.0),
                  ("arco", 250.0, -90.0),
                  ("recta", 350.0)])


def pista_curva_cerrada():
    return Pista([("recta", 200.0),
                  ("arco", 120.0, 180.0),
                  ("recta", 300.0)])


def pista_esquina():
    return Pista([("recta", 350.0),
                  ("arco", 18.0, 90.0),
                  ("recta", 350.0)])


def pista_esquina_derecha():
    return Pista([("recta", 350.0),
                  ("arco", 18.0, -90.0),
                  ("recta", 350.0)])


def pista_curva_90():
    return Pista([("recta", 300.0),
                  ("arco", 60.0, 90.0),
                  ("recta", 350.0)])


def pista_discontinua():
    # 70 mm de linea, 30 mm de hueco, repetido.
    huecos = []
    s = 100.0
    while s < 1200.0:
        huecos.append((s, s + 30.0))
        s += 100.0
    return Pista([("recta", 1500.0)], huecos=huecos)


def pista_discontinua_variable():
    # Alterna huecos de 30 mm y de 60 mm (como una pista aleatoria).
    huecos = [(100.0, 130.0), (180.0, 240.0),
              (300.0, 330.0), (380.0, 440.0),
              (500.0, 530.0), (580.0, 640.0),
              (700.0, 730.0), (780.0, 840.0)]
    return Pista([("recta", 1500.0)], huecos=huecos)


def pista_colina():
    # Colina suave: sube y baja, como los bultos de la pista.
    return Pista([("recta", 200.0),
                  ("arco", 40.0, 60.0),
                  ("arco", -40.0, 60.0),
                  ("arco", -40.0, 60.0),
                  ("arco", 40.0, 60.0),
                  ("recta", 300.0)])


def pista_hueco_largo():
    return Pista([("recta", 1400.0)], huecos=[(350.0, 500.0)])


def escenarios():
    return [
        Escenario("recta", pista_recta(), meta_dist=1300.0,
                  descripcion="recta larga a maxima velocidad"),
        Escenario("curvas", pista_curvas(), meta_dist=800.0,
                  descripcion="curvas de 250 mm de radio"),
        Escenario("curva_cerrada", pista_curva_cerrada(), meta_dist=450.0,
                  descripcion="horquilla de 120 mm de radio"),
        Escenario("curva_90", pista_curva_90(), meta_dist=650.0,
                  descripcion="curva de 90 grados, radio 60 mm"),
        Escenario("esquina", pista_esquina(), meta_dist=600.0,
                  descripcion="esquina de 90 grados muy cerrada (izquierda)"),
        Escenario("esquina_der", pista_esquina_derecha(), meta_dist=600.0,
                  descripcion="esquina de 90 grados muy cerrada (derecha)"),
        Escenario("discontinua", pista_discontinua(), meta_dist=1350.0,
                  descripcion="linea discontinua: 70 mm linea / 30 mm hueco"),
        Escenario("discontinua_var", pista_discontinua_variable(),
                  meta_dist=1350.0,
                  descripcion="huecos alternos de 30 y 60 mm"),
        Escenario("colina", pista_colina(), meta_dist=550.0,
                  descripcion="colina suave de 60 grados por arco"),
        Escenario("hueco_largo", pista_hueco_largo(), meta_dist=1250.0,
                  descripcion="hueco de 150 mm"),
        Escenario("perdida", pista_recta(), s0=300.0, d0=60.0,
                  max_ms=14000,
                  descripcion="empieza 50 mm fuera de la linea y debe buscarla"),
        Escenario("perdida_cerca", pista_recta(), s0=300.0, d0=25.0,
                  max_ms=14000,
                  descripcion="empieza 15 mm fuera del borde y debe buscarla"),
    ]


# ---------------------------------------------------------------------------
# Simulacion
# ---------------------------------------------------------------------------
class Sim:
    def __init__(self, escenario):
        self.esc = escenario
        self.pista = escenario.pista
        self.robot = RobotSim(self.pista, escenario.s0, escenario.d0,
                              escenario.giro0)
        self.t_ms = 0
        self.max_ms = escenario.max_ms
        self.inicio = None
        self.fin = None
        self.muestras = []
        self.traza = []
        self.chars = []
        self.char_actual = "R"
        self.botones = set()
        self.motivo_fin = "tiempo"
        self.n_muestras = 0
        self.ultimo_char = "R"

    # -- sensor -------------------------------------------------------------
    def leer_sensor(self):
        if self.inicio is None:
            self.inicio = self.t_ms
        sx, sy = self.robot.sensor()
        n, idx, s, d, hueco, fuera = self.pista.reflectancia(
            sx, sy, self.robot.cache)
        self.robot.cache = idx
        self.muestras.append((self.t_ms, n, d, s, hueco, fuera,
                              self.robot.v, self.robot.w,
                              self.robot.angulo(), self.char_actual))
        if self.t_ms % 100 == 0:
            self.traza.append((self.t_ms, self.char_actual, n, d, s,
                               self.robot.v, self.robot.w,
                               self.robot.angulo(), self.robot.dist,
                               self.robot.v_cmd, self.robot.w_cmd))
        self.n_muestras += 1
        return n

    # -- tiempo -------------------------------------------------------------
    def avanzar(self, ms):
        ms = int(round(ms))
        for _ in range(ms):
            self.robot.avanzar(0.001)
            self.t_ms += 1
            if (self.esc.meta_dist is not None and
                    self.robot.dist >= self.esc.meta_dist):
                raise FinSimulacion("meta")
            if self.t_ms >= self.max_ms:
                raise FinSimulacion("tiempo")

    # -- display ------------------------------------------------------------
    def mostrar(self, ch):
        self.ultimo_char = ch
        self.char_actual = ch
        if not self.chars or self.chars[-1][1] != ch:
            self.chars.append((self.t_ms, ch))
        if ch == "E" and self.inicio is not None:
            raise FinSimulacion("error")
        if ch == "S" and self.inicio is not None:
            raise FinSimulacion("usuario")

    # -- metrics ------------------------------------------------------------
    def resumen(self):
        fin = self.fin if self.fin is not None else self.t_ms
        ini = self.inicio if self.inicio is not None else 0
        dur = max(1, fin - ini)
        lado = self.esc.lado
        hw = self.pista.hw

        vis = []
        for m in self.muestras:
            t, n, d, s, hueco, fuera, v, w, ang, ch = m
            if hueco or fuera or n >= 90.0:
                continue
            vis.append(m)

        errores = [m[2] - lado * hw for m in vis]
        if errores:
            rms = math.sqrt(sum(e * e for e in errores) / len(errores))
            max_e = max(abs(e) for e in errores)
        else:
            rms = max_e = float("nan")

        # Duracion por estado y barridos de busqueda, con la linea de
        # tiempo real de las muestras (cada 10 ms).
        tiempos = {"normal": 0, "cruzar": 0, "buscar": 0, "recuperar": 0,
                   "otro": 0}
        barridos = []
        barrido_actual = None
        for i, m in enumerate(self.muestras):
            t, n, d, s, hueco, fuera, v, w, ang, ch = m
            t2 = self.muestras[i + 1][0] if i + 1 < len(self.muestras) else fin
            dt = max(0, t2 - t)
            if ch in ("=", ">", "<"):
                tiempos["cruzar"] += dt
            elif ch == "!":
                tiempos["buscar"] += dt
                if barrido_actual is None:
                    barrido_actual = [ang, ang]
                else:
                    barrido_actual[0] = min(barrido_actual[0], ang)
                    barrido_actual[1] = max(barrido_actual[1], ang)
            elif ch == "+":
                tiempos["recuperar"] += dt
            elif ch in ("|", "N", "B"):
                tiempos["normal"] += dt
            else:
                tiempos["otro"] += dt
            if ch != "!" and barrido_actual is not None:
                barridos.append(barrido_actual[1] - barrido_actual[0])
                barrido_actual = None
        if barrido_actual is not None:
            barridos.append(barrido_actual[1] - barrido_actual[0])
        barrido = max(barridos) if barridos else 0.0

        vel = [m[6] for m in self.muestras if m[0] >= ini]
        vel_media = sum(vel) / len(vel) if vel else 0.0

        # Cambios de signo del giro (zigzag) en estado normal
        giros = 0
        signo_prev = 0
        for m in self.muestras:
            if m[9] in ("|", "N", "B") and abs(m[7]) > 15:
                signo = 1 if m[7] > 0 else -1
                if signo_prev != 0 and signo != signo_prev:
                    giros += 1
                signo_prev = signo

        return {
            "nombre": self.esc.nombre,
            "descripcion": self.esc.descripcion,
            "duracion": dur,
            "distancia": self.robot.dist,
            "vel_media": vel_media,
            "rms": rms,
            "max": max_e,
            "tiempos": tiempos,
            "barrido": barrido,
            "busquedas": len(barridos),
            "giros": giros,
            "final": self.ultimo_char,
            "motivo": self.motivo_fin,
            "muestras": len(self.muestras),
            "chars": "".join(c for _t, c in self.chars),
        }


# ---------------------------------------------------------------------------
# Stubs de pybricks
# ---------------------------------------------------------------------------
class Button:
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"


class Color:
    BLACK = "BLACK"
    BLUE = "BLUE"
    GREEN = "GREEN"
    RED = "RED"
    WHITE = "WHITE"
    YELLOW = "YELLOW"


class Port:
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class Direction:
    CLOCKWISE = "CW"
    COUNTERCLOCKWISE = "CCW"


class Motor:
    def __init__(self, port, direction=None):
        self.port = port
        self.direction = direction
        self.angle = 0


class _Display:
    def __init__(self, sim):
        self.sim = sim

    def char(self, ch, *a, **k):
        self.sim.mostrar(ch)

    def number(self, n, *a, **k):
        pass

    def text(self, txt, *a, **k):
        pass

    def off(self):
        pass

    def pixel(self, *a, **k):
        pass


class _Light:
    def __init__(self, sim):
        self.sim = sim

    def on(self, color):
        pass

    def off(self):
        pass


class _Speaker:
    def beep(self, *a, **k):
        pass


class _Buttons:
    def __init__(self, sim):
        self.sim = sim

    def pressed(self):
        return set(self.sim.botones)


class _IMU:
    def __init__(self, sim):
        self.sim = sim

    def heading(self):
        a = self.sim.robot.angulo()
        while a >= 180.0:
            a -= 360.0
        while a < -180.0:
            a += 360.0
        return a

    def reset_heading(self, angle=0):
        pass

    def angle(self):
        return self.sim.robot.angulo()

    def angular_velocity(self, axis=None):
        w = self.sim.robot.w
        return (0.0, 0.0, w)

    def acceleration(self, axis=None):
        return (0.0, 0.0, 0.0)

    def up(self):
        return (0, 0, 1)

    def tilt(self):
        return (0.0, 0.0)


class _System:
    def __init__(self, sim):
        self.sim = sim

    def storage(self, offset, read=0, write=b""):
        return None

    def set_stop_button(self, button):
        pass

    def shutdown(self):
        raise FinSimulacion("shutdown")


class PrimeHub:
    def __init__(self, *a, **k):
        self.sim = SIM
        self.display = _Display(self.sim)
        self.light = _Light(self.sim)
        self.speaker = _Speaker()
        self.buttons = _Buttons(self.sim)
        self.imu = _IMU(self.sim)
        self.system = _System(self.sim)
        self.battery = types.SimpleNamespace(voltage=lambda: 8000,
                                             current=lambda: 100)


class ColorSensor:
    def __init__(self, port):
        self.port = port
        self.sim = SIM

    def reflection(self):
        return self.sim.leer_sensor()

    def color(self):
        return None


class DriveBase:
    def __init__(self, left, right, wheel_diameter, axle_track):
        self.sim = SIM
        self.left = left
        self.right = right
        self.wheel_diameter = wheel_diameter
        self.axle_track = axle_track

    def drive(self, speed, turn_rate=None):
        self.sim.robot.v_cmd = float(speed)
        self.sim.robot.w_cmd = float(turn_rate or 0.0)

    def stop(self):
        self.sim.robot.v_cmd = 0.0
        self.sim.robot.w_cmd = 0.0

    def brake(self):
        self.stop()

    def distance(self):
        return self.sim.robot.dist

    def angle(self):
        return self.sim.robot.angulo()

    def reset(self, distance=0, angle=0):
        pass

    def use_gyro(self, use):
        pass

    def settings(self, *a, **k):
        pass


class StopWatch:
    def __init__(self):
        self.t0 = SIM.t_ms

    def time(self):
        return SIM.t_ms - self.t0

    def reset(self):
        self.t0 = SIM.t_ms

    def pause(self):
        pass

    def resume(self):
        pass


def _wait(ms):
    SIM.avanzar(ms)
    # Boton DERECHA pulsado solo al inicio, para arrancar el programa.
    if SIM.t_ms < 150:
        SIM.botones = {Button.RIGHT}
    else:
        SIM.botones = set()


# ---------------------------------------------------------------------------
# Ejecucion
# ---------------------------------------------------------------------------
SIM = None


def instalar_stubs():
    def modulo(nombre, **attrs):
        m = types.ModuleType(nombre)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[nombre] = m
        return m

    pybricks = modulo("pybricks")
    pybricks.__path__ = []
    modulo("pybricks.hubs", PrimeHub=PrimeHub)
    modulo("pybricks.pupdevices", Motor=Motor, ColorSensor=ColorSensor)
    modulo("pybricks.parameters", Port=Port, Direction=Direction,
           Button=Button, Color=Color)
    modulo("pybricks.robotics", DriveBase=DriveBase)
    modulo("pybricks.tools", wait=_wait, StopWatch=StopWatch)


def ejecutar(ruta, escenario):
    global SIM
    SIM = Sim(escenario)
    instalar_stubs()
    with open(ruta, encoding="utf-8") as f:
        codigo = f.read()
    # El programa imprime mucho; se guarda y se descarta para no ensuciar.
    ruido = io.StringIO()
    with contextlib.redirect_stdout(ruido):
        try:
            exec(compile(codigo, ruta, "exec"), {"__name__": "__main__"})
        except FinSimulacion as e:
            SIM.motivo_fin = str(e)
        except Exception as e:
            import traceback
            traceback.print_exc()
            SIM.motivo_fin = "excepcion: %s" % e
    SIM.fin = SIM.t_ms
    if os.environ.get("SIM_TRAZA") in (SIM.esc.nombre, "1", "todos"):
        print("")
        print("TRAZA %s" % SIM.esc.nombre)
        print("%6s %2s %4s %6s %6s %6s %6s %7s %7s" % (
            "t", "st", "n", "d", "s", "v", "w", "ang", "dist"))
        for fila in SIM.traza:
            print("%6d %2s %4.0f %6.1f %6.1f %6.1f %6.1f %7.1f %7.1f" % (
                fila[0], fila[1], fila[2], fila[3], fila[4], fila[5],
                fila[6], fila[7], fila[8]))
    return SIM.resumen()


def imprimir_tabla(resultados):
    cab = ("Escenario", "v media", "RMS", "Max", "tiempo", "cruce",
           "busca", "barrido", "final")
    print("")
    print("%-13s %8s %7s %7s %7s %7s %7s %9s %6s" % cab)
    print("-" * 82)
    for r in resultados:
        print("%-13s %7.1f %7.2f %7.2f %7.1f %7.1f %7.1f %8.0f %6s" % (
            r["nombre"], r["vel_media"], r["rms"], r["max"],
            r["duracion"] / 1000.0, r["tiempos"]["cruzar"] / 1000.0,
            r["tiempos"]["buscar"] / 1000.0, r["barrido"], r["final"]))
        print("%-13s %s" % ("", r["chars"]))


def main():
    args = sys.argv[1:]
    if args:
        programas = [(os.path.basename(a), os.path.abspath(a)) for a in args]
    else:
        programas = [
            ("anterior", os.path.join(RAIZ, "sim", "_baseline_05.py")),
            ("nuevo", os.path.join(RAIZ, "05_seguidor_linea.py")),
        ]

    for nombre, ruta in programas:
        if not os.path.exists(ruta):
            print("No existe: %s" % ruta)
            continue
        print("")
        print("=" * 82)
        print("PROGRAMA: %s (%s)" % (nombre, os.path.basename(ruta)))
        print("=" * 82)
        resultados = []
        filtro = os.environ.get("SIM_ESC", "")
        lista = [e for e in escenarios()
                 if not filtro or e.nombre in filtro.split(",")]
        for esc in lista:
            print("  ejecutando %-13s ..." % esc.nombre, end="", flush=True)
            r = ejecutar(ruta, esc)
            print(" %5.2f s  v=%5.1f  RMS=%5.2f" % (
                r["duracion"] / 1000.0, r["vel_media"], r["rms"]))
            resultados.append(r)
        imprimir_tabla(resultados)


if __name__ == "__main__":
    main()
