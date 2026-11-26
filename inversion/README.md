# 📈 Módulo de inversión: carteras + estrategia fija

Todo es gratuito. El objetivo es tener **todas las carteras en un sitio** y una **estrategia escrita que decide por ti**, para no tomar decisiones precipitadas.

| Archivo | Para qué sirve |
|---|---|
| `estrategia.yaml` | Tu plan: reparto objetivo, banda de rebalanceo, aportación mensual, reglas y periodo de enfriamiento. Solo se cambia una vez al año. |
| `carteras.yaml` | Tus posiciones. Es privado: está en `.gitignore`. Se crea copiando `carteras.example.yaml`. |
| `core.py` | Los cálculos: valoración, desviaciones, reparto de aportaciones, rebalanceo y diario. |
| `bot.py` | Bot de Telegram. |
| `app.py` | Panel web con Streamlit. |

## Cómo te protege de las decisiones precipitadas

1. **Banda de rebalanceo (±5 pp):** si nada se sale de la banda, el bot te dice *"La decisión correcta es no hacer nada"*.
2. **Rebalanceo con aportaciones:** `/aportar` mete el dinero nuevo en lo que está por debajo del objetivo, así no hace falta vender.
3. **Enfriamiento obligatorio:** cualquier operación fuera del plan se registra con `/quiero vender X motivo…`. No se puede marcar como ejecutada hasta que pasen 72 h. Mientras tanto recibes un checklist, y al terminar el plazo el bot te pregunta si sigue teniendo sentido.
4. **Diario de decisiones:** cuenta cuántos impulsos has frenado.
5. **Recordatorio mensual:** el día de aportación te llega el reparto sugerido.

## Puesta en marcha (5 minutos)

```bash
cd inversion
pip install -r requirements.txt
cp carteras.example.yaml carteras.yaml   # y edítalo con tus datos
```

### Panel web
```bash
streamlit run app.py      # abre http://localhost:8501
```

### Bot de Telegram
1. En Telegram, habla con **@BotFather** → `/newbot` → copia el token.
2. Arranca el bot y escríbele `/id` para ver tu chat id:
   ```bash
   export TELEGRAM_TOKEN="123456:ABC..."
   python bot.py
   ```
3. Páralo y vuelve a arrancarlo con tu id, para que **solo tú** puedas usarlo:
   ```bash
   export TELEGRAM_CHAT_ID="tu_id"
   python bot.py
   ```

Comandos: `/resumen`, `/carteras`, `/estrategia`, `/aportar 300`, `/rebalanceo`, `/precios`, `/quiero vender IWDA.AS motivo`, `/pendientes`, `/ejecutada N`, `/descartada N`, `/diario`.

Para actualizar tus posiciones, edita `carteras.yaml` después de cada compra. Los precios se actualizan solos con `/precios`, que usa Yahoo Finance de forma gratuita.

## Dónde tenerlo funcionando gratis

| Opción | Panel | Bot 24/7 | Notas |
|---|---|---|---|
| Tu PC o una Raspberry Pi | ✅ | ✅ si queda encendido | Lo más sencillo y privado. |
| Oracle Cloud *Always Free* (VM) | ✅ | ✅ | Gratis de forma permanente. Usa `systemd` o `tmux` para que el bot siga corriendo. |
| Streamlit Community Cloud | ✅ | ❌ | Despliega `app.py` desde un repo **privado**. |

> ⚠️ **Privacidad:** no subas `carteras.yaml` ni `diario.json` a un repositorio público. Si quieres el panel en la nube, mueve esta carpeta a un repo privado.

## Alternativas de código abierto, si en el futuro quieres más

- [Ghostfolio](https://github.com/ghostfolio/ghostfolio): tracker web autoalojado (Docker), muy completo.
- [Wealthfolio](https://github.com/afadil/wealthfolio): app de escritorio, local y privada.
- [Portfolio Performance](https://github.com/portfolio-performance/portfolio): rentabilidades detalladas (TWR, IRR) en escritorio.

Ninguna incluye las reglas anti-impulso de este módulo. Puedes usar una de ellas para la contabilidad detallada y este bot como "guardián" de la estrategia.
