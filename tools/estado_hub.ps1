# -----------------------------------------------------------------------------
#  Muestra el estado del entorno: pybricksdev, hub por USB, puertos COM y
#  Bluetooth. Sirve para saber por que no conecta.
# -----------------------------------------------------------------------------
$ErrorActionPreference = "Continue"

function Linea($texto, $color = "Gray") {
    Write-Host $texto -ForegroundColor $color
}

Linea ""
Linea "  ==========================================" "DarkCyan"
Linea "   ESTADO DEL ENTORNO PYBricks" "Cyan"
Linea "  ==========================================" "DarkCyan"

# --- pybricksdev --------------------------------------------------------------
Linea ""
Linea "  HERRAMIENTA" "Cyan"
$exe = (Get-Command pybricksdev -ErrorAction SilentlyContinue).Source
if (-not $exe) {
    $alternativa = Join-Path $env:USERPROFILE ".local\bin\pybricksdev.exe"
    if (Test-Path -LiteralPath $alternativa) { $exe = $alternativa }
}
if ($exe) {
    Linea "  pybricksdev : $(& $exe --version 2>&1)" "Green"
    Linea "  ruta        : $exe"
} else {
    Linea "  pybricksdev : NO INSTALADO" "Red"
    Linea "  Instalalo con:  uv tool install pybricksdev" "Yellow"
}

try {
    Linea "  Python      : $(python --version 2>&1)"
} catch {
    Linea "  Python      : no encontrado" "Yellow"
}

# --- Hub por USB --------------------------------------------------------------
Linea ""
Linea "  HUB POR USB" "Cyan"
try {
    $usb = @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop |
        Where-Object { $_.DeviceID -and $_.DeviceID -like "*VID_0694*" })
    if ($usb.Count -eq 0) {
        Linea "  No hay ningun dispositivo LEGO conectado por USB." "Yellow"
        Linea "  Usa el cable de datos y enciende el hub." "Yellow"
    } else {
        foreach ($d in $usb) {
            Linea "  - $($d.Name)" "Green"
            Linea "    $($d.DeviceID)" "DarkGray"
        }
    }
} catch {
    Linea "  No se pudo consultar el USB." "Yellow"
}

# --- Puertos COM --------------------------------------------------------------
Linea ""
Linea "  PUERTOS COM" "Cyan"
try {
    $com = [System.IO.Ports.SerialPort]::GetPortNames()
    if (-not $com -or $com.Count -eq 0) {
        Linea "  Ninguno (normal en modo Pybricks por USB)." "Yellow"
    } else {
        foreach ($p in $com) { Linea "  - $p" }
    }
} catch {
    Linea "  No se pudieron leer los puertos COM." "Yellow"
}

# --- Bluetooth ----------------------------------------------------------------
Linea ""
Linea "  BLUETOOTH DEL PC" "Cyan"
try {
    $bt = @(Get-PnpDevice -Class Bluetooth -ErrorAction Stop |
        Where-Object { $_.Status -eq "OK" })
    if ($bt.Count -eq 0) {
        Linea "  No se detecta adaptador Bluetooth activo." "Yellow"
    } else {
        Linea "  Adaptador activo. Si el hub no aparece:" "Green"
        Linea "  - Enciende el hub y alejalo de otros dispositivos." "Yellow"
        Linea "  - Cierra Pybricks Code (solo admite una conexion)." "Yellow"
    }
} catch {
    Linea "  No se pudo consultar el Bluetooth." "Yellow"
}

# --- Recomendaciones ----------------------------------------------------------
Linea ""
Linea "  QUE HACER SI NO CONECTA" "Cyan"
Linea "  1. Cierra Pybricks Code y cualquier otra pestana conectada al hub." "Yellow"
Linea "  2. Prueba primero por USB con un cable de datos." "Yellow"
Linea "  3. Si sigue igual, usa la tarea 'Ejecutar por Bluetooth'." "Yellow"
Linea "  4. Apaga y enciende el hub; espera 5 segundos." "Yellow"
Linea ""
