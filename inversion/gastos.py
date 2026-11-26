"""Módulo de gastos: movimientos en SQLite, categorías, ingresos/gastos fijos e informes.

Tipos de movimiento:
  gasto      – sale dinero y cuenta como gasto
  ingreso    – entra dinero (nómina, etc.)
  aportacion – sale dinero hacia inversión: NO es gasto, es ahorro
"""
from __future__ import annotations

import calendar
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent
RUTA_DB = Path(os.getenv("INV_DB", BASE / "finanzas.db"))
RUTA_CATEGORIAS = BASE / "categorias.yaml"
RUTA_FINANZAS = Path(os.getenv("INV_FINANZAS", BASE / "finanzas.yaml"))
RUTA_FINANZAS_EJEMPLO = BASE / "finanzas.example.yaml"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS movimientos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha     TEXT NOT NULL,              -- YYYY-MM-DD
    importe   REAL NOT NULL CHECK (importe > 0),
    tipo      TEXT NOT NULL,              -- gasto | ingreso | aportacion | pendiente
    categoria TEXT,
    nota      TEXT DEFAULT '',
    banco     TEXT,
    origen    TEXT DEFAULT 'manual',      -- manual | fijo | ticket | captura
    creado    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos(fecha);
"""


# ---------------------------------------------------------------- config
def categorias() -> dict:
    return yaml.safe_load(RUTA_CATEGORIAS.read_text(encoding="utf-8"))["categorias"]


def finanzas() -> dict:
    ruta = RUTA_FINANZAS if RUTA_FINANZAS.exists() else RUTA_FINANZAS_EJEMPLO
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def etiqueta(cat: str) -> str:
    c = categorias().get(cat)
    return f"{c['emoji']} {c['nombre']}" if c else cat


def tipo_de_categoria(cat: str) -> str:
    return "aportacion" if categorias()[cat].get("tipo") == "aportacion" else "gasto"


# ---------------------------------------------------------------- db
@contextmanager
def conexion():
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def registrar(importe: float, tipo: str, categoria: str | None = None, nota: str = "",
              banco: str | None = None, fecha: date | None = None, origen: str = "manual") -> int:
    with conexion() as con:
        cur = con.execute(
            "INSERT INTO movimientos (fecha, importe, tipo, categoria, nota, banco, origen, creado)"
            " VALUES (?,?,?,?,?,?,?,?)",
            ((fecha or date.today()).isoformat(), round(importe, 2), tipo, categoria, nota,
             banco or finanzas()["banco_por_defecto"], origen, _ahora()),
        )
        return cur.lastrowid


def obtener(mov_id: int) -> dict | None:
    with conexion() as con:
        r = con.execute("SELECT * FROM movimientos WHERE id=?", (mov_id,)).fetchone()
        return dict(r) if r else None


def clasificar(mov_id: int, categoria: str) -> dict | None:
    """Asigna categoría a un movimiento pendiente (o la cambia)."""
    with conexion() as con:
        con.execute("UPDATE movimientos SET categoria=?, tipo=? WHERE id=?",
                    (categoria, tipo_de_categoria(categoria), mov_id))
    return obtener(mov_id)


def cambiar_banco(mov_id: int, banco: str) -> dict | None:
    with conexion() as con:
        con.execute("UPDATE movimientos SET banco=? WHERE id=?", (banco, mov_id))
    return obtener(mov_id)


def borrar(mov_id: int) -> bool:
    with conexion() as con:
        return con.execute("DELETE FROM movimientos WHERE id=?", (mov_id,)).rowcount > 0


def limpiar_pendientes(horas: int = 24) -> int:
    """Borra apuntes rápidos que nunca se clasificaron."""
    with conexion() as con:
        return con.execute(
            "DELETE FROM movimientos WHERE tipo='pendiente' AND creado < datetime('now','localtime',?)",
            (f"-{horas} hours",),
        ).rowcount


def ultimos(n: int = 10) -> list[dict]:
    with conexion() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM movimientos WHERE tipo!='pendiente' ORDER BY fecha DESC, id DESC LIMIT ?", (n,))]


# ---------------------------------------------------------------- entrada de texto
PATRON_IMPORTE = re.compile(r"^\s*(\d[\d.,]*)\s*€?(?:\s+(.*))?$", re.S)


def _a_numero(t: str) -> float | None:
    """Acepta 12 · 12,5 · 12.50 · 1.234 · 1.234,56 · 1,234.56"""
    if "," in t and "." in t:  # el último separador es el decimal
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def parsear(texto: str) -> tuple[float, str] | None:
    """'12,50 menú del día' -> (12.5, 'menú del día')."""
    m = PATRON_IMPORTE.match(texto)
    if not m:
        return None
    importe = _a_numero(m.group(1))
    if not importe or importe <= 0 or importe >= 1e7:
        return None
    return round(importe, 2), (m.group(2) or "").strip()


# ---------------------------------------------------------------- fijos
def _dia_efectivo(dia: int, hoy: date) -> int:
    return min(dia, calendar.monthrange(hoy.year, hoy.month)[1])


def aplicar_fijos(hoy: date | None = None) -> list[dict]:
    """Apunta los ingresos/gastos fijos que tocan hoy y aún no están este mes."""
    hoy = hoy or date.today()
    fin = finanzas()
    candidatos = (
        [{**i, "tipo": "ingreso", "categoria": None} for i in fin.get("ingresos_fijos", [])]
        + [{**g, "tipo": tipo_de_categoria(g["categoria"])} for g in fin.get("gastos_fijos", [])]
    )
    hechos = []
    mes = hoy.strftime("%Y-%m")
    with conexion() as con:
        for f in candidatos:
            if _dia_efectivo(int(f["dia"]), hoy) > hoy.day or not f.get("importe"):
                continue
            ya = con.execute(
                "SELECT 1 FROM movimientos WHERE origen='fijo' AND nota=? AND substr(fecha,1,7)=?",
                (f["concepto"], mes)).fetchone()
            if ya:
                continue
            con.execute(
                "INSERT INTO movimientos (fecha, importe, tipo, categoria, nota, banco, origen, creado)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (hoy.isoformat(), float(f["importe"]), f["tipo"], f["categoria"], f["concepto"],
                 f.get("banco", fin["banco_por_defecto"]), "fijo", _ahora()))
            hechos.append(f)
    return hechos


# ---------------------------------------------------------------- informes
def _mes_anterior(mes: str, n: int) -> str:
    y, m = map(int, mes.split("-"))
    m -= n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def totales_mes(mes: str) -> dict:
    """mes = 'YYYY-MM'. Devuelve ingresos, gastos, aportaciones y gasto por categoría."""
    with conexion() as con:
        filas = con.execute(
            "SELECT tipo, categoria, SUM(importe) s FROM movimientos "
            "WHERE substr(fecha,1,7)=? AND tipo!='pendiente' GROUP BY tipo, categoria", (mes,)).fetchall()
    res = {"ingresos": 0.0, "gastos": 0.0, "aportaciones": 0.0, "por_categoria": {}}
    for f in filas:
        if f["tipo"] == "ingreso":
            res["ingresos"] += f["s"]
        elif f["tipo"] == "aportacion":
            res["aportaciones"] += f["s"]
        elif f["tipo"] == "gasto":
            res["gastos"] += f["s"]
            res["por_categoria"][f["categoria"] or "otros"] = (
                res["por_categoria"].get(f["categoria"] or "otros", 0) + f["s"])
    res["ahorro"] = res["ingresos"] - res["gastos"]
    res["tasa_ahorro"] = res["ahorro"] / res["ingresos"] * 100 if res["ingresos"] else None
    res["sin_asignar"] = res["ahorro"] - res["aportaciones"]
    return res


def media_categorias(mes: str, meses: int = 3) -> dict[str, float]:
    """Media mensual por categoría de los `meses` anteriores a `mes` (solo meses con datos)."""
    acumulado: dict[str, float] = {}
    con_datos = 0
    for i in range(1, meses + 1):
        t = totales_mes(_mes_anterior(mes, i))
        if t["gastos"] or t["ingresos"]:
            con_datos += 1
            for c, v in t["por_categoria"].items():
                acumulado[c] = acumulado.get(c, 0) + v
    return {c: v / con_datos for c, v in acumulado.items()} if con_datos else {}


def mes_actual() -> str:
    return date.today().strftime("%Y-%m")
