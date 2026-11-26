# Seguidor de Líneas - "El Caballito de Troya"
## LEGO SPIKE Prime con Pybricks

### 📂 Versiones del seguidor

| Carpeta | Sensores | Descripción |
| :--- | :--- | :--- |
| [`seguidor_linea_pybricks/`](./seguidor_linea_pybricks/) | 2 (A y E) | La línea pasa entre los dos sensores. Incluye test de sensores, calibración, test de motores y seguidor final. |
| [`seguidor_linea_1_sensor/`](./seguidor_linea_1_sensor/) | 1 (A) | Un solo sensor centrado; sigue un borde de la línea. Incluye la corrección de control estable. |

Cada carpeta tiene su propio `README.md` con el orden de ejecución, la calibración y el ajuste fino.

> **Historial:** este repositorio muestra la evolución del seguidor de 1 sensor. Primero se subió la versión inicial y después la **corrección** que evita que el robot "dé vueltas": control más suave, banda muerta, filtro, freno sobre blanco y búsqueda continua.

---

### 📋 Asignación de Puertos
| Componente | Puerto | Sentido / Rol |
| :--- | :--- | :--- |
| **Motor Izquierdo** | **Puerto F** | Tracción izquierda (`Direction.COUNTERCLOCKWISE`) |
| **Motor Derecho** | **Puerto B** | Tracción derecha (`Direction.CLOCKWISE`) |
| **Sensor de Color Izquierdo** | **Puerto A** | Detección de línea / superficie izquierda |
| **Sensor de Color Derecho** | **Puerto E** | Detección de línea / superficie derecha |

---

### 🚀 Cómo Ejecutar el Programa

#### Opción 1 (recomendada): desde Visual Studio Code

El proyecto ya trae todo configurado en `.vscode/` para compilar y subir el
código al hub **sin abrir el navegador**:

1. Abre VS Code en esta carpeta: **Archivo → Abrir carpeta…**.
2. Abre el archivo que quieras ejecutar (por ejemplo
   `seguidor_linea_1_sensor/05_seguidor_linea.py`).
3. Pulsa **Ctrl + Shift + B**.
   Eso compila y sube **el archivo que tengas abierto** al hub.

Para elegir otro archivo o modo, usa **Ctrl + Shift + P → `Tasks: Run Task`**
(o *Terminal → Ejecutar tarea…*). Estas son las tareas disponibles:

| Tarea | Qué hace |
| :--- | :--- |
| ▶ **Ejecutar en el hub (archivo abierto)** | Compila y sube el archivo abierto. Usa USB si el hub está conectado; si no, Bluetooth. |
| ▶ **Ejecutar y ver mensajes (no soltar)** | Igual, pero se queda conectado para mostrar los `print()` en la terminal de VS Code. |
| ▶ **Ejecutar y soltar el robot** | Sube, arranca y se desconecta. El robot queda andando. |
| 🔵 **Ejecutar por Bluetooth** | Fuerza Bluetooth aunque el cable esté puesto. |
| ✅ **Revisar sintaxis (sin hub)** | Compila el archivo abierto sin necesidad de hub. |
| 🔌 **Estado del hub y la conexión** | Muestra `pybricksdev`, dispositivos LEGO por USB, puertos COM y Bluetooth. |
| **1 sensor · 01…05** | Ejecuta directamente cada script de `seguidor_linea_1_sensor/`. |
| **2 sensores · 01…05** | Ejecuta directamente cada script de `seguidor_linea_pybricks/`. |

**Cosas importantes:**

- **El archivo se guarda solo** antes de ejecutar la tarea (VS Code lo hace
  por defecto), así que no hace falta guardar a mano.
- **Los tests 01–04 esperan** y muestran sus mensajes en la terminal. Los
  sensores se pueden leer ahí mismo, sin abrir Pybricks Code.
- **El 05 se suelta**: el robot empieza a moverse y la tarea termina enseguida.
  Para detenerlo, pulsa el **botón central** del hub. Para volver a subir un
  cambio, pulsa otra vez la tarea.
- **Para ver la consola** (los `print()` del hub, como el panel de salida de
  Pybricks Code), usa la tarea **▶ Ejecutar y ver mensajes (no soltar)**.
  Se queda conectado y muestra el texto en vivo. Es solo texto: el panel
  gráfico de sensores y motores sigue siendo el de Pybricks Code. Mientras
  muestra mensajes, no desconectes el cable USB: se corta la sesión. Para que
  el robot corra libre, usa **▶ Ejecutar y soltar el robot**.
