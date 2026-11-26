# Seguidor de Líneas con 1 Sensor — LEGO SPIKE Prime + Pybricks

Carpeta alternativa al seguidor de dos sensores. Aquí se usa **un solo sensor de color, el A**, montado **centrado en el robot**, mirando la línea.

---

## 1. Qué hay en esta carpeta

| Archivo | Para qué sirve |
| :--- | :--- |
| `01_test_sensor.py` | Muestra la reflectancia del sensor A, el mínimo/máximo y el contraste. |
| `02_calibracion.py` | Calibración en 2 pasos (negro y blanco) y guardado en el hub. |
| `03_test_motores_y_giro.py` | Prueba motores, recta, giros de 90° y fuerza de giro real con el IMU. |
| `04_prueba_control.py` | Prueba 4 perfiles de velocidad/KP/KD con estadísticas. |
| `05_seguidor_linea.py` | Programa final. |

Cada archivo es independiente: puedes ejecutarlo desde **VS Code** con `Ctrl+Shift+B` o pegarlo en **Pybricks Code**.

---

## 2. Conexiones

| Componente | Puerto | Configuración |
| :--- | :--- | :--- |
| Motor izquierdo | **F** | `Direction.COUNTERCLOCKWISE` |
| Motor derecho | **B** | `Direction.CLOCKWISE` |
| Sensor de color | **A** | Centrado en el robot, mirando la línea |

```python
robot = DriveBase(
    motor_left,
    motor_right,
    wheel_diameter=56,   # rueda de 56 mm
    axle_track=200       # ajústalo si tu robot es distinto
)
```

---

## 3. La idea clave: con un sensor se sigue un borde, no el centro

La reflectancia es **baja (negro)** en el centro de la línea y **alta (blanco)** fuera de ella. Si el sensor va por el **centro** de la línea:

- Si el robot se desvía un poco a la izquierda, la lectura sube.
- Si se desvía un poco a la derecha, la lectura **también** sube.

Con un solo sensor no hay forma de distinguir esos dos casos: el centro es una **zona ciega**. Por eso un control proporcional que intente quedarse en el centro es inestable.

En cambio, en el **borde** de la línea la lectura es monótona:

| Posición del sensor | Lectura | Corrección |
| :--- | :--- | :--- |
| Sobre el negro (centro) | baja (~10) | girar hacia el borde |
| En el borde | media (~50) | recto |
| Fuera, sobre blanco | alta (~100) | girar hacia la línea |

Por eso el robot se calibra para seguir la **transición** (TARGET ≈ 50). El cuerpo del robot queda desviado respecto al centro de la línea aproximadamente **medio ancho de línea** (unos 10 mm con una línea de 19 mm). Es normal y no afecta al seguimiento.

Con `LADO = 1` sigue el borde **izquierdo**; con `LADO = -1`, el **derecho**. El robot elige un borde y se mantiene en él.

> **Ventaja:** ahora “todo blanco” sí significa claramente **perdido**, porque el estado normal es el borde (gris), no el blanco. Eso encaja con la lógica que querías.

---

## 4. Estrategia del programa final

El control tiene **tres estados** y varias protecciones para que no se ponga a dar vueltas:

1. **NORMAL** — sigue el borde con un PD suave:
   - filtra la lectura (`FILTRO`) para quitar ruido;
   - normaliza: **0 = negro**, **100 = blanco**;
   - `error = n - TARGET_N`;
   - **banda muerta** amplia (`DEADBAND`): si está cerca del borde, no corrige;
   - **límite de cambio de giro** (`TURN_SLEW`): el giro no cambia de golpe;
   - **freno sobre blanco** (`FRENO_GRIS`, `FRENO_BLANCO`): al ver blanco baja la velocidad para no escaparse mientras corrige;
   - `turn = LADO * (KP * error + KD * derivada_filtrada)`.
2. **BUSCAR** — si la lectura se queda casi blanca (`n > WHITE_LOST`) durante `LOST_GRACE_MS`, deja de avanzar y **gira en el sitio** en el sentido de la última corrección (`SEARCH_TURN`) hasta reencontrar la línea. Si da una vuelta completa (`SEARCH_TIMEOUT_MS`) sin verla, se detiene.
3. **RECUPERAR** — cuando vuelve a ver negro, avanza despacio y gira hacia el borde elegido (`-LADO * RECOVER_TURN`) hasta llegar a la transición. Así no se queda del lado equivocado.
4. **Seguridad** — si se pierde más de `MAX_PERDIDAS` veces seguidas, se detiene y muestra `E` en vez de girar indefinidamente.

