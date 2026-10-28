"""Carga tickets ficticios de ejemplo en mesa.db (ejecutar desde la raíz del proyecto)."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mesa  # noqa: E402


def f(texto):
    return datetime.strptime(texto, mesa.FORMATO)


conn = mesa.conectar("mesa.db")

# (titulo, categoria, prioridad, solicitante, creado, tecnico, cerrado, solucion)
TICKETS = [
    ("La impresora no imprime", "Impresoras", "alta", "Juan Perez", "2026-10-26 08:00",
     "Maria Gomez", "2026-10-26 09:30", "Se reinició el servicio de cola de impresión"),
    ("Sin internet en el área de ventas", "Red", "critica", "Juan Perez", "2026-10-26 08:15",
     "Pedro Ruiz", "2026-10-26 10:15", "Se reinició el switch y se verificó el DHCP"),
    ("Olvidé mi contraseña", "Cuentas", "media", "Lucia Fernandez", "2026-10-26 09:00",
     "Maria Gomez", "2026-10-26 11:00", "Se restableció la contraseña y se exigió cambio al iniciar"),
    ("Excel se cierra solo", "Software", "media", "Lucia Fernandez", "2026-10-25 09:00",
     "Pedro Ruiz", None, None),
    ("Monitor sin señal", "Hardware", "baja", "Juan Perez", "2026-10-26 10:00", None, None, None),
    ("Wifi muy lento en reuniones", "Red", "alta", "Lucia Fernandez", "2026-10-26 07:00",
     "Pedro Ruiz", "2026-10-26 17:00", "Se cambió el canal del access point"),
    ("Cuenta bloqueada", "Cuentas", "alta", "Juan Perez", "2026-10-26 15:00", None, None, None),
]

for titulo, cat, prio, quien, creado, tecnico, cerrado, solucion in TICKETS:
    ticket = mesa.crear_ticket(conn, titulo, cat, prio, quien, ahora=f(creado))
    if tecnico:
        mesa.asignar_ticket(conn, ticket, tecnico)
    if cerrado:
        mesa.cerrar_ticket(conn, ticket, solucion, ahora=f(cerrado))

conn.close()
print("Tickets de ejemplo cargados en mesa.db")
