# -----------------------------------------------------------------------------
#  Compila y sube un programa Pybricks al hub.
#
#  Uso normal (lo hacen las tareas de VS Code por ti):
#    powershell -NoProfile -ExecutionPolicy Bypass -File tools\ejecutar.ps1 ^
#        -Ruta "seguidor_linea_1_sensor\05_seguidor_linea.py"
#
#  Opciones:
#    -Conexion auto|usb|ble   auto = USB si esta conectado, si no Bluetooth
#    -Modo     auto|esperar|soltar
#                              auto = espera en los tests y suelta en 05/main
#    -SoloCompilar            solo revisa la sintaxis, no toca el hub
# -----------------------------------------------------------------------------
param(
    [Parameter(Mandatory = $true)][string]$Ruta,
    [ValidateSet("auto", "usb", "ble")][string]$Conexion = "auto",
    [ValidateSet("auto", "esperar", "soltar")][string]$Modo = "auto",
    [switch]$SoloCompilar
)

$ErrorActionPreference = "Continue"

function Linea($texto, $color = "Gray") {
    Write-Host $texto -ForegroundColor $color
}

function Fallo($texto) {
    Write-Host ""
    Write-Host "  [X] $texto" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# --- Comprobar el archivo -----------------------------------------------------
if (-not (Test-Path -LiteralPath $Ruta)) {
    Fallo "No existe el archivo: $Ruta"
}
if ([System.IO.Path]::GetExtension($Ruta) -ne ".py") {
    Fallo "Abre un archivo .py en el editor antes de ejecutar esta tarea."
}
$Ruta = (Resolve-Path -LiteralPath $Ruta).Path
$nombre = Split-Path $Ruta -Leaf

# --- Localizar pybricksdev ----------------------------------------------------
$exe = (Get-Command pybricksdev -ErrorAction SilentlyContinue).Source
if (-not $exe) {
    $alternativa = Join-Path $env:USERPROFILE ".local\bin\pybricksdev.exe"
    if (Test-Path -LiteralPath $alternativa) { $exe = $alternativa }
}
if (-not $exe) {
    Fallo "No encuentro 'pybricksdev'. Instalalo con:  uv tool install pybricksdev"
}

# --- libusb para USB ----------------------------------------------------------
# pybricksdev incluye libusb en el paquete libusb_package, pero pyusb no lo
# encuentra solo en Windows. Buscamos la DLL y la ponemos en el PATH.
function HabilitarLibusb {
    $raices = @()
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        try {
            $dirUv = (& uv tool dir 2>$null | Select-Object -First 1)
            if ($dirUv) { $raices += (Join-Path $dirUv "pybricksdev") }
        } catch { }
    }
    $raices += (Join-Path $env:APPDATA "uv\tools\pybricksdev")
    $raices += (Join-Path $env:USERPROFILE ".local\pipx\venvs\pybricksdev")
    $raices += (Join-Path $env:APPDATA "Python")
    $raices += (Join-Path $env:LOCALAPPDATA "Programs\Python")

    foreach ($raiz in $raices) {
        if (-not (Test-Path -LiteralPath $raiz)) { continue }
        $dll = Get-ChildItem -LiteralPath $raiz -Recurse -Filter "libusb-1.0.dll" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($dll) {
            $dir = $dll.DirectoryName
            if ($env:PATH -notlike "*$dir*") {
                $env:PATH = "$dir;$env:PATH"
            }
            return
        }
    }
}

# --- 1. Compilar (rapido, sin hub) --------------------------------------------
Linea ""
Linea "  Revisando $nombre ..." "Cyan"

$salida = [System.IO.Path]::GetTempFileName()
$errores = [System.IO.Path]::GetTempFileName()
& $exe compile $Ruta 1> $salida 2> $errores
$codigo = $LASTEXITCODE

$textoError = ""
if (Test-Path -LiteralPath $errores) {
    $textoError = Get-Content -LiteralPath $errores -Raw
}
Remove-Item -LiteralPath $salida, $errores -Force -ErrorAction SilentlyContinue