**Por qué antes daba vueltas:** con el sensor sobre el negro (centro de la línea), el error se saturaba en −50 y el control antiguo (`KP=2.5`, sin banda muerta ni filtro) ordenaba un giro fuerte constante. El robot se ponía a **orbitar sobre la propia línea** sin llegar nunca al borde: eso eran las “vueltas sin sentido”. Además, la transición negro/blanco es muy brusca (pasa de ~50 a ~80 en pocos milímetros), así que cualquier ganancia alta hacía que se pasara al otro lado. El filtro, la banda muerta, el límite de giro, el freno sobre blanco y la recuperación rompen ese ciclo.

La derivada se filtra para que un salto brusco de lectura no produzca un giro violento:

```python
deriv = error - error_anterior
deriv_f = 0.6 * deriv_f + 0.4 * deriv
turn = LADO * (KP * error + KD * deriv_f)
```

---

## 5. Antes de empezar

1. El hub debe tener **Pybricks** instalado.
2. Batería con buena carga.
3. Sensor a **5–8 mm** del piso, sin rozar.
4. Línea **negra mate**; evita brillos y sombras fuertes.
5. El sensor debe quedar **centrado lateralmente** en el robot. Si está muy adelantado, la búsqueda girando en el sitio funciona mejor (barre un arco más amplio).

---

## 6. Procedimiento recomendado

### Paso 1 — `01_test_sensor.py`

Pasa el sensor despacio sobre la línea y sobre el piso blanco. En consola verás algo como:

```text
A= 11 [ 10.. 12] contraste=  2
A= 93 [ 10.. 93] contraste= 83
```

| Lectura | Significado |
| :--- | :--- |
| **5–15** | Negro (línea) |
| **85–100** | Blanco (piso) |
| **Contraste > 50** | Excelente |
| **Contraste 20–50** | Aceptable |
| **Contraste < 20** | Problema: sensor alto, línea brillante o luz inestable |

Luz del hub: **verde** = negro, **rojo** = blanco, **amarillo** = borde/gris.

---

### Paso 2 — `02_calibracion.py`

1. Sensor A sobre la **línea negra** → DERECHA.
2. Sensor A sobre el **piso blanco** → DERECHA.

En consola:

```text
=== VALORES PARA 04 Y 05 ===
BLACK = 17.3
WHITE = 98.4
TARGET = 57.8
```

Se guarda en la memoria del hub. `04` y `05` la leen automáticamente.

> Si después de calibrar `05` usa los valores por defecto, detén el programa, apaga el hub normalmente y vuelve a encenderlo. La memoria se confirma al apagar de forma normal. También puedes copiar los valores a mano en `05_seguidor_linea.py`.

---

### Paso 3 — `03_test_motores_y_giro.py`

Comprueba:

1. **Motores por separado** (levanta el robot).
2. **Recta de 300 mm** y desvío medido con el giroscopio.
3. **Giros de 90°** y fuerza de giro real para `60, 120, 180 y 240 °/s`.

- Si una rueda gira al revés, cambia su `Direction` en `03` y en `05`.
- Si en recta se desvía más de 8°, revisa la tracción.
- Si el giro medido es muy distinto del comando, ajusta `axle_track`.

---

### Paso 4 — `04_prueba_control.py`

Perfiles:

| Perfil | Velocidad | KP | KD | Cuándo usarlo |
| :--- | :--- | :--- | :--- | :--- |
| 1 SUAVE | 80 mm/s | 1.0 | 0.00 | Primeras pruebas, curvas cerradas |
| 2 MEDIO | 100 mm/s | 1.5 | 0.15 | Uso general (recomendado) |
| 3 FUERTE | 130 mm/s | 2.0 | 0.30 | Robot estable |
| 4 MUY FUERTE | 160 mm/s | 2.5 | 0.45 | Solo si los anteriores van sobrados |

Cómo usarlo:

1. Coloca el sensor sobre la línea.
2. **IZQUIERDA** cambia de perfil.
3. **DERECHA** inicia la prueba (15 s).
4. **IZQUIERDA** durante la prueba detiene.
5. Al final verás algo como:

```text
=== RESULTADO MEDIO ===
Muestras con linea visible: 610
Error medio: 6.2
Error maximo: 48.0
Cambios de direccion (zigzag): 18
Giro maximo: 120 deg/s
Perdidas: 0
Tiempo buscando: 0.0 s
Perfil: v=100 KP=1.50 KD=0.15
```

