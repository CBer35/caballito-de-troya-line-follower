# Seguidor de Líneas con 2 Sensores Separados — LEGO SPIKE Prime + Pybricks

Carpeta independiente con el código y las pruebas para el robot **“El Caballito de Troya”**.

En esta versión los dos sensores van **separados** y la línea pasa **entre ellos**. Cuando el robot está centrado, los dos sensores ven **blanco**. Si el robot se desvía, uno de los dos sensores ve **negro**.

---

## 1. Qué hay en esta carpeta

| Archivo | Para qué sirve |
| :--- | :--- |
| `01_test_sensores.py` | Muestra los valores crudos de los dos sensores, el mínimo/máximo y el contraste. Sirve para comprobar que ven bien el negro y el blanco. |
| `02_calibracion.py` | Calibración guiada en 3 pasos para sensores separados. Guarda los valores en la memoria del hub. |
| `03_test_motores_y_giro.py` | Prueba cada motor, avanza en recta, gira 90° y mide con el giroscopio cuánto gira realmente. |
| `04_prueba_control.py` | Prueba 4 perfiles de velocidad/KP/KD y muestra estadísticas de error, zigzag y tiempo buscando la línea. |
| `05_seguidor_linea.py` | Programa final, con la estrategia de “todo blanco” y búsqueda girando en el sitio. |

Cada archivo es independiente: puedes ejecutarlo desde **VS Code** con `Ctrl+Shift+B` o pegarlo en **Pybricks Code**.

---

## 2. Conexiones

| Componente | Puerto | Configuración |
| :--- | :--- | :--- |
| Motor izquierdo | **F** | `Direction.COUNTERCLOCKWISE` |
| Motor derecho | **B** | `Direction.CLOCKWISE` |
| Sensor de color izquierdo | **A** | Va a la izquierda de la línea |
| Sensor de color derecho | **E** | Va a la derecha de la línea |

```python
robot = DriveBase(
    motor_left,
    motor_right,
    wheel_diameter=56,   # rueda de 56 mm
    axle_track=200       # distancia entre puntos de apoyo; ajústala si tu robot es distinto
)
```

> Si tu robot tiene otra distancia entre ruedas, mídela y cambia `axle_track`. No es crítico para seguir la línea, pero sí para que `robot.turn(90)` y las pruebas de giro sean exactas.

---

## 3. La geometría y el problema de “todo blanco”

Con los sensores separados y la línea entre ellos:

| Estado | Sensores | Interpretación |
| :--- | :--- | :--- |
| Centrado | Los dos ven **blanco** | La línea pasa entre los dos |
| Desviado a la izquierda | El **derecho** ve negro | Hay que girar a la derecha |
| Desviado a la derecha | El **izquierdo** ve negro | Hay que girar a la izquierda |
| Cruce / línea ancha | Los dos ven **negro** | Seguir recto para cruzar |

El problema es que **“los dos en blanco”** puede significar dos cosas:

1. El robot está centrado y la línea pasa entre los sensores.
2. El robot se salió de la línea y está perdido.

Con solo dos sensores **no se puede distinguir de inmediato**. La estrategia del código es:

1. Si al menos un sensor ve negro, se corrige con control PD normal.
2. Si los dos ven blanco, el robot avanza recto **a velocidad reducida** solo durante `WHITE_GRACE_MS` (1500 ms por defecto), porque probablemente está centrado. Además conserva un poco el último giro para no perder las curvas.
3. Si sigue todo blanco, **deja de avanzar** y gira en el sitio barriendo a izquierda y derecha para volver a encontrar la línea.
4. Si sigue todo blanco más de `LOST_TIMEOUT_MS` (3 s en total, contando la gracia), se detiene y muestra `E`.

Así el robot no se escapa avanzando a ciegas cuando pierde la línea. El precio es que, en una recta muy larga y perfectamente centrada, puede hacer una pausa y buscar; si eso pasa, sube `WHITE_GRACE_MS`.

