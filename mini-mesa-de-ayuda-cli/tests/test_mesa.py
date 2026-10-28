import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mesa  # noqa: E402


def f(texto):
    return datetime.strptime(texto, mesa.FORMATO)


class TestCicloDeVida(unittest.TestCase):
    def setUp(self):
        self.conn = mesa.conectar(":memory:")

    def tearDown(self):
        self.conn.close()

    def nuevo(self, **kw):
        datos = dict(titulo="No imprime", categoria="impresoras", prioridad="Alta",
                     solicitante="Juan", ahora=f("2026-10-26 09:00"))
        datos.update(kw)
        return mesa.crear_ticket(self.conn, **datos)

    def test_crear_normaliza_categoria_y_prioridad(self):
        t = self.nuevo()
        fila = mesa.listar_tickets(self.conn)[0]
        self.assertEqual(t, fila["id"])
        self.assertEqual(fila["categoria"], "Impresoras")
        self.assertEqual(fila["prioridad"], "alta")
        self.assertEqual(fila["estado"], "abierto")

    def test_datos_invalidos(self):
        with self.assertRaises(ValueError):
            self.nuevo(categoria="Cocina")
        with self.assertRaises(ValueError):
            self.nuevo(prioridad="urgentisima")
        with self.assertRaises(ValueError):
            self.nuevo(titulo="   ")

    def test_flujo_completo(self):
        t = self.nuevo()
        mesa.asignar_ticket(self.conn, t, "Maria")
        self.assertEqual(mesa.listar_tickets(self.conn, estado="en_curso")[0]["tecnico"], "Maria")
        mesa.cerrar_ticket(self.conn, t, "Se reinició el spooler", ahora=f("2026-10-26 10:30"))
        fila = mesa.listar_tickets(self.conn, estado="cerrado")[0]
        self.assertEqual(fila["solucion"], "Se reinició el spooler")
        self.assertEqual(mesa.horas_entre(fila["creado"], fila["cerrado"]), 1.5)

    def test_no_se_puede_cerrar_sin_asignar(self):
        t = self.nuevo()
        with self.assertRaises(ValueError):
            mesa.cerrar_ticket(self.conn, t, "solución")

    def test_cerrar_exige_solucion(self):
        t = self.nuevo()
        mesa.asignar_ticket(self.conn, t, "Maria")
        with self.assertRaises(ValueError):
            mesa.cerrar_ticket(self.conn, t, "  ")

    def test_ticket_inexistente(self):
        with self.assertRaises(ValueError):
            mesa.asignar_ticket(self.conn, 999, "Maria")

    def test_no_se_asigna_un_cerrado_pero_si_se_reabre(self):
        t = self.nuevo()
        mesa.asignar_ticket(self.conn, t, "Maria")
        mesa.cerrar_ticket(self.conn, t, "ok", ahora=f("2026-10-26 10:00"))
        with self.assertRaises(ValueError):
            mesa.asignar_ticket(self.conn, t, "Pedro")
        mesa.reabrir_ticket(self.conn, t)
        fila = mesa.listar_tickets(self.conn)[0]
        self.assertEqual((fila["estado"], fila["tecnico"], fila["solucion"]), ("abierto", None, None))

    def test_filtrar_por_tecnico(self):
        a = self.nuevo(); b = self.nuevo(titulo="Sin internet", categoria="Red")
        mesa.asignar_ticket(self.conn, a, "Maria")
        mesa.asignar_ticket(self.conn, b, "Pedro")
        self.assertEqual([x["id"] for x in mesa.listar_tickets(self.conn, tecnico="Pedro")], [b])


class TestReporte(unittest.TestCase):
    def setUp(self):
        self.conn = mesa.conectar(":memory:")
        # Cerrado dentro de SLA: alta (8 h), resuelto en 2 h
        a = mesa.crear_ticket(self.conn, "A", "Red", "alta", "x", ahora=f("2026-10-26 08:00"))
        mesa.asignar_ticket(self.conn, a, "Maria")
        mesa.cerrar_ticket(self.conn, a, "ok", ahora=f("2026-10-26 10:00"))
        # Cerrado fuera de SLA: critica (4 h), resuelto en 6 h
        b = mesa.crear_ticket(self.conn, "B", "Red", "critica", "x", ahora=f("2026-10-26 08:00"))
        mesa.asignar_ticket(self.conn, b, "Pedro")
        mesa.cerrar_ticket(self.conn, b, "ok", ahora=f("2026-10-26 14:00"))
        # Abierto y vencido: media (24 h), creado hace 30 h
        mesa.crear_ticket(self.conn, "C", "Software", "media", "x", ahora=f("2026-10-25 06:00"))
        # Abierto dentro de SLA: baja
        mesa.crear_ticket(self.conn, "D", "Hardware", "baja", "x", ahora=f("2026-10-26 11:00"))
        self.r = mesa.reporte(self.conn, ahora=f("2026-10-26 12:00"))

    def tearDown(self):
        self.conn.close()

    def test_totales_y_abiertos(self):
        self.assertEqual(self.r["total"], 4)
        self.assertEqual(self.r["abiertos_por_prioridad"],
                         {"critica": 0, "alta": 0, "media": 1, "baja": 1})

    def test_promedio_por_categoria(self):
        self.assertEqual(self.r["promedio_horas_por_categoria"], {"Red": 4.0})

    def test_cumplimiento_sla(self):
        self.assertEqual(self.r["cerrados"], 2)
        self.assertEqual(self.r["cumplimiento_sla"], 50.0)

    def test_vencidos_sin_cerrar(self):
        self.assertEqual(self.r["vencidos_sin_cerrar"], [3])

    def test_reporte_vacio(self):
        conn = mesa.conectar(":memory:")
        r = mesa.reporte(conn, ahora=f("2026-10-26 12:00"))
        self.assertIsNone(r["cumplimiento_sla"])
        self.assertIn("sin datos", mesa.formatear_reporte(r))
        conn.close()

    def test_formato_texto(self):
        texto = mesa.formatear_reporte(self.r)
        self.assertIn("Cumplimiento de SLA: 50.0% de 2 cerrados", texto)
        self.assertIn("#3", texto)


if __name__ == "__main__":
    unittest.main()