Interpretación:

- **Error medio bajo** y **pocos cambios de dirección** = sigue bien.
- **Muchos cambios de dirección** = KP alto o KD bajo.
- **Error máximo alto y se sale en curvas** = KP bajo, velocidad alta o sensor mal ubicado.
- **Tiempo buscando > 0** = se quedó sin ver el borde. Si pasa en curvas, sube `KP` o baja la velocidad; si pasa en rectas, revisa la calibración.
- **Se pierde la línea** = empieza con SUAVE y sube poco a poco.

Cuando encuentres el mejor perfil, copia sus valores en `05_seguidor_linea.py`:

```python
BASE_SPEED = 130
KP = 2.0
KD = 0.30
```

---

### Paso 5 — `05_seguidor_linea.py`

| Botón | Acción |
| :--- | :--- |
| **DERECHA** | Iniciar |
| **IZQUIERDA** | Detener |
| **CENTRAL** | Detener el programa |

Pantalla del hub:

| Símbolo | Significado |
| :--- | :--- |
| `R` | Listo, esperando DERECHA |
| `\|` | En el borde (correcto) |
| `N` | Sobre negro (centro de la línea) |
| `B` | Sobre blanco (posible pérdida) |
| `!` | Buscando la línea girando en el sitio |
| `+` | Recuperando: encontró la línea y vuelve al borde |
| `S` | Detenido por el usuario |
| `E` | Línea perdida o control inestable |

---

## 7. Ajuste fino

| Síntoma | Qué cambiar |
| :--- | :--- |
| **Da vueltas en círculos / encuentra y pierde** | Baja `KP` (1.0–1.5), baja `BASE_SPEED` (70–90), sube `DEADBAND` (12–15) o baja `TURN_SLEW` (10–15). |
| Zigzaguea mucho | Baja `KP`, sube un poco `KD` o baja `BASE_SPEED`. |
| No corrige a tiempo y se sale | Sube `KP` o baja `BASE_SPEED`. |
| Se va hacia el lado contrario | Cambia `LADO` de `1` a `-1` (o al revés). |
| Queda desviado y no encuentra el borde | Ajusta `TARGET_N` (prueba 40–60). |
| Se detiene y busca en curvas | Sube `KP`, baja la velocidad o sube `LOST_GRACE_MS`. |
| Se escapa al perder la línea | Baja `LOST_GRACE_MS` (400–600 ms) o baja `FRENO_BLANCO` (0.25) para frenar más sobre blanco. |
| No encuentra la línea al buscar | Sube `SEARCH_TIMEOUT_MS` o monta el sensor un poco más adelante. |
| Avanza al revés | Invierte `Direction` de los dos motores. |
| Corrige al revés | Cambia `LADO` o niega `KP`. |

> **Si sigue dando vueltas:** ejecuta `03_test_motores_y_giro.py` y comprueba que `axle_track=200` sea parecido al real. Un `axle_track` mal puesto hace que los giros comandados no coincidan con los reales y el control se vuelve impredecible.

> **Regla práctica:** primero ajusta `KP` con el robot lento. Cuando ya siga sin salirse, sube la velocidad y ajusta `KD` para quitar el zigzag.

### Diagnóstico rápido en consola

Mientras sigue la línea verás algo como:

```text
A= 62 n= 55 | err=   5 turn=   6 | NORMAL
A= 90 n= 89 | err=  39 turn=  47 | NORMAL
```

- Si `n` sube hacia 90–100 y `turn` es **positivo**, el robot gira a la derecha: correcto si sigue el borde izquierdo (`LADO = 1`).
- Si ves que `turn` empuja **alejándose** de la línea, cambia `LADO` a `-1`.
- Si aparece muchas veces `BUSCAR`, baja `KP` y `BASE_SPEED`, o sube `DEADBAND`.

---

## 8. Problemas comunes

| Problema | Causa probable | Solución |
| :--- | :--- | :--- |
| `ImportError` | El hub no tiene Pybricks | Instala el firmware de Pybricks. |
| Lecturas siempre 0 | Sensor desconectado o puerto equivocado | Revisa cable y puerto A. |
| Lecturas siempre 100 | Sensor muy lejos del piso | Acércalo a 5–8 mm. |
| El robot se va de lado | `LADO` o signo de `KP` equivocado | Cambia `LADO`. |
| Da vueltas en círculos | `KP`/velocidad altos o `LADO` equivocado | Baja `KP` y `BASE_SPEED`; si sigue, cambia `LADO`. |
| Zigzag constante | `KP` alto o `KD` bajo | Baja `KP`, sube `KD`. |
| La calibración no se carga | El hub no se apagó normalmente | Apaga/enciende el hub o copia los valores a mano. |

