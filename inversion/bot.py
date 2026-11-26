"""Bot de Telegram para consultar la cartera y respetar la estrategia.

Variables de entorno:
  TELEGRAM_TOKEN    token de @BotFather
  TELEGRAM_CHAT_ID  tu chat id (solo tú podrás usar el bot). Si no lo sabes,
                    arranca el bot sin él y escribe /id.
"""
from __future__ import annotations

import html
import logging
import os
from datetime import time

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

import core

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SOLO_YO = filters.Chat(chat_id=int(CHAT_ID)) if CHAT_ID else filters.ALL

AYUDA = """<b>📈 Módulo de inversión</b>

/resumen – valor y reparto actual vs objetivo
/carteras – detalle de posiciones por cartera
/estrategia – mi plan y reglas fijas
/aportar 300 – cómo repartir una aportación
/rebalanceo – ¿toca rebalancear?
/precios – actualizar precios (Yahoo Finance)

<b>Antes de operar fuera del plan</b>
/quiero vender IWDA.AS motivo… – registra la idea y arranca el enfriamiento
/pendientes – ideas en enfriamiento
/ejecutada 3 · /descartada 3 – cerrar una idea
/diario – historial de decisiones
/id – ver tu chat id"""


async def responder(update: Update, texto: str) -> None:
    await update.effective_message.reply_html(texto, disable_web_page_preview=True)


def texto_resumen() -> str:
    est, car = core.cargar_estrategia(), core.cargar_carteras()
    m = est["moneda"]
    desv = core.desviaciones(car, est)
    total = sum(d.valor for d in desv)
    lineas = [f"<b>💼 Patrimonio: {core.eur(total, m)}</b>", ""]
    for d in desv:
        icono = "🔴" if d.fuera_banda else ("🟢" if abs(d.diferencia) < 2 else "🟡")
        lineas.append(
            f"{icono} <b>{core.nombre_clase(d.clase)}</b>\n"
            f"    {d.actual:.1f}% (obj. {d.objetivo:.0f}%, {d.diferencia:+.1f} pp) · "
            f"{core.eur(d.valor, m)}"
        )
    lineas.append("")
    if core.necesita_rebalanceo(car, est):
        lineas.append("⚠️ Hay clases fuera de banda. Mira /rebalanceo.")
    else:
        lineas.append(f"✅ Todo dentro de la banda (±{est['banda_rebalanceo']} pp). No hagas nada.")
    if core.usando_ejemplo():
        lineas.append("\n<i>(Datos de ejemplo: crea carteras.yaml con los tuyos)</i>")
    return "\n".join(lineas)


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await responder(update, AYUDA)


