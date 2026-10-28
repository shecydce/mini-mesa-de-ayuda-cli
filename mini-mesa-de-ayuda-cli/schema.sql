CREATE TABLE IF NOT EXISTS tickets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo       TEXT NOT NULL,
    descripcion  TEXT NOT NULL DEFAULT '',
    categoria    TEXT NOT NULL,
    prioridad    TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'abierto',   -- abierto, en_curso, cerrado
    solicitante  TEXT NOT NULL,
    tecnico      TEXT,
    creado       TEXT NOT NULL,                     -- AAAA-MM-DD HH:MM
    cerrado      TEXT,
    solucion     TEXT
);
