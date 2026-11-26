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

#### Opción 1: Desde Pybricks Code (Navegador Chrome / Edge / Brave)
1. Abre [code.pybricks.com](https://code.pybricks.com/).
2. Conecta tu Spike Prime mediante el cable USB (seleccionando el puerto serie/COM de tu hub `jgLegoHUB1`) o vía Bluetooth.
3. Abre o pega el contenido del archivo [`main.py`](./main.py).
4. Haz clic en el botón de descarga/ejecución (botón ▶️ Play).

#### Opción 2: Usando `pybricksdev` desde la terminal
```powershell
pybricksdev run ble -n jgLegoHUB1 main.py
```

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
