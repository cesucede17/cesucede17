"""Handlers de Telegram del módulo de gastos (los registra bot.py)."""
from __future__ import annotations

import html
import os
from datetime import date

from telegram import (InlineKeyboardButton as Btn, InlineKeyboardMarkup, ReplyKeyboardMarkup,
                      Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import core
import gastos as g

MENU_GASTO, MENU_MES, MENU_BALANCE, MENU_INVERSION = "➕ Gasto", "📊 Mes", "⚖️ Balance", "💼 Inversión"
MENU = ReplyKeyboardMarkup([[MENU_GASTO, MENU_MES], [MENU_BALANCE, MENU_INVERSION]],
                           resize_keyboard=True, is_persistent=True)
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def eur(x: float) -> str:
    return core.eur(x, "EUR")


def _autorizado(update: Update) -> bool:
    return not CHAT_ID or str(update.effective_chat.id) == CHAT_ID


# ---------------------------------------------------------------- teclados
def teclado_categorias(mov_id: int) -> InlineKeyboardMarkup:
    botones = [Btn(f"{c['emoji']} {c['nombre']}", callback_data=f"cat:{mov_id}:{k}")
               for k, c in g.categorias().items()]
    filas = [botones[i:i + 3] for i in range(0, len(botones), 3)]
    filas.append([Btn("❌ Cancelar", callback_data=f"del:{mov_id}")])
    return InlineKeyboardMarkup(filas)


def teclado_guardado(mov_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        Btn("🏦 Cambiar banco", callback_data=f"ban:{mov_id}"),
        Btn("🏷️ Categoría", callback_data=f"rec:{mov_id}"),
        Btn("↩️ Deshacer", callback_data=f"del:{mov_id}"),
    ]])


def teclado_bancos(mov_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        Btn(f"{b['emoji']} {b['nombre']}", callback_data=f"setb:{mov_id}:{k}")
        for k, b in g.finanzas()["bancos"].items()
    ]])


def texto_movimiento(m: dict) -> str:
    banco = g.finanzas()["bancos"].get(m["banco"], {}).get("nombre", m["banco"])
    nota = f" · <i>{html.escape(m['nota'])}</i>" if m["nota"] else ""
    tipo = " (aportación, no cuenta como gasto)" if m["tipo"] == "aportacion" else ""
    return f"✅ <b>{eur(m['importe'])}</b> · {g.etiqueta(m['categoria'])}{tipo}{nota}\n🏦 {banco}"


# ---------------------------------------------------------------- informes
def texto_mes(mes: str) -> str:
    t = g.totales_mes(mes)
    media = g.media_categorias(mes)
    cats = g.categorias()
    lineas = [f"<b>📊 {mes}</b>", ""]
    if not t["por_categoria"]:
        lineas.append("Sin gastos registrados este mes.")
    for c, v in sorted(t["por_categoria"].items(), key=lambda x: -x[1]):
        pct = v / t["gastos"] * 100
        extra = []
        if media.get(c):
            extra.append(f"{(v / media[c] - 1) * 100:+.0f}% vs media")
        pres = cats.get(c, {}).get("presupuesto") or 0
        if pres:
            extra.append(f"{v / pres * 100:.0f}% del presupuesto")
        lineas.append(f"{g.etiqueta(c)}: <b>{eur(v)}</b> ({pct:.0f}%)"
                      + (f"\n      <i>{' · '.join(extra)}</i>" if extra else ""))
    lineas += ["", f"💸 Gastos: <b>{eur(t['gastos'])}</b>",
               f"💰 Ingresos: {eur(t['ingresos'])}",
               f"📈 Invertido: {eur(t['aportaciones'])}"]
    if t["tasa_ahorro"] is not None:
        lineas.append(f"🐷 Ahorro: {eur(t['ahorro'])} ({t['tasa_ahorro']:.0f}% de tus ingresos)")
    return "\n".join(lineas)