async def cmd_id(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await responder(update, f"Tu chat id es <code>{update.effective_chat.id}</code>")


async def cmd_resumen(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await responder(update, texto_resumen())


async def cmd_carteras(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    est, car = core.cargar_estrategia(), core.cargar_carteras()
    m = est["moneda"]
    out = []
    for c in car["carteras"]:
        filas = core.posiciones({"carteras": [c]})
        out.append(f"<b>🏦 {html.escape(c['nombre'])}</b> – {core.eur(sum(p['valor'] for p in filas), m)}")
        for p in filas:
            out.append(
                f"  • {html.escape(p.get('nombre', p['ticker']))} "
                f"({p['participaciones']} × {p['precio']}) = {core.eur(p['valor'], m)}"
            )
        out.append("")
    await responder(update, "\n".join(out))


async def cmd_estrategia(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    est = core.cargar_estrategia()
    obj = "\n".join(f"  • {core.nombre_clase(c)}: {v}%" for c, v in est["objetivo"].items())
    reglas = "\n".join(f"{i}. {html.escape(r)}" for i, r in enumerate(est["reglas"], 1))
    await responder(
        update,
        f"<b>🧭 {html.escape(est['nombre'])}</b>\n\n<b>Objetivo</b>\n{obj}\n\n"
        f"Banda de rebalanceo: ±{est['banda_rebalanceo']} pp\n"
        f"Aportación: {core.eur(est['aportacion_mensual'], est['moneda'])} el día {est['dia_aportacion']}\n"
        f"Enfriamiento: {est['enfriamiento_horas']} h\n"
        f"Revisión de la estrategia: solo en {est['revision_anual']}\n\n<b>Reglas</b>\n{reglas}",
    )


async def cmd_aportar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    est, car = core.cargar_estrategia(), core.cargar_carteras()
    try:
        importe = float(ctx.args[0].replace(",", ".")) if ctx.args else float(est["aportacion_mensual"])
    except ValueError:
        await responder(update, "Uso: /aportar 300")
        return
    reparto = core.reparto_aportacion(car, est, importe)
    lineas = [f"<b>💶 Reparto de {core.eur(importe, est['moneda'])}</b>", ""]
    lineas += [f"  • {core.nombre_clase(c)}: {core.eur(v, est['moneda'])}" for c, v in reparto.items()]
    lineas.append("\nSe prioriza lo que está por debajo del objetivo (rebalanceo sin vender).")
    await responder(update, "\n".join(lineas))


async def cmd_rebalanceo(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    est, car = core.cargar_estrategia(), core.cargar_carteras()
    if not core.necesita_rebalanceo(car, est):
        await responder(
            update,
            f"✅ Ninguna clase se sale de ±{est['banda_rebalanceo']} pp.\n"
            "<b>La decisión correcta es no hacer nada.</b>",
        )
        return
    movs = core.rebalanceo_completo(car, est)
    lineas = ["<b>⚖️ Toca rebalancear</b>", "",
              "1️⃣ Primero intenta corregirlo con aportaciones (/aportar).",
              "2️⃣ Si no basta, movimientos para volver al objetivo:", ""]
    for c, v in movs.items():
        if abs(v) >= 1:
            accion = "Comprar" if v > 0 else "Vender"
            lineas.append(f"  • {accion} {core.eur(abs(v), est['moneda'])} de {core.nombre_clase(c)}")
    await responder(update, "\n".join(lineas))


async def cmd_precios(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if core.usando_ejemplo():
        await responder(update, "Primero crea carteras.yaml (copia de carteras.example.yaml).")
        return
    await responder(update, "Actualizando precios…")
    log = core.actualizar_precios()
    await responder(update, "\n".join(html.escape(x) for x in log) + "\n\n" + texto_resumen())


async def cmd_quiero(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if len(ctx.args) < 3 or ctx.args[0].lower() not in ("comprar", "vender"):
        await responder(update, "Uso: /quiero vender IWDA.AS porque ...\n(el motivo es obligatorio)")
        return
    est = core.cargar_estrategia()
    op = core.solicitar_operacion(ctx.args[0].lower(), ctx.args[1], " ".join(ctx.args[2:]), est)
    checklist = "\n".join(f"☐ {html.escape(q)}" for q in est["checklist_operacion"])
    await responder(
        update,
        f"📝 <b>Idea #{op['id']} registrada</b>: {op['tipo']} {html.escape(op['ticker'])}\n"
        f"Motivo: <i>{html.escape(op['motivo'])}</i>\n\n"
        f"⏳ Enfriamiento hasta <b>{op['desbloqueo'].replace('T', ' ')}</b>.\n"
        f"Te lo recordaré entonces. Mientras, responde con calma:\n\n{checklist}\n\n"
        f"Cuando pase el plazo: /ejecutada {op['id']} o /descartada {op['id']}",
    )


async def cmd_pendientes(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    ops = core.diario(solo_pendientes=True)
    if not ops:
        await responder(update, "No tienes ideas en enfriamiento. 🧘")
        return
    await responder(update, "\n".join(
        f"#{o['id']} {o['tipo']} {html.escape(o['ticker'])} – hasta {o['desbloqueo'].replace('T', ' ')}\n"
        f"   <i>{html.escape(o['motivo'])}</i>" for o in ops))


async def _resolver(update: Update, ctx: ContextTypes.DEFAULT_TYPE, estado: str) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await responder(update, f"Uso: /{estado} 3")
        return
    _, msg = core.resolver_operacion(int(ctx.args[0]), estado)
    await responder(update, html.escape(msg))


async def cmd_ejecutada(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _resolver(update, ctx, "ejecutada")


async def cmd_descartada(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _resolver(update, ctx, "descartada")


async def cmd_diario(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    ops = core.diario()[-15:]
    if not ops:
        await responder(update, "Diario vacío.")
        return
    desc = sum(o["estado"] == "descartada" for o in core.diario())
    await responder(update, "\n".join(
        f"#{o['id']} {o['creada'][:10]} {o['tipo']} {html.escape(o['ticker'])} → <b>{o['estado']}</b>"
        for o in ops) + f"\n\n🛡️ Impulsos frenados en total: {desc}")


# ---------------------------------------------------------------- tareas diarias
async def tarea_diaria(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not CHAT_ID:
        return
    from datetime import datetime

    est, car = core.cargar_estrategia(), core.cargar_carteras()
    hoy = datetime.now()
    if hoy.day == est["dia_aportacion"]:
        reparto = core.reparto_aportacion(car, est, float(est["aportacion_mensual"]))
        txt = "\n".join(f"  • {core.nombre_clase(c)}: {core.eur(v, est['moneda'])}" for c, v in reparto.items())
        await ctx.bot.send_message(CHAT_ID, f"📅 Hoy toca aportar. Reparto sugerido:\n{txt}")
    if core.necesita_rebalanceo(car, est):
        await ctx.bot.send_message(CHAT_ID, "⚠️ Alguna clase está fuera de banda. Escribe /rebalanceo.")
    for o in core.diario(solo_pendientes=True):
        if datetime.fromisoformat(o["desbloqueo"]) <= hoy:
            await ctx.bot.send_message(
                CHAT_ID,
                f"⏰ Terminó el enfriamiento de la idea #{o['id']} ({o['tipo']} {o['ticker']}).\n"
                f"Motivo: {o['motivo']}\n¿Sigue teniendo sentido? /ejecutada {o['id']} o /descartada {o['id']}",
            )


def main() -> None:
    if not TOKEN:
        raise SystemExit("Falta TELEGRAM_TOKEN (créalo con @BotFather)")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("id", cmd_id))  # accesible siempre para averiguar el id
    for nombre, fn in {
        "start": cmd_start, "ayuda": cmd_start, "help": cmd_start,
        "resumen": cmd_resumen, "carteras": cmd_carteras, "estrategia": cmd_estrategia,
        "aportar": cmd_aportar, "rebalanceo": cmd_rebalanceo, "precios": cmd_precios,
        "quiero": cmd_quiero, "pendientes": cmd_pendientes, "ejecutada": cmd_ejecutada,
        "descartada": cmd_descartada, "diario": cmd_diario,
    }.items():
        app.add_handler(CommandHandler(nombre, fn, filters=SOLO_YO))
    app.job_queue.run_daily(tarea_diaria, time=time(hour=9, minute=0))
    logging.info("Bot en marcha")
    app.run_polling()


if __name__ == "__main__":
    main()