> **Limitación real:** con dos sensores separados, la ambigüedad “centrado vs perdido” no se puede eliminar por completo. Si necesitas certeza absoluta, hay que añadir un tercer sensor, usar una línea más ancha para que los dos sensores vean negro, o usar una cámara.

### La alternativa que elimina la ambigüedad

Si puedes **acercar los sensores** hasta que, con el robot centrado, cada uno vea el **borde** de la línea (una lectura intermedia, por ejemplo 40–60, en vez de blanco puro), entonces:

- Centrado → los dos leen un valor intermedio (gris).
- Desviado a la izquierda → el derecho ve más negro y el izquierdo más blanco.
- **Todo blanco → con seguridad se salió de la línea** (ya no hay línea bajo ningún sensor).
- Todo negro → línea ancha o cruce.

Esa geometría es la clásica de los seguidores de dos sensores y da una señal continua, más suave y fácil de ajustar. En ese caso se puede usar la regla estricta “todo blanco = detenerse y buscar”, sin ventana de gracia. Si tu robot permite mover los sensores, es la opción más robusta. El código de esta carpeta está pensado para la geometría “centrado = blanco”; si acercas los sensores, avísame y lo adapto a la geometría de borde.

---

## 4. Antes de empezar

1. El hub debe tener **Pybricks** instalado (no el firmware de la app SPIKE).
2. Carga el hub al 100 % o con buena batería.
3. Los sensores deben quedar a **5–8 mm** del piso, sin rozar.
4. Usa una línea **negra mate**. El brillo o una sombra fuerte cambian las lecturas.
5. Acerca los sensores todo lo que puedas a la línea, pero deja que pase entre ellos. Cuanto más separados estén, más tarde corrige el robot y más zigzag puede hacer.

---

## 5. Procedimiento recomendado

### Paso 1 — `01_test_sensores.py`

Pasa el robot despacio para que cada sensor vea la línea negra y el piso blanco.

En la consola verás algo parecido a:

```text
L(A)= 11 [ 10.. 12] | R(E)= 10 [  9.. 11]
L(A)= 93 [ 10.. 93] | R(E)= 88 [  9.. 88]
```

Interpretación:

| Lectura | Significado |
| :--- | :--- |
| **5–15** | Negro (línea) |
| **85–100** | Blanco (piso) |
| **Contraste > 50** | Excelente |
| **Contraste 20–50** | Aceptable |
| **Contraste < 20** | Problema: sensor muy alto, línea brillante o luz inestable |

La luz del hub indica:

- **Verde:** al menos un sensor ve negro (línea detectada).
- **Rojo:** los dos ven blanco (centrado o perdido).
- **Amarillo:** borde/gris.

Botones:

- **IZQUIERDA:** reinicia los mínimos/máximos.
- **DERECHA:** termina y muestra el resumen.

---

### Paso 2 — `02_calibracion.py`

La calibración para sensores separados se hace en **3 pasos**:

1. **Sensor izquierdo (A) sobre la línea negra** y **sensor derecho (E) sobre el piso blanco**. Pulsa DERECHA.
2. **Sensor derecho (E) sobre la línea negra** y **sensor izquierdo (A) sobre el piso blanco**. Pulsa DERECHA.
3. **Robot centrado**, con la línea entre los dos sensores y **los dos sobre el piso blanco**. Pulsa DERECHA.

Así se obtiene el negro de cada sensor por separado y el blanco de cada uno por separado, sin necesidad de que la línea sea ancha.

En consola verás:

```text
=== VALORES PARA 04 Y 05 ===
BLACK_L = 10.8
WHITE_L = 97.4
BLACK_R = 10.2
WHITE_R = 90.0
UMBRAL_L = 54.1
UMBRAL_R = 50.1
```

La calibración se guarda en la memoria del hub. `04` y `05` la leen automáticamente.

> **Importante:** si después de calibrar ejecutas `05` y ves que usa los valores por defecto, detén el programa, apaga el hub normalmente y vuelve a encenderlo. La memoria del hub se confirma al apagarlo de forma normal. También puedes copiar los valores a mano en `05_seguidor_linea.py`.

