# Simulador offline (solo PC)

Este simulador **no se sube al hub**. Sirve para comparar el programa final
con la versión anterior sin gastar batería ni pista.

## Qué incluye

| Archivo | Para qué sirve |
| :--- | :--- |
| `simular_seguidor.py` | Motor de simulación: pista, robot, sensor y módulos falsos de Pybricks. |
| `_baseline_05.py` | Copia de la versión anterior del `05`, para comparar. |

## Cómo ejecutarlo

Desde la carpeta `seguidor_linea_1_sensor`:

```powershell
# Comparar la versión anterior contra la nueva en todos los escenarios
python sim\simular_seguidor.py

# Solo la versión nueva
python sim\simular_seguidor.py 05_seguidor_linea.py

# Solo la versión anterior
python sim\simular_seguidor.py sim\_baseline_05.py

# Elegir escenarios
$env:SIM_ESC = "recta,discontinua,perdida_cerca"
python sim\simular_seguidor.py 05_seguidor_linea.py

# Ver la traza de un escenario (cada 100 ms)
$env:SIM_TRAZA = "discontinua"
python sim\simular_seguidor.py 05_seguidor_linea.py
```

## Escenarios

| Escenario | Qué prueba |
| :--- | :--- |
| `recta` | Velocidad máxima y precisión en recta. |
| `curvas` | Curvas de 250 mm de radio. |
| `curva_cerrada` | Horquilla de 120 mm. |
| `curva_90` | Curva de 90° con radio 60 mm. |
| `esquina` | Esquina de 90° muy cerrada, antihoraria (caso límite). |
| `esquina_der` | Esquina de 90° muy cerrada, horaria (caso límite). |
| `discontinua` | Línea discontinua: 70 mm de línea / 30 mm de hueco. |
| `discontinua_var` | Huecos alternos de 30 y 60 mm (pista variable). |
| `colina` | Colina suave (sube y baja) como las de la pista. |
| `hueco_largo` | Hueco de 150 mm (caso límite). |
| `perdida` | El robot empieza 50 mm fuera de la línea (caso límite). |
| `perdida_cerca` | El robot empieza 15 mm fuera del borde y debe buscar. |

## Cómo leer la tabla

- **v media**: velocidad media real del robot, en mm/s.
- **RMS / Max**: error lateral medio y máximo respecto del borde, en mm.
- **tiempo**: duración del escenario.
- **cruce**: segundos en estado `SALTAR`/`RETROCESO` (huecos).
- **busca**: segundos en estado `BUSCAR` (búsqueda de 180°).
- **barrido**: grados máximos girados en una búsqueda.
- **final**: último símbolo mostrado (`|` normal, `!` buscando, `E` perdido).

## Modelo (para que las cifras no engañen)

- Pista de 19 mm de ancho, borde de transición suave y ruido de ±1.2 %.
- Sensor 30 mm delante del centro del robot.
- Motores con constante de tiempo (60 ms velocidad, 85 ms giro) y una
  deriva de rumbo de 1.8°/s que simula ruedas imperfectas.
- No modela patinaje, batería baja, sombras ni la inercia real del chasis.

Por eso el simulador sirve para **comparar** y detectar lógicas que fallan,
pero la prueba final siempre es en el robot. Si el robot real se comporta
distinto, usa la tabla de ajuste del `README.md` principal.