---

## 9. Diferencias con la versión de 2 sensores

| | 2 sensores | 1 sensor |
| :--- | :--- | :--- |
| Estado centrado | los dos ven blanco | el sensor ve el borde (~50) |
| “Todo blanco” | ambiguo: centrado o perdido | claramente perdido |
| Señal de error | `nL - nR` (continua) | `n - TARGET` (continua en el borde) |
| Posición del robot | centrado sobre la línea | desviado ~medio ancho de línea |
| Robustez ante curvas | mejor | aceptable, requiere ajuste |
| Complejidad | media | baja |

---

## 10. Cómo ejecutar

### Opción A — Visual Studio Code (recomendado)

El repositorio ya trae tareas listas en `.vscode/`:

1. Abre VS Code en la carpeta del proyecto.
2. Abre el script que quieras ejecutar.
3. Pulsa **Ctrl + Shift + B** para subir el archivo abierto al hub.

También puedes usar **Ctrl + Shift + P → `Tasks: Run Task`** y elegir, por
ejemplo, `1 sensor · 02 Calibración`. Sigue el orden `01 → 02 → 03 → 04 → 05`.

Los tests muestran sus mensajes en la terminal de VS Code. El `05` se suelta
para que el robot arranque; se detiene con el **botón central** del hub.
Ver el [README principal](../README.md#-cómo-ejecutar-el-programa) para el
detalle de cada tarea y la solución de problemas de conexión.

### Opción B — Pybricks Code

1. Abre [code.pybricks.com](https://code.pybricks.com/).
2. Conecta el hub por USB o Bluetooth.
3. Pega el contenido de un programa y pulsa ▶️.
4. Sigue el orden `01 → 02 → 03 → 04 → 05`.

### Opción C — `pybricksdev` desde la terminal

```powershell
# desde la carpeta raíz del repositorio
pybricksdev run usb seguidor_linea_1_sensor\01_test_sensor.py
pybricksdev run usb seguidor_linea_1_sensor\02_calibracion.py
pybricksdev run usb seguidor_linea_1_sensor\03_test_motores_y_giro.py
pybricksdev run usb seguidor_linea_1_sensor\04_prueba_control.py
pybricksdev run usb seguidor_linea_1_sensor\05_seguidor_linea.py
```

Sin `-n`, busca el primer hub con Pybricks. También sirve `run ble`. Añade
`--no-wait` para soltar el robot y que el comando termine enseguida.

---

## 11. Referencias

- **Pybricks — Color Sensor:** `reflection()` devuelve 0–100 %.  
  <https://docs.pybricks.com/en/stable/pupdevices/colorsensor.html>
- **Pybricks — DriveBase:** `turn_rate` positivo gira a la derecha; `drive(speed, turn_rate)` usa mm/s y °/s.  
  <https://docs.pybricks.com/en/stable/robotics.html>
- **Pybricks — Prime Hub:** botones, pantalla, luces, IMU y almacenamiento persistente.  
  <https://docs.pybricks.com/en/stable/hubs/primehub.html>
- **FLL Knowledge Base — Line Following:** diferencia de reflectancia y control de línea.  
  <https://lego.xclean.dev/advanced/line-following>
- **Pybricks Discussion #1285 — Line Following:** ejemplo básico con sensor de color en SPIKE Prime.  
  <https://github.com/orgs/pybricks/discussions/1285>

---

## 12. Resumen rápido

1. `01` → comprobar que el negro es bajo y el blanco alto (contraste > 50).
2. `02` → calibrar negro/blanco y guardar.
3. `03` → comprobar motores y fuerza de giro.
4. `04` → probar perfiles y elegir KP/KD/velocidad.
5. `05` → ejecutar el seguidor final.

Si tienes prisa: ejecuta `02` y luego `05`. El `05` viene con valores **conservadores** (90 mm/s, KP 1.2, banda 12) para que no se descontrole.

- Si **da vueltas en círculos**: baja `KP` y `BASE_SPEED`; si sigue, cambia `LADO` de `1` a `-1`.
- Si **zigzaguea**: baja `KP` o sube `DEADBAND`.
- Si **se sale en curvas**: sube `KP` poco a poco o baja `BASE_SPEED`.
- Si **se va hacia el lado contrario**: cambia `LADO`.
