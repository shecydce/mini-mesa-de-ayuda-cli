# Mini mesa de ayuda por línea de comandos

Sistema de tickets simple en Python + SQLite que reproduce el ciclo de trabajo de una mesa de ayuda: **abrir** un incidente, **asignarlo** a un técnico, **cerrarlo** con su solución y **medir** tiempos y cumplimiento de SLA.

Sin dependencias externas: solo Python 3.

## Ciclo de vida
```
abierto --asignar--> en_curso --cerrar (con solución)--> cerrado
                                                          |
                                                      reabrir --> abierto
```
Reglas que valida el programa: no se puede cerrar un ticket sin asignarlo, hay que escribir la solución, un ticket cerrado no se reasigna sin reabrirlo, y categorías y prioridades deben ser válidas.

## SLA por prioridad
| Prioridad | Tiempo máximo de resolución |
|---|---|
| critica | 4 horas |
| alta | 8 horas |
| media | 24 horas |
| baja | 72 horas |

Los valores están en la constante `SLA_HORAS` de `mesa.py` y se pueden cambiar.

## Uso
```bash
python ejemplos/cargar_ejemplo.py     # carga tickets ficticios (opcional)

python mesa.py crear "No imprime" Impresoras alta "Juan Perez"
python mesa.py asignar 1 "Maria Gomez"
python mesa.py cerrar 1 "Se reinició el servicio de cola de impresión"
python mesa.py reabrir 1
python mesa.py listar [--estado abierto|en_curso|cerrado] [--tecnico "Maria Gomez"]
python mesa.py ver 1
python mesa.py reporte
```
Categorías: Hardware, Software, Red, Cuentas, Impresoras, Otros.

## Salida de ejemplo
Con los datos ficticios de `ejemplos/cargar_ejemplo.py`.

`listar`
```
ID  ESTADO    PRIORIDAD  CATEGORIA   TECNICO      TITULO                           
1   cerrado   alta       Impresoras  Maria Gomez  La impresora no imprime          
2   cerrado   critica    Red         Pedro Ruiz   Sin internet en el área de ventas
3   cerrado   media      Cuentas     Maria Gomez  Olvidé mi contraseña             
4   en_curso  media      Software    Pedro Ruiz   Excel se cierra solo             
5   abierto   baja       Hardware    -            Monitor sin señal                
6   cerrado   alta       Red         Pedro Ruiz   Wifi muy lento en reuniones      
7   abierto   alta       Cuentas     -            Cuenta bloqueada                 
```

`ver 1`
```
id          : 1
titulo      : La impresora no imprime
descripcion : 
categoria   : Impresoras
prioridad   : alta
estado      : cerrado
solicitante : Juan Perez
tecnico     : Maria Gomez
creado      : 2026-10-26 08:00
cerrado     : 2026-10-26 09:30
solucion    : Se reinició el servicio de cola de impresión
```

`reporte --ahora "2026-10-26 18:00"`
```
REPORTE DE LA MESA DE AYUDA
===========================
Tickets totales: 7

Abiertos o en curso por prioridad:
  critica  0
  alta     1
  media    1
  baja     1

Tiempo promedio de resolución por categoría (horas):
  Cuentas     2.0
  Impresoras  1.5
  Red         6.0

Cumplimiento de SLA: 75.0% de 4 cerrados
Sin cerrar y fuera de SLA: #4
```
(La opción `--ahora` fija la fecha del reporte para que el resultado sea reproducible; sin ella se usa la hora actual.)



