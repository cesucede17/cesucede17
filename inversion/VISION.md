# Visión: asistente de finanzas personales (Telegram + Raspberry Pi)

> Prompt de especificación. Es el documento de referencia para construir y ajustar el sistema.
> Las decisiones abiertas están al final.

---

## Prompt

Construye un **asistente de finanzas personales** que funcione 24/7 en una **Raspberry Pi**.
Es gratuito, privado (los datos se quedan en local) y lo uso desde **un único bot de Telegram**, con un **panel web** en mi red local para ver más detalle.

El sistema tiene **dos módulos conectados por un balance común**:

```
 ┌──────────────┐     balance mensual      ┌──────────────────┐
 │  1. GASTOS   │ ───────────────────────▶ │  2. INVERSIÓN    │
 │ día a día    │  ingresos − gastos =     │ carteras +       │
 │ (rápido)     │  capacidad de ahorro     │ estrategia fija  │
 └──────────────┘                          └──────────────────┘
```

### Principios
1. **Registrar un gasto debe costar menos de 5 segundos.** Escribo el importe y elijo la categoría con un botón.
2. **El bot me ayuda a decidir con datos, no con impulsos.** Me dice en qué gasto, cuánto puedo recortar y cuánto puedo invertir sin romper mi estrategia.
3. **Mis datos son solo míos.** Se guardan en SQLite en la Raspberry, solo responde a mi chat id y el repositorio es privado.

---

### Módulo 1: Gastos

**Registro rápido con botones**
- Escribo `12,50` o `12,50 menú del día`. El bot responde con **botones de categoría** y al pulsar uno queda guardado, con un botón **↩️ Deshacer**.
- Las categorías se configuran en un archivo. Cada una lleva un emoji, un tipo (**fijo** o **variable**) y una naturaleza (**esencial** o **prescindible**):

| Categoría | Tipo | Naturaleza |
|---|---|---|
| 🛒 Comida – supermercado | variable | esencial |
| 🍽️ Comida – fuera | variable | prescindible |
| 🏋️ Gimnasio | fijo | prescindible |
| 🎉 Ocio | variable | prescindible |
| 📶 Wifi / móvil | fijo | esencial |
| 💊 Medicación | variable | esencial |
| 💆 Autocuidado | variable | prescindible |
| 🏠 Vivienda | fijo | esencial |
| 🚌 Transporte | variable | esencial |
| 📺 Suscripciones | fijo | prescindible |
| 📈 Inversiones | — | *no cuenta como gasto: es ahorro* |
| ❓ Otros | variable | prescindible |

- **Ingresos:** `/ingreso 1800 nómina`.
- **Gastos fijos recurrentes** (wifi, gimnasio, suscripciones…): se dan de alta una vez y se anotan solos cada mes.
- **Presupuesto mensual por categoría**, con avisos al llegar al 80 % y al 100 %.

**Informes**
- `/mes`: total por categoría, % del total, presupuesto y comparación con la media de los últimos 3 meses.
- Gráfico circular o de barras como imagen.
- `/recortar`: detecta las categorías **prescindibles** que están por encima de su presupuesto o de su media, y calcula el impacto. Ejemplo: *"Si bajas Ocio y Comida fuera un 20 %, liberas 85 €/mes, que en 10 años al 5 % son unos 13.200 €"*.
- `/exportar`: descarga los movimientos en CSV.

### Puente: balance

- **Balance del mes** = ingresos − gastos.
  - Muestra la **tasa de ahorro** (%) y cuánto queda disponible para invertir.
- **Fondo de emergencia** = liquidez / gasto medio mensual, expresado en meses cubiertos (objetivo: 6).
  - **Si no está completo, el bot recomienda llenarlo antes de invertir más.**
- **Un gasto en la categoría 📈 Inversiones es una aportación.**
  - El bot pregunta con botones a qué cartera o clase de activo va.
  - Lo anota en el módulo de inversión como aportación (opcionalmente con participaciones y precio).
- **Patrimonio neto** = cuentas + carteras, con una foto guardada cada mes para ver la evolución.

### Módulo 2: Inversión (detalle)

Es lo que ya está construido:
- estrategia fija con reparto objetivo, margen de rebalanceo, aportación mensual y reglas;
- reparto de cada aportación;
- rebalanceo;
- espera obligatoria antes de cualquier operación fuera del plan;
- diario de decisiones;
- precios de Yahoo Finance.

Se añade:
- las aportaciones que llegan desde el módulo de gastos;
- el histórico mensual del valor;
- la rentabilidad acumulada frente a lo aportado.

### Módulo 3: Asistente IA (Claude)

Usa la **API de Claude** desde la Raspberry (SDK oficial `anthropic` en Python). Tiene tres funciones.