- **USB o Bluetooth es automático.** Si el hub no aparece por USB, se intenta
  por Bluetooth. Asegúrate de **cerrar Pybricks Code** antes: el hub solo
  admite una conexión a la vez.
- La extensión de Pybricks para VS Code **no se usa** en este flujo. Si te
  sigue pidiendo seleccionar el hub, puedes desinstalarla o deshabilitarla.

La primera vez, comprueba que `pybricksdev` está instalado:

```powershell
pybricksdev --version
# si no existe:
uv tool install pybricksdev
```

También puedes ejecutar los scripts a mano desde una terminal normal:

```powershell
# USB
pybricksdev run usb seguidor_linea_1_sensor\05_seguidor_linea.py

# Bluetooth (busca cualquier hub con Pybricks)
pybricksdev run ble seguidor_linea_1_sensor\05_seguidor_linea.py

# Solo revisar sintaxis
pybricksdev compile seguidor_linea_1_sensor\05_seguidor_linea.py
```

> **Carpetas de apoyo:** `tools/` contiene el script que usan las tareas
> (`ejecutar.ps1`) y el diagnóstico de conexión (`estado_hub.ps1`).
> `typings/` contiene los tipos de Pybricks para que VS Code muestre
> autocompletado y no marque `import pybricks` como error.

#### Opción 2: desde Pybricks Code (Navegador Chrome / Edge / Brave)

1. Abre [code.pybricks.com](https://code.pybricks.com/).
2. Conecta tu Spike Prime mediante el cable USB o vía Bluetooth.
3. Abre o pega el contenido del archivo que quieras ejecutar.
4. Haz clic en el botón de descarga/ejecución (botón ▶️ Play).

Úsalo sobre todo para **ver el estado de sensores y motores** con su interfaz
gráfica, o si no tienes VS Code a mano.

---

### 🎮 Controles del Hub
- **Letra 'L' en la pantalla:** El robot está encendido y listo en espera.
- **Botón DERECHO (Iniciar):**
  - Pulsa una vez: **Inicia** el seguimiento de línea.
  - Pulsa durante la marcha (o botón izquierdo): **Frena y detiene** el robot.
- **Botón IZQUIERDO (Calibración automática):**
  - Si cambias de mesa o iluminación, coloca el robot sobre la línea y pulsa el botón izquierdo.
  - El robot hará un breve escaneo de derecha a izquierda leyendo el negro de la línea y el blanco del piso, calibrando los sensores automáticamente.
- **Botón CENTRAL:** Reservado por Pybricks como botón de parada general / apagado del sistema.

---

### 🆕 Versión 2: `main_v2.py` (mejorada)

Esta versión incluye:

- **Calibración automática** al iniciar: el robot mide 20 reflectancias y calcula los valores normalizados de cada sensor.
- **Controlador PID completo** (proporcional + integral + derivativo) para un seguimiento más estable.
- **Reducción de velocidad en curvas**: cuando el robot gira mucho, la velocidad se reduce proporcionalmente al valor del giro.
- **Manejo de botones** (R/L): detiene el robot y muestra un sonido de confirmación.
- **Visualización en pantalla** del estado del robot.

Para usarla, pega el contenido de [`main_v2.py`](./main_v2.py) en Pybricks Code y haz clic en ▶️ Play.

```powershell
pybricksdev run ble -n jgLegoHUB1 main_v2.py
```

---

### ⚙️ Ajuste de Velocidad y PID (`main.py`)

Si deseas que el robot vaya más rápido o se comporte diferente en las curvas, modifica estas variables al inicio de [`main.py`](./main.py):

```python
BASE_SPEED = 280   # Velocidad en grados/seg (subir a 400-600 para competir)
KP = 2.4          # Si zigzaguea mucho, reduce KP (ej: 1.8). Si no gira en curvas, aumenta KP (ej: 3.0)
KD = 14.0         # Amortiguador de oscilaciones. Ayuda a altas velocidades.
KI = 0.002        # Corrección acumulada.
```

> **Nota si avanza en reversa:**
> Si al iniciar el robot avanza alejándose de los sensores en lugar de avanzar hacia adelante, simplemente invierte los sentidos en las líneas de los motores:
> ```python
> motor_left = Motor(Port.F, Direction.CLOCKWISE)
> motor_right = Motor(Port.B, Direction.COUNTERCLOCKWISE)
> ```