def texto_balance() -> str:
    mes = g.mes_actual()
    t = g.totales_mes(mes)
    est, car = core.cargar_estrategia(), core.cargar_carteras()
    liquidez = core.valor_por_clase(car, est).get("liquidez", 0.0)
    media = g.media_categorias(mes)
    gasto_medio = sum(media.values())
    objetivo = est.get("fondo_emergencia_meses", 6)
    plan = float(est["aportacion_mensual"])

    lineas = [f"<b>⚖️ Balance de {mes}</b>", "",
              f"💰 Ingresos: {eur(t['ingresos'])}",
              f"💸 Gastos: {eur(t['gastos'])}",
              f"📈 Invertido: {eur(t['aportaciones'])} de {eur(plan)} del plan",
              f"🟰 Sin asignar: <b>{eur(t['sin_asignar'])}</b>", ""]
    fondo_ok = None
    if gasto_medio > 0:
        meses = liquidez / gasto_medio
        fondo_ok = meses >= objetivo
        lineas.append(f"{'✅' if fondo_ok else '⚠️'} Fondo de emergencia: {eur(liquidez)} = "
                      f"<b>{meses:.1f} meses</b> de gastos (objetivo {objetivo})")
        if not fondo_ok:
            lineas.append(f"   → Faltan {eur(objetivo * gasto_medio - liquidez)}. "
                          "El excedente va primero a liquidez.")
    else:
        lineas.append("ℹ️ El fondo de emergencia se calculará cuando haya un mes completo de gastos.")

    falta_plan = plan - t["aportaciones"]
    if falta_plan > 0 and fondo_ok is not False:
        lineas.append(f"📅 Pendiente la aportación del plan: {eur(falta_plan)} → /aportar {falta_plan:.0f}")
    elif falta_plan <= 0:
        lineas.append("✅ Aportación del mes hecha. Lo que sobre, a liquidez: "
                      "invertir más de lo planificado se decide en la revisión anual.")
    if core.usando_ejemplo():
        lineas.append("\n<i>(La liquidez sale de carteras de ejemplo)</i>")
    return "\n".join(lineas)


# ---------------------------------------------------------------- handlers
async def on_texto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    texto = update.effective_message.text
    if texto == MENU_GASTO:
        await update.effective_message.reply_html(
            "Escribe el importe y, si quieres, una nota.\nEj.: <code>12,50 menú del día</code>",
            reply_markup=MENU)
        return
    if texto == MENU_MES:
        await update.effective_message.reply_html(texto_mes(g.mes_actual()), reply_markup=MENU)
        return
    if texto == MENU_BALANCE:
        await update.effective_message.reply_html(texto_balance(), reply_markup=MENU)
        return
    if texto == MENU_INVERSION:
        await update.effective_message.reply_html(ctx.bot_data["texto_inversion"](), reply_markup=MENU)
        return

    parsed = g.parsear(texto)
    if not parsed:
        await update.effective_message.reply_html(
            "No he entendido. Para apuntar un gasto escribe p. ej. <code>12,50 súper</code>. "
            "Ayuda: /start", reply_markup=MENU)
        return
    importe, nota = parsed
    mov_id = g.registrar(importe, "pendiente", nota=nota)
    await update.effective_message.reply_html(
        f"<b>{eur(importe)}</b>{' · ' + html.escape(nota) if nota else ''}\n¿Categoría?",
        reply_markup=teclado_categorias(mov_id))