Si el programa muestra `E` y un pitido grave, el contraste es demasiado bajo. Revisa la altura de los sensores y la superficie.

---

### Paso 3 — `03_test_motores_y_giro.py`

Este programa comprueba:

1. **Motores por separado:** levanta el robot y pulsa DERECHA. La rueda izquierda debe girar hacia adelante; luego la derecha.
2. **Recta:** pon el robot en el piso y avanza 300 mm. El giroscopio mide cuánto se desvió.
3. **Giros y fuerza:** gira 90° a la derecha, 90° a la izquierda y mide cuánto gira de verdad para comandos de `60, 120, 180 y 240 °/s`.

Ejemplo:

```text
Comando (deg/s) | En sitio (deg) | Avanzando (deg)
      60        |       58       |       61
     120        |      119       |      117
     180        |      176       |      181
     240        |      238       |      235
```

Qué hacer:

- Si una rueda gira al revés, cambia su `Direction` en `03` y en `05`.
- Si en recta se desvía más de 8°, revisa la tracción.
- Si el giro medido es mucho menor que el comando, sube `KP` o `TURN_MAX`.
- Si el signo es contrario, revisa las direcciones de los motores.

---

### Paso 4 — `04_prueba_control.py`

Este programa prueba 4 perfiles:

| Perfil | Velocidad | KP | KD | Cuándo usarlo |
| :--- | :--- | :--- | :--- | :--- |
| 1 SUAVE | 120 mm/s | 1.0 | 0.00 | Primeras pruebas, curvas cerradas |
| 2 MEDIO | 160 mm/s | 2.0 | 0.60 | Uso general |
| 3 FUERTE | 200 mm/s | 3.0 | 1.20 | Robot estable y línea amplia |
| 4 MUY FUERTE | 240 mm/s | 4.0 | 1.80 | Solo si los anteriores quedan lentos |

Cómo usarlo:

1. Coloca el robot centrado sobre la línea.
2. Con **IZQUIERDA** cambia de perfil.
3. Con **DERECHA** inicia la prueba (12 segundos).
4. Durante la prueba, **IZQUIERDA** detiene.
5. Al final verás algo como:

```text
=== RESULTADO FUERTE ===
Muestras con linea visible: 620
Error medio: 8.4
Error maximo: 62.0
Cambios de direccion (zigzag): 14
Giro maximo: 310 deg/s
Tiempo buscando: 0.0 s
Perfil: v=200 KP=3.00 KD=1.20
```

Interpretación:

- **Error medio bajo** y **pocos cambios de dirección** = sigue bien y sin zigzag.
- **Muchos cambios de dirección** = KP demasiado alto o KD demasiado bajo.
- **Error máximo alto y se sale en curvas** = KP bajo, velocidad alta o sensores muy separados.
- **Tiempo buscando > 0** = se quedó sin ver negro y tuvo que buscar. Si pasa en rectas, sube `WHITE_GRACE_MS`; si pasa en curvas, sube `KP` o baja la velocidad.
- **Se pierde la línea** = empieza con SUAVE y sube poco a poco.

Cuando encuentres el mejor perfil, copia sus valores en `05_seguidor_linea.py`:

```python
BASE_SPEED = 200
KP = 3.0
KD = 1.20
```

---

### Paso 5 — `05_seguidor_linea.py`

Es el programa final.

Botones:

| Botón | Acción |
| :--- | :--- |
| **DERECHA** | Iniciar el seguimiento |
| **IZQUIERDA** | Detener el robot |
| **CENTRAL** | Detener el programa (comportamiento normal de Pybricks) |

Comportamiento:

- Si un sensor ve negro, corrige hacia el lado de la línea.
- Si los dos ven negro, sigue recto (cruce o línea ancha).
- Si los dos ven blanco, avanza recto a velocidad reducida durante `WHITE_GRACE_MS`.
- Si sigue todo blanco, se detiene y gira en el sitio para buscar.
- Si sigue todo blanco más de `LOST_TIMEOUT_MS`, se detiene y muestra `E`.

Pantalla del hub:

