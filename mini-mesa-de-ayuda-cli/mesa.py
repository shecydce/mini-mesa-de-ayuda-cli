"""Mini mesa de ayuda por línea de comandos (Python + SQLite).

Ciclo de vida de un ticket:  abierto -> en_curso (se asigna técnico) -> cerrado (con solución).
Cada prioridad tiene un SLA (tiempo máximo de resolución) y el reporte mide el cumplimiento.

Uso:
    python mesa.py crear "No imprime" Impresoras alta "Juan Perez"
    python mesa.py asignar 1 "Maria Gomez"
    python mesa.py cerrar 1 "Se reinició el servicio de cola de impresión"
    python mesa.py listar --estado abierto
    python mesa.py reporte
"""
import argparse
import os
import sqlite3
from datetime import datetime

RUTA_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
FORMATO = "%Y-%m-%d %H:%M"

CATEGORIAS = ["Hardware", "Software", "Red", "Cuentas", "Impresoras", "Otros"]
SLA_HORAS = {"critica": 4, "alta": 8, "media": 24, "baja": 72}


def conectar(ruta="mesa.db"):
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    with open(RUTA_SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    return conn


def _ahora(ahora):
    return (ahora or datetime.now()).strftime(FORMATO)


def _categoria_valida(categoria):
    for c in CATEGORIAS:
        if c.lower() == categoria.strip().lower():
            return c
    raise ValueError(f"Categoría inválida: {categoria!r}. Opciones: {', '.join(CATEGORIAS)}")


def _prioridad_valida(prioridad):
    p = prioridad.strip().lower()
    if p not in SLA_HORAS:
        raise ValueError(f"Prioridad inválida: {prioridad!r}. Opciones: {', '.join(SLA_HORAS)}")
    return p


def _obtener(conn, ticket_id):
    fila = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if fila is None:
        raise ValueError(f"No existe el ticket #{ticket_id}")
    return fila


def crear_ticket(conn, titulo, categoria, prioridad, solicitante, descripcion="", ahora=None):
    if not titulo.strip():
        raise ValueError("El título no puede estar vacío")
    cur = conn.execute(
        """INSERT INTO tickets (titulo, descripcion, categoria, prioridad, solicitante, creado)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (titulo.strip(), descripcion, _categoria_valida(categoria),
         _prioridad_valida(prioridad), solicitante, _ahora(ahora)),
    )
    conn.commit()
    return cur.lastrowid


def asignar_ticket(conn, ticket_id, tecnico):
    t = _obtener(conn, ticket_id)
    if t["estado"] == "cerrado":
        raise ValueError(f"El ticket #{ticket_id} está cerrado; reabrilo primero")
    conn.execute("UPDATE tickets SET tecnico = ?, estado = 'en_curso' WHERE id = ?", (tecnico, ticket_id))
    conn.commit()


def cerrar_ticket(conn, ticket_id, solucion, ahora=None):
    t = _obtener(conn, ticket_id)
    if t["estado"] != "en_curso":
        raise ValueError(f"Solo se pueden cerrar tickets en curso (el #{ticket_id} está {t['estado']})")
    if not solucion.strip():
        raise ValueError("Hay que describir la solución")
    conn.execute(
        "UPDATE tickets SET estado = 'cerrado', cerrado = ?, solucion = ? WHERE id = ?",
        (_ahora(ahora), solucion.strip(), ticket_id),
    )
    conn.commit()


def reabrir_ticket(conn, ticket_id):
    t = _obtener(conn, ticket_id)
    if t["estado"] != "cerrado":
        raise ValueError(f"El ticket #{ticket_id} no está cerrado")
    conn.execute(
        "UPDATE tickets SET estado = 'abierto', tecnico = NULL, cerrado = NULL, solucion = NULL WHERE id = ?",
        (ticket_id,),
    )
    conn.commit()


def listar_tickets(conn, estado=None, tecnico=None):
    sql, params, filtros = "SELECT * FROM tickets", [], []
    if estado:
        filtros.append("estado = ?"); params.append(estado)
    if tecnico:
        filtros.append("tecnico = ?"); params.append(tecnico)
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    return conn.execute(sql + " ORDER BY id", params).fetchall()


def horas_entre(inicio, fin):
    """Horas transcurridas entre dos textos 'AAAA-MM-DD HH:MM'."""
    delta = datetime.strptime(fin, FORMATO) - datetime.strptime(inicio, FORMATO)
    return round(delta.total_seconds() / 3600, 1)


def reporte(conn, ahora=None):
    """Métricas de la mesa de ayuda."""
    ahora_txt = _ahora(ahora)
    tickets = conn.execute("SELECT * FROM tickets").fetchall()

    abiertos_por_prioridad = {p: 0 for p in SLA_HORAS}
    vencidos_abiertos = []
    horas_por_categoria = {}
    cerrados = cumplieron = 0

    for t in tickets:
        sla = SLA_HORAS[t["prioridad"]]
        if t["estado"] == "cerrado":
            horas = horas_entre(t["creado"], t["cerrado"])
            horas_por_categoria.setdefault(t["categoria"], []).append(horas)
            cerrados += 1
            cumplieron += horas <= sla
        else:
            abiertos_por_prioridad[t["prioridad"]] += 1
            if horas_entre(t["creado"], ahora_txt) > sla:
                vencidos_abiertos.append(t["id"])

    return {
        "total": len(tickets),
        "abiertos_por_prioridad": abiertos_por_prioridad,
        "promedio_horas_por_categoria": {
            c: round(sum(h) / len(h), 1) for c, h in sorted(horas_por_categoria.items())
        },
        "cerrados": cerrados,
        "cumplimiento_sla": round(100 * cumplieron / cerrados, 1) if cerrados else None,
        "vencidos_sin_cerrar": vencidos_abiertos,
    }


def formatear_reporte(r):
    lineas = ["REPORTE DE LA MESA DE AYUDA", "=" * 27, f"Tickets totales: {r['total']}", ""]
    lineas.append("Abiertos o en curso por prioridad:")
    for p, n in r["abiertos_por_prioridad"].items():
        lineas.append(f"  {p:<8} {n}")
    lineas += ["", "Tiempo promedio de resolución por categoría (horas):"]
    if r["promedio_horas_por_categoria"]:
        for c, h in r["promedio_horas_por_categoria"].items():
            lineas.append(f"  {c:<11} {h}")
    else:
        lineas.append("  (sin tickets cerrados)")
    sla = "sin datos" if r["cumplimiento_sla"] is None else f"{r['cumplimiento_sla']}% de {r['cerrados']} cerrados"
    lineas += ["", f"Cumplimiento de SLA: {sla}"]
    vencidos = r["vencidos_sin_cerrar"]
    lineas.append("Sin cerrar y fuera de SLA: " + (", ".join(f"#{i}" for i in vencidos) if vencidos else "ninguno"))
    return "\n".join(lineas)


def _tabla(tickets):
    if not tickets:
        return "(sin tickets)"
    filas = [["ID", "ESTADO", "PRIORIDAD", "CATEGORIA", "TECNICO", "TITULO"]]
    for t in tickets:
        filas.append([str(t["id"]), t["estado"], t["prioridad"], t["categoria"],
                      t["tecnico"] or "-", t["titulo"]])
    anchos = [max(len(f[i]) for f in filas) for i in range(6)]
    return "\n".join("  ".join(v.ljust(anchos[i]) for i, v in enumerate(f)) for f in filas)


def main():
    p = argparse.ArgumentParser(description="Mini mesa de ayuda")
    p.add_argument("--db", default="mesa.db")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("crear")
    s.add_argument("titulo"); s.add_argument("categoria"); s.add_argument("prioridad"); s.add_argument("solicitante")
    s.add_argument("--descripcion", default="")
    s = sub.add_parser("asignar"); s.add_argument("id", type=int); s.add_argument("tecnico")
    s = sub.add_parser("cerrar"); s.add_argument("id", type=int); s.add_argument("solucion")
    s = sub.add_parser("reabrir"); s.add_argument("id", type=int)
    s = sub.add_parser("listar"); s.add_argument("--estado", choices=["abierto", "en_curso", "cerrado"]); s.add_argument("--tecnico")
    s = sub.add_parser("ver"); s.add_argument("id", type=int)
    s = sub.add_parser("reporte"); s.add_argument("--ahora", help="fecha y hora 'AAAA-MM-DD HH:MM' (por defecto, ahora)")

    a = p.parse_args()
    conn = conectar(a.db)
    try:
        if a.comando == "crear":
            print(f"Ticket #{crear_ticket(conn, a.titulo, a.categoria, a.prioridad, a.solicitante, a.descripcion)} creado")
        elif a.comando == "asignar":
            asignar_ticket(conn, a.id, a.tecnico); print(f"Ticket #{a.id} asignado a {a.tecnico}")
        elif a.comando == "cerrar":
            cerrar_ticket(conn, a.id, a.solucion); print(f"Ticket #{a.id} cerrado")
        elif a.comando == "reabrir":
            reabrir_ticket(conn, a.id); print(f"Ticket #{a.id} reabierto")
        elif a.comando == "listar":
            print(_tabla(listar_tickets(conn, a.estado, a.tecnico)))
        elif a.comando == "ver":
            t = _obtener(conn, a.id)
            for k in t.keys():
                print(f"{k:<12}: {t[k] if t[k] is not None else '-'}")
        elif a.comando == "reporte":
            ahora = datetime.strptime(a.ahora, FORMATO) if a.ahora else None
            print(formatear_reporte(reporte(conn, ahora)))
    except ValueError as e:
        p.exit(2, f"Error: {e}\n")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
