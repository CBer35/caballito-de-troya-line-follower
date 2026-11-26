"""Revisa la sintaxis de un archivo .py y muestra un error corto.

Se usa desde tools/ejecutar.ps1 para que, cuando el codigo no compila, se vea
el numero de linea y el mensaje en vez de un traceback largo.
"""

import sys

if len(sys.argv) != 2:
    print("Uso: python tools/revisar_sintaxis.py <archivo.py>")
    sys.exit(2)

ruta = sys.argv[1]

try:
    with open(ruta, encoding="utf-8") as archivo:
        compile(archivo.read(), ruta, "exec")
except SyntaxError as error:
    print("  Error de sintaxis en %s, linea %s:" % (ruta, error.lineno))
    print("  %s" % error.msg)
    if error.text:
        print("")
        print("  %s" % error.text.rstrip())
        if error.offset:
            print("  %s^" % (" " * max(0, error.offset - 1)))
    sys.exit(1)
except OSError as error:
    print("  No se pudo leer el archivo: %s" % error)
    sys.exit(1)