| Símbolo | Significado |
| :--- | :--- |
| `R` | Listo, esperando DERECHA |
| `^` | Centrado, cruzando o corrigiendo poco |
| `>` | Corrigiendo a la derecha |
| `<` | Corrigiendo a la izquierda |
| `!` | Buscando la línea (girando en el sitio) |
| `S` | Detenido por el usuario |
| `E` | Línea perdida |

---

## 6. Cómo funciona el control

La reflectancia se normaliza para que:

- **0** = negro
- **100** = blanco

```python
nL = (raw_L - BLACK_L) * 100 / (WHITE_L - BLACK_L)
nR = (raw_R - BLACK_R) * 100 / (WHITE_R - BLACK_R)
error = nL - nR
```

Con la línea entre los sensores:

- Centrado: los dos ven blanco, `error ≈ 0`.
- Se va a la izquierda: el derecho ve negro, `nR` baja, `error > 0`.
- En Pybricks, un `turn_rate` positivo gira a la **derecha**. Por eso `turn = KP * error` corrige correctamente.
- Se va a la derecha: el izquierdo ve negro, `error < 0`, gira a la izquierda.

El término derivativo amortigua el zigzag (se filtra para que no reaccione a un salto brusco):

```python
deriv = error - error_anterior
deriv_f = 0.6 * deriv_f + 0.4 * deriv
turn = KP * error + KD * deriv_f
```

La velocidad baja cuando el giro es grande:

```python
velocidad = BASE_SPEED - abs(turn) * SPEED_REDUCTION
```

Durante la ventana de “todo blanco” se conserva un porcentaje del último giro:

```python
turn = last_turn * TURN_MEMORY
```

Eso ayuda a no perder las curvas cuando la línea queda justo entre los sensores.

---

## 7. Ajuste fino

| Síntoma | Qué cambiar |
| :--- | :--- |
| Zigzaguea mucho | Baja `KP`, sube un poco `KD` o baja `BASE_SPEED`. |
| No corrige a tiempo y se sale | Acerca los sensores, baja `BASE_SPEED` o sube `KP`. |
| Se queda buscando en rectas largas | Sube `WHITE_GRACE_MS` (por ejemplo a 2000–3000 ms). |
| Avanza demasiado cuando se pierde | Baja `WHITE_GRACE_MS` (por ejemplo a 400–700 ms) o baja `WHITE_SPEED_FACTOR`. |
| No encuentra la línea al buscar | Sube `LOST_TIMEOUT_MS` o revisa que los sensores estén a 5–8 mm. |
| Corrige al lado contrario | Cambia los puertos A/E o niega `KP`. |
| Avanza al revés | Invierte `Direction` de los dos motores. |
| En una curva cerrada se sale | Baja `BASE_SPEED`, sube `KP`, acerca los sensores. |

> **Regla práctica:** primero se ajusta `KP` con el robot lento. Cuando ya siga sin salirse, se sube la velocidad y se ajusta `KD` para quitar el zigzag.

---

## 8. Problemas comunes

| Problema | Causa probable | Solución |
| :--- | :--- | :--- |
| `ImportError` o `ModuleNotFoundError` | El hub no tiene Pybricks | Instala el firmware de Pybricks. |
| Lecturas siempre 0 | Sensor desconectado o puerto equivocado | Revisa cable y puerto A/E. |
| Lecturas siempre 100 | Sensor muy lejos del piso o línea blanca | Acércalo a 5–8 mm y usa negro mate. |
| Los dos sensores nunca ven negro | La línea es más angosta que la separación y el robot no se desvía lo suficiente | Acerca los sensores o haz que el robot se desvíe más para probar. |
| El robot gira al lado contrario | Sensores invertidos o `KP` con signo contrario | Cambia A/E o usa `KP = -KP`. |
| La calibración no se carga | El hub no se apagó normalmente después de calibrar | Apaga y enciende el hub, o copia los valores a mano. |
| Se detiene y busca en rectas largas | `WHITE_GRACE_MS` demasiado bajo | Súbelo a 2000–3000 ms. |
| Se escapa al perder la línea | `WHITE_GRACE_MS` demasiado alto | Bájalo a 400–700 ms. |
| Zigzag constante | `KP` alto, `KD` bajo o sensores muy separados | Baja `KP`, sube `KD`, acerca los sensores. |