if ($codigo -ne 0) {
    # pybricksdev lanza un traceback poco claro. Usamos Python para mostrar
    # el error real con numero de linea.
    $detalle = ""
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $detalle = & python "$PSScriptRoot\revisar_sintaxis.py" $Ruta 2> $null | Out-String
    }
    if ($detalle -and $detalle.Trim()) {
        Write-Host $detalle.Trim() -ForegroundColor Red
    } elseif ($textoError) {
        Write-Host $textoError -ForegroundColor Red
    }
    Fallo "El codigo no compila. Corrige el error de arriba y vuelve a intentar."
}
if ($textoError -and $textoError.Trim()) {
    Write-Host $textoError -ForegroundColor Yellow
}
Linea "  Sintaxis OK" "Green"

if ($SoloCompilar) { exit 0 }

# --- 2. Elegir conexion -------------------------------------------------------
function HayHubUSB {
    try {
        $dispositivos = @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop |
            Where-Object { $_.DeviceID -and $_.DeviceID -like "*VID_0694*" })
        return ($dispositivos.Count -gt 0)
    } catch {
        return $false
    }
}

$destino = $Conexion
if ($destino -eq "auto") {
    if (HayHubUSB) {
        $destino = "usb"
    } else {
        $destino = "ble"
        Linea "  No veo el hub por USB: probando por Bluetooth..." "Yellow"
    }
}

# --- 3. Decidir si esperar o soltar -------------------------------------------
# Los tests (01..04) terminan solos y sus mensajes importan: esperamos.
# El seguidor (05) y main* no terminan nunca: se sueltan y el robot arranca.
$esperar = $true
if ($Modo -eq "soltar") {
    $esperar = $false
} elseif ($Modo -eq "auto") {
    if ($nombre -match "^(05_|main)") { $esperar = $false }
}

# --- 4. Subir y ejecutar ------------------------------------------------------
function Subir($conexion) {
    $argumentos = @("run", $conexion, $Ruta)
    if (-not $esperar) { $argumentos += "--no-wait" }

    $errArchivo = [System.IO.Path]::GetTempFileName()
    & $exe @argumentos 2> $errArchivo
    $salidaCodigo = $LASTEXITCODE

    $texto = ""
    if (Test-Path -LiteralPath $errArchivo) {
        $texto = Get-Content -LiteralPath $errArchivo -Raw
    }
    Remove-Item -LiteralPath $errArchivo -Force -ErrorAction SilentlyContinue

    return [pscustomobject]@{ Codigo = $salidaCodigo; Error = $texto }
}

Linea ""
Linea "  Subiendo a $($destino.ToUpper()) ..." "Cyan"
Linea ""

if ($destino -eq "usb") { HabilitarLibusb }

$resultado = Subir $destino

# Si USB no esta disponible, reintentar por Bluetooth (solo en modo auto).
$errorUSB = $resultado.Error -match "NoBackendError|Pybricks Hub not found|No backend available"
if ($resultado.Codigo -ne 0 -and $Conexion -eq "auto" -and $destino -eq "usb" -and $errorUSB) {
    Linea "  El USB no respondio: reintentando por Bluetooth..." "Yellow"
    Linea ""
    $resultado = Subir "ble"
    $destino = "ble"
}

$codigo = $resultado.Codigo
$errTexto = $resultado.Error

Linea ""
if ($codigo -eq 0) {
    if ($esperar) {
        Linea "  Listo." "Green"
    } else {
        Linea "  Listo: el programa ya esta corriendo en el hub." "Green"
        Linea "  Para detenerlo, pulsa el boton central del hub." "Gray"
    }
    exit 0
}

Linea "  [X] No se pudo ejecutar (codigo $codigo)." "Red"
Linea ""

if ($errTexto -match "NoBackendError|No backend available") {
    Linea "  Falta el controlador USB (libusb) o no es accesible." "Red"
    Linea "  Usa la tarea 'Ejecutar por Bluetooth'." "Yellow"
    Linea ""
} elseif (-not ($errTexto -match "TimeoutError|Pybricks Hub not found|No powered devices|No device")) {
    if ($errTexto -and $errTexto.Trim()) {
        Write-Host $errTexto.Trim() -ForegroundColor DarkGray
        Linea ""
    }
}

Linea "  Revisa:" "Yellow"
Linea "   - USB: cable de datos (no solo de carga) y hub encendido." "Yellow"
Linea "   - Bluetooth: Bluetooth del PC encendido y hub cerca." "Yellow"
Linea "   - Cierra Pybricks Code: el hub solo acepta una conexion a la vez." "Yellow"
Linea "   - Prueba la tarea 'Estado del hub y la conexion'." "Yellow"
Linea ""
exit $codigo