async def on_boton(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _autorizado(update):
        await q.answer("No autorizado")
        return
    accion, mov_id, *resto = q.data.split(":")
    mov_id = int(mov_id)
    if not g.obtener(mov_id):
        await q.answer("Ese apunte ya no existe")
        await q.edit_message_reply_markup(None)
        return
    if accion == "cat":
        m = g.clasificar(mov_id, resto[0])
        await q.edit_message_text(texto_movimiento(m), parse_mode="HTML",
                                  reply_markup=teclado_guardado(mov_id))
        await _aviso_presupuesto(q, m)
    elif accion == "rec":
        await q.edit_message_reply_markup(teclado_categorias(mov_id))
    elif accion == "ban":
        await q.edit_message_reply_markup(teclado_bancos(mov_id))
    elif accion == "setb":
        m = g.cambiar_banco(mov_id, resto[0])
        await q.edit_message_text(texto_movimiento(m), parse_mode="HTML",
                                  reply_markup=teclado_guardado(mov_id))
    elif accion == "del":
        g.borrar(mov_id)
        await q.edit_message_text("🗑️ Borrado.")
    await q.answer()


async def _aviso_presupuesto(q, m: dict) -> None:
    if m["tipo"] != "gasto":
        return
    pres = g.categorias().get(m["categoria"], {}).get("presupuesto") or 0
    if not pres:
        return
    gastado = g.totales_mes(m["fecha"][:7])["por_categoria"].get(m["categoria"], 0)
    antes = gastado - m["importe"]
    for umbral, msg in ((1.0, "🔴 Has superado"), (0.8, "🟡 Llevas más del 80% de")):
        if antes < umbral * pres <= gastado:
            await q.message.reply_html(
                f"{msg} el presupuesto de {g.etiqueta(m['categoria'])}: {eur(gastado)} de {eur(pres)}")
            return


async def cmd_ingreso(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    parsed = g.parsear(" ".join(ctx.args)) if ctx.args else None
    if not parsed:
        await update.effective_message.reply_html("Uso: <code>/ingreso 1800 nómina</code>")
        return
    importe, nota = parsed
    mov_id = g.registrar(importe, "ingreso", nota=nota or "Ingreso")
    await update.effective_message.reply_html(
        f"💰 Ingreso de <b>{eur(importe)}</b> apuntado.",
        reply_markup=InlineKeyboardMarkup([[Btn("🏦 Cambiar banco", callback_data=f"ban:{mov_id}"),
                                            Btn("↩️ Deshacer", callback_data=f"del:{mov_id}")]]))


async def cmd_mes(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    mes = ctx.args[0] if ctx.args else g.mes_actual()
    await update.effective_message.reply_html(texto_mes(mes), reply_markup=MENU)


async def cmd_balance(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(texto_balance(), reply_markup=MENU)


async def cmd_ultimos(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    movs = g.ultimos(15)
    if not movs:
        await update.effective_message.reply_html("Aún no hay movimientos.")
        return
    signo = {"ingreso": "+", "gasto": "−", "aportacion": "→"}
    await update.effective_message.reply_html("\n".join(
        f"<code>#{m['id']}</code> {m['fecha'][5:]} {signo[m['tipo']]}{eur(m['importe'])} "
        f"{g.etiqueta(m['categoria']) if m['categoria'] else '💰'} {html.escape(m['nota'] or '')}"
        for m in movs) + "\n\nPara borrar uno: /borrar N")


async def cmd_borrar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await update.effective_message.reply_html("Uso: /borrar 12  (el número sale en /ultimos)")
        return
    ok = g.borrar(int(ctx.args[0]))
    await update.effective_message.reply_html("🗑️ Borrado." if ok else "No existe ese movimiento.")


async def tarea_fijos(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    g.limpiar_pendientes()
    hechos = g.aplicar_fijos()
    if hechos and CHAT_ID:
        await ctx.bot.send_message(CHAT_ID, "🔁 Apuntados automáticamente:\n" + "\n".join(
            f"  • {f['concepto']}: {eur(float(f['importe']))}" for f in hechos))


def registrar_handlers(app: Application, solo_yo, texto_inversion) -> None:
    app.bot_data["texto_inversion"] = texto_inversion
    for nombre, fn in {"ingreso": cmd_ingreso, "mes": cmd_mes, "balance": cmd_balance,
                       "ultimos": cmd_ultimos, "borrar": cmd_borrar}.items():
        app.add_handler(CommandHandler(nombre, fn, filters=solo_yo))
    app.add_handler(MessageHandler(solo_yo & filters.TEXT & ~filters.COMMAND, on_texto))
    app.add_handler(CallbackQueryHandler(on_boton, pattern=r"^(cat|rec|ban|setb|del):"))