---

## 9. Cómo ejecutar

### Opción A — Visual Studio Code (recomendado)

El repositorio ya trae tareas listas en `.vscode/`:

1. Abre VS Code en la carpeta del proyecto.
2. Abre el script que quieras ejecutar.
3. Pulsa **Ctrl + Shift + B** para subir el archivo abierto al hub.

También puedes usar **Ctrl + Shift + P → `Tasks: Run Task`** y elegir, por
ejemplo, `2 sensores · 01 Test de sensores`. Sigue el orden `01 → 02 → 03 → 04 → 05`.

Los tests muestran sus mensajes en la terminal de VS Code. El `05` se suelta
para que el robot arranque; se detiene con el **botón central** del hub.
Ver el [README principal](../README.md#-cómo-ejecutar-el-programa) para el
detalle de cada tarea y la solución de problemas de conexión.

### Opción B — Pybricks Code

1. Abre [code.pybricks.com](https://code.pybricks.com/) en Chrome, Edge o Brave.
2. Conecta el hub por USB o Bluetooth.
3. Crea un archivo nuevo, pega el contenido de uno de los programas y pulsa ▶️.
4. Empieza por `01_test_sensores.py` y sigue el orden.

### Opción C — `pybricksdev` desde la terminal

```powershell
# desde la carpeta raíz del repositorio
pybricksdev run usb seguidor_linea_pybricks\01_test_sensores.py
pybricksdev run usb seguidor_linea_pybricks\02_calibracion.py
pybricksdev run usb seguidor_linea_pybricks\03_test_motores_y_giro.py
pybricksdev run usb seguidor_linea_pybricks\04_prueba_control.py
pybricksdev run usb seguidor_linea_pybricks\05_seguidor_linea.py
```

Sin `-n`, busca el primer hub con Pybricks. También sirve `run ble`. Añade
`--no-wait` para soltar el robot y que el comando termine enseguida.

---

## 10. Referencias usadas

- **Pybricks — Color Sensor:** `reflection()` devuelve 0–100 %, `color()` y `hsv()` para diagnóstico.  
  <https://docs.pybricks.com/en/stable/pupdevices/colorsensor.html>
- **Pybricks — DriveBase:** los valores positivos de `turn_rate` giran a la **derecha**; `drive(speed, turn_rate)` usa mm/s y °/s.  
  <https://docs.pybricks.com/en/stable/robotics.html>
- **Pybricks — Prime Hub:** botones, pantalla, luces, IMU (`hub.imu.heading()`) y almacenamiento persistente (`hub.system.storage`).  
  <https://docs.pybricks.com/en/stable/hubs/primehub.html>
- **FLL Knowledge Base — Line Following:** explica el seguidor de dos sensores usando la diferencia de reflectancia como error.  
  <https://lego.xclean.dev/advanced/line-following>
- **Pybricks Discussion #1285 — How to use Line Following:** ejemplo básico de seguimiento con sensor de color en SPIKE Prime.  
  <https://github.com/orgs/pybricks/discussions/1285>
- **The Team Fusion — FLL Line Squaring:** referencia de alineación con dos sensores de color en SPIKE Prime.  
  <https://theteamfusion.com/post/fll-line-squaring-align-your-robot-on-a-black-line-spike-prime-python>

---

## 11. Resumen rápido

1. `01` → comprobar que negro ≈ 10 y blanco ≈ 90.
2. `02` → calibrar en 3 pasos y guardar.
3. `03` → comprobar motores y fuerza de giro.
4. `04` → probar perfiles y elegir KP/KD/velocidad.
5. `05` → ejecutar el seguidor final.

Si tienes prisa: ejecuta `02`, luego `05` con los valores por defecto. Si zigzaguea, baja `KP`; si se sale en curvas, súbelo poco a poco. Si se queda buscando en rectas, sube `WHITE_GRACE_MS`.