**a) Lectura de tickets** (foto o PDF de un ticket de compra)
- Claude extrae en JSON estructurado: comercio, fecha, total y **las líneas del ticket**.
  - Cada línea se clasifica en una categoría. Un ticket del súper puede repartirse entre 🛒 Comida, 💆 Autocuidado y 💊 Medicación.
- El bot enseña el resultado con botones `✅ Guardar` · `✏️ Corregir` · `❌ Descartar`. **Nunca guarda nada sin tu confirmación.**
- Las correcciones se guardan como ejemplos ("en Mercadona, el champú es Autocuidado"), para que la próxima vez acierte más.

**b) Capturas de movimientos** (captura de la app del banco o del extracto)
- Claude saca todos los movimientos de la imagen y propone una categoría para cada uno.
- El bot **detecta duplicados** con lo que ya está registrado (mismo importe, fecha y comercio) y te pide confirmar la lista.
- Así cuadras los gastos con tarjeta que no apuntaste a mano.
- **Varios bancos:** en `bancos.yaml` se configura cada banco y cuenta (nombre, formato de fecha, si los gastos salen en negativo…). Esas pistas se le pasan a Claude según el banco.
  - Cada movimiento queda asociado a su banco y cuenta.
  - **Transferencias entre tus propias cuentas:** se detectan (sale X de un banco y entra X en otro en ±2 días) y **no cuentan como gasto**.
  - Más adelante, para los bancos que lo permitan, se puede importar el **CSV del extracto** sin IA: es gratis y exacto.

**c) Preguntas en lenguaje natural**
- Ejemplos: *"¿cuánto gasté en ocio este trimestre comparado con el anterior?"*, *"¿cuánto puedo invertir este mes sin tocar el fondo de emergencia?"*, *"¿qué pasa si subo la renta fija al 20 %?"*.
- Claude **no ve la base de datos directamente**. Usa herramientas de solo lectura que define el bot:
  - `gastos_por_categoria(desde, hasta)`
  - `balance_mes(mes)`
  - `estado_cartera()`
  - `estrategia()`
  - `simular_estrategia(cambios)`
- **Ajustar parámetros de inversión:** Claude puede *proponer* un cambio en `estrategia.yaml` con su simulación (cómo quedaría el reparto, las aportaciones y el rebalanceo). La propuesta **pasa por la misma espera de 72 h** que cualquier operación. Claude nunca modifica la estrategia ni registra operaciones por su cuenta.
- Las instrucciones de Claude lo atan a tu estrategia escrita: responde con tus datos y reglas, y no da recomendaciones de compra o venta de valores concretos.

**Cómo se conecta a Claude: dos opciones, el bot sirve para ambas**

| | A) Tu suscripción (por defecto) | B) Clave de API |
|---|---|---|
| Cómo | Claude Code instalado en la Raspberry, con `claude login` hecho una vez con tu cuenta. El bot llama a `claude -p --model …` | Clave de console.anthropic.com en `.env` |
| Coste | **0 € extra**: consume de los límites de tu plan, compartidos con tu uso normal de Claude y Claude Code | Pago por uso. Con plan Max, Ultra o Team incluye créditos de API mensuales (Max: 100 $/mes) |
| Límite | Si agotas el límite del plan, el bot espera hasta que se renueve | Tope de gasto opcional en la consola |
| API de lotes (-50 %) | No disponible | Sí |
| Condiciones | Solo para ti: no se comparte el bot con nadie y nunca se copian ni se guardan los tokens de sesión | Sin restricciones |

La opción se elige en `modelos.yaml` (`proveedor: suscripcion | api`).

- Las fotos y los datos que se consultan se envían a la API de Anthropic para procesarlos. La base de datos completa sigue en la Raspberry.
- Si usas clave de API, se guarda en un archivo `.env` de la Raspberry, nunca en el repositorio.

### Elección dinámica del modelo según la dificultad

Candidatos, con precio por millón de tokens de entrada/salida y coste aproximado:

| Modelo | Precio | Por ticket | Por pregunta |
|---|---|---|---|
| Claude Haiku 5.5 | $0,10 / $0,50 | ~0,001 $ | ~0,002 $ |
| Claude Sonnet 5.5 | $2 / $10 | ~0,015 $ | ~0,025 $ |
| Claude Opus 5.5 | $4 / $20 | ~0,03 $ | ~0,05 $ |

**Escalera con comprobaciones objetivas.** Se empieza por el modelo barato y solo se sube de nivel si el resultado falla alguna comprobación que el bot hace sin IA:

| Tarea | Empieza en | Sube de nivel si… |
|---|---|---|
| Ticket | Haiku | la suma de las líneas no cuadra con el total (±0,02 €), falta la fecha o el comercio, o hay alguna línea con confianza baja |
| Captura de banco | Sonnet | el número de movimientos o los saldos no cuadran, o hay fechas imposibles |
| Pregunta sencilla ("¿cuánto gasté en X?") | Haiku | — |
| Análisis o comparación | Sonnet | — |
| Propuesta de cambio de estrategia | Opus | — |

