"""Lógica del módulo de inversión: valoración, desviaciones, aportaciones,
rebalanceo y diario de operaciones con periodo de enfriamiento.

Sin dependencias de Telegram ni Streamlit: lo usan bot.py y app.py.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent
RUTA_ESTRATEGIA = Path(os.getenv("INV_ESTRATEGIA", BASE / "estrategia.yaml"))
RUTA_CARTERAS = Path(os.getenv("INV_CARTERAS", BASE / "carteras.yaml"))
RUTA_EJEMPLO = BASE / "carteras.example.yaml"
RUTA_DIARIO = Path(os.getenv("INV_DIARIO", BASE / "diario.json"))


# ---------------------------------------------------------------- carga
def cargar_estrategia() -> dict:
    est = yaml.safe_load(RUTA_ESTRATEGIA.read_text(encoding="utf-8"))
    total = sum(est["objetivo"].values())
    if abs(total - 100) > 0.01:
        raise ValueError(f"El objetivo de estrategia.yaml suma {total}, debe sumar 100")
    return est


def cargar_carteras() -> dict:
    ruta = RUTA_CARTERAS if RUTA_CARTERAS.exists() else RUTA_EJEMPLO
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def guardar_carteras(data: dict) -> None:
    RUTA_CARTERAS.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def usando_ejemplo() -> bool:
    return not RUTA_CARTERAS.exists()


# ---------------------------------------------------------------- valoración
def posiciones(carteras: dict) -> list[dict]:
    filas = []
    for c in carteras.get("carteras", []):
        for p in c.get("posiciones", []):
            valor = float(p["participaciones"]) * float(p["precio"])
            filas.append({**p, "cartera": c["nombre"], "valor": valor})
    return filas


def valor_por_clase(carteras: dict, estrategia: dict) -> dict[str, float]:
    totales = {clase: 0.0 for clase in estrategia["objetivo"]}
    for p in posiciones(carteras):
        if p["clase"] not in totales:
            raise ValueError(
                f"La posición {p['ticker']} tiene clase '{p['clase']}', "
                f"que no existe en estrategia.yaml"
            )
        totales[p["clase"]] += p["valor"]
    return totales


@dataclass
class Desviacion:
    clase: str
    valor: float
    actual: float      # % actual
    objetivo: float    # % objetivo
    diferencia: float  # puntos (actual - objetivo)
    fuera_banda: bool


def desviaciones(carteras: dict, estrategia: dict) -> list[Desviacion]:
    totales = valor_por_clase(carteras, estrategia)
    total = sum(totales.values()) or 1.0
    banda = estrategia["banda_rebalanceo"]
    res = []
    for clase, obj in estrategia["objetivo"].items():
        actual = totales[clase] / total * 100
        dif = actual - obj
        res.append(Desviacion(clase, totales[clase], actual, obj, dif, abs(dif) > banda))
    return res


# ---------------------------------------------------------------- decisiones
def reparto_aportacion(carteras: dict, estrategia: dict, importe: float) -> dict[str, float]:
    """Reparte dinero nuevo hacia las clases infraponderadas (rebalanceo sin vender)."""
    totales = valor_por_clase(carteras, estrategia)
    nuevo_total = sum(totales.values()) + importe
    deficit = {
        c: max(0.0, estrategia["objetivo"][c] / 100 * nuevo_total - v)
        for c, v in totales.items()
    }
    suma = sum(deficit.values())
    if suma <= 0:  # todo equilibrado: reparto según objetivo
        return {c: importe * o / 100 for c, o in estrategia["objetivo"].items()}
    return {c: importe * d / suma for c, d in deficit.items() if d > 0}


def rebalanceo_completo(carteras: dict, estrategia: dict) -> dict[str, float]:
    """Compras (+) y ventas (-) por clase para volver exactamente al objetivo."""
    totales = valor_por_clase(carteras, estrategia)
    total = sum(totales.values())
    return {c: estrategia["objetivo"][c] / 100 * total - v for c, v in totales.items()}


def necesita_rebalanceo(carteras: dict, estrategia: dict) -> bool:
    return any(d.fuera_banda for d in desviaciones(carteras, estrategia))


# ---------------------------------------------------------------- precios
def actualizar_precios() -> list[str]:
    """Actualiza precios con Yahoo Finance (gratis). Devuelve log de cambios."""
    import yfinance as yf

    data = cargar_carteras()
    log = []
    for c in data["carteras"]:
        for p in c["posiciones"]:
            if p["ticker"].upper() == "CASH":
                continue
            try:
                hist = yf.Ticker(p["ticker"]).history(period="5d")
                nuevo = round(float(hist["Close"].dropna().iloc[-1]), 4)
                log.append(f"{p['ticker']}: {p['precio']} → {nuevo}")
                p["precio"] = nuevo
            except Exception as e:  # noqa: BLE001
                log.append(f"{p['ticker']}: sin precio ({e.__class__.__name__})")
    guardar_carteras(data)
    return log


# ---------------------------------------------------------------- diario
def _leer_diario() -> list[dict]:
    if RUTA_DIARIO.exists():
        return json.loads(RUTA_DIARIO.read_text(encoding="utf-8"))
    return []


def _guardar_diario(d: list[dict]) -> None:
    RUTA_DIARIO.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def solicitar_operacion(tipo: str, ticker: str, motivo: str, estrategia: dict) -> dict:
    """Registra una intención de operar. No se puede confirmar hasta pasar el enfriamiento."""
    diario = _leer_diario()
    ahora = datetime.now()
    op = {
        "id": max((o["id"] for o in diario), default=0) + 1,
        "tipo": tipo,
        "ticker": ticker.upper(),
        "motivo": motivo,
        "creada": ahora.isoformat(timespec="minutes"),
        "desbloqueo": (ahora + timedelta(hours=estrategia["enfriamiento_horas"])).isoformat(
            timespec="minutes"
        ),
        "estado": "enfriando",
    }
    diario.append(op)
    _guardar_diario(diario)
    return op


def resolver_operacion(op_id: int, estado: str) -> tuple[bool, str]:
    """estado: 'ejecutada' o 'descartada'. Ejecutar solo tras el enfriamiento."""
    diario = _leer_diario()
    for op in diario:
        if op["id"] != op_id:
            continue
        if op["estado"] != "enfriando":
            return False, f"La operación #{op_id} ya está {op['estado']}."
        if estado == "ejecutada" and datetime.now() < datetime.fromisoformat(op["desbloqueo"]):
            return False, (
                f"⏳ Aún en enfriamiento hasta {op['desbloqueo'].replace('T', ' ')}. "
                "Si sigue teniendo sentido entonces, adelante."
            )
        op["estado"] = estado
        op["resuelta"] = datetime.now().isoformat(timespec="minutes")
        _guardar_diario(diario)
        return True, f"Operación #{op_id} marcada como {estado}."
    return False, f"No existe la operación #{op_id}."


def diario(solo_pendientes: bool = False) -> list[dict]:
    d = _leer_diario()
    return [o for o in d if o["estado"] == "enfriando"] if solo_pendientes else d


# ---------------------------------------------------------------- texto
def eur(x: float, moneda: str = "EUR") -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {'€' if moneda == 'EUR' else moneda}"


def nombre_clase(c: str) -> str:
    return c.replace("_", " ").capitalize()