- El tipo de pregunta lo decide primero una llamada muy barata a Haiku, que devuelve `sencilla`, `analisis` o `estrategia`.
- Si tú corriges el resultado, eso cuenta como un fallo de ese modelo para esa tarea.
- La configuración vive en `modelos.yaml`, editable sin tocar el código. Para cada tarea indica el modelo inicial, la escalera y el esfuerzo de razonamiento (*effort*).

### Periodo de prueba para elegir los modelos definitivos (2–4 semanas)

Se comparan **Claude Opus 5.5, Claude Sonnet 5.5 y Claude Haiku 5.5** con tus datos reales.

**Tickets y capturas:** cada imagen se procesa también con los otros modelos "en sombra". Tú solo ves el resultado del modelo principal.
- Las ejecuciones en sombra van por la noche, para no competir con tu uso de día. Con clave de API usarían la **API de lotes** (Batch API), que cuesta la mitad.
- Lo que tú confirmas o corriges se toma como la respuesta correcta.
- Para cada modelo se mide el acierto en total, fecha, comercio y categoría de cada línea, y en las capturas qué movimientos detectó y cuáles se inventó.

**Preguntas:** prueba **a ciegas**. Para cada pregunta, el bot te enseña dos respuestas (A y B, de modelos distintos y sin decirte cuál es cuál) y tú pulsas `A mejor` · `B mejor` · `Igual`.

**Informe `/evaluacion`:** para cada tarea y modelo muestra el % de acierto o de preferencia, el coste por cada 100 usos, el tiempo de respuesta y cuántas veces hubo que subir de nivel.

**Regla de decisión:** para cada tarea se elige **el modelo más barato que queda a menos de 2 puntos del mejor**. Con eso se actualiza `modelos.yaml`.

**Coste de la prueba:** con la suscripción, 0 € extra, pero consume más límite del plan, porque cada ticket se procesa 3 veces. Con clave de API serían unos 5–8 $.

### Interfaz del bot
- **Menú fijo** con 4 botones: `➕ Gasto` · `📊 Mes` · `⚖️ Balance` · `💼 Inversión`.
- Cada sección tiene submenús con botones dentro del propio mensaje. Los comandos `/…` siguen funcionando como atajo.
- **Avisos automáticos:**
  - el día de aportación;
  - cuando un presupuesto se está agotando;
  - un resumen cada domingo;
  - un cierre mensual con balance y recomendación;
  - cuando termina la espera de una idea de inversión.

### Técnica
- Python 3.11, `python-telegram-bot` v21, **SQLite** para los movimientos y YAML para la configuración (categorías, presupuestos y estrategia).
- Un servicio `systemd` en la Raspberry, que arranca solo y se reinicia si falla.
- **Copia de seguridad diaria** de la base de datos, enviada como archivo a mi propio chat de Telegram (gratis y fuera de la Raspberry).
- Panel Streamlit accesible en la red local (`http://raspberrypi.local:8501`).

### Fases
1. **Gastos básicos:** registro con botones, deshacer, `/mes`, ingresos y SQLite.
2. **Control:** presupuestos, gastos fijos recurrentes, avisos, `/recortar` y gráficos.
3. **Puente:** balance, tasa de ahorro, fondo de emergencia, Inversiones como aportación y patrimonio neto.
4. **Raspberry:** systemd, copias de seguridad y panel ampliado con gastos e histórico.
5. **IA:** lectura de tickets con escalera de modelos → capturas de varios bancos con duplicados y transferencias internas → preguntas con herramientas → **periodo de prueba** (sombra + prueba a ciegas + `/evaluacion`) → modelos definitivos en `modelos.yaml` → propuestas de estrategia con espera de 72 h.

---

## Decisiones abiertas (para ajustar)
1. **Ingresos:** ¿una nómina fija al mes o ingresos variables?
2. **Presupuestos:** ¿los pongo yo a partir de 1–2 meses de datos, o los defines tú desde el principio?
3. **Gastos con tarjeta:** ¿basta con apuntarlos a mano, o quieres importar el CSV del banco (y de qué banco)?
4. **¿Solo tú,** o también gastos compartidos (pareja o piso) con reparto?
5. **Cuentas de liquidez:** ¿cuántas cuentas o bancos hay que tener en cuenta para el fondo de emergencia?
6. ~~Modelo de IA~~ → **decidido:** escalera dinámica + periodo de prueba Opus 5.5 / Sonnet 5.5 / Haiku 5.5. Conexión: **tu suscripción** a través de Claude Code (opción A). Falta: ¿qué plan tienes (Pro, Max…)?
7. **Bancos:** son varios. ¿Cuáles son? Así preparo las pistas de cada uno en `bancos.yaml` y miro cuáles permiten exportar CSV.
