# Investigación — 2026-11-26

## 1. Estado del kit de buenas prácticas (platform-engineering-playbook)

**Fase 0 del prompt `NEW_PLATFORM_PROJECT_PROMPT.md`:**

| Comprobación | Resultado (sesión en la nube) |
|---|---|
| `~/.claude/pipeline_profile.json` | **No existe.** El prompt dice que hay que parar e instalar antes el pipeline personal. |
| git | 2.43.0 |
| python | 3.13 |
| uv | 0.11 |
| claude | 2.1.332 |
| docker | 29.9 |
| node / npm | 22 / 10.9 |
| task (go-task) | **FALTA** |
| pre-commit | **FALTA** |
| gitleaks | **FALTA** |

**Fallos encontrados en el kit.** La documentación está en inglés y el código en español, y no coinciden:

| La documentación dice | El código espera |
|---|---|
| `kit.py select / install / check / table` | `seleccionar / instalar / comprobar / tabla` |
| `--type platform --options` | `--tipo plataforma --opciones` |
| `SKILLS_CATALOG.json` (el archivo que existe) | `CATALOGO_SKILLS.json` → **falla con FileNotFoundError** |
| `~/.claude/pipeline_profile.json` | `instalar.py` busca `perfil_pipeline.json` |
| `general_guide/`, `tools/install.py` | la carpeta real es `general-pipeline/` y el script es `tools/instalar.py` |

`kit.py` es idéntico en `ml-engineering-playbook`, así que tiene el mismo fallo. Tal como está publicado, el kit no se puede ejecutar siguiendo sus propias instrucciones.

**Encaje con este proyecto.** El kit está pensado para plataformas web: FastAPI, OpenAPI, `/health`, OIDC y Docker Compose. Este proyecto es un bot de Telegram con un panel Streamlit y SQLite, para un solo usuario. Lo que encaja directamente:
- estructura por capas;
- `CLAUDE.md`, ADR, CHANGELOG;
- pre-commit con dos niveles, gitleaks, Taskfile y CI;
- TDD y tests basados en propiedades (para los parsers de importes);
- runbook de copia de seguridad y vuelta atrás.

Lo que hay que adaptar y dejar escrito en el ADR 0001:
- **API/OpenAPI:** no hay API HTTP. El "contrato" serían los comandos del bot y el esquema de la base de datos.
- **OIDC:** no aplica. La autenticación es el chat id de Telegram.
- **`/health`:** un latido del bot y del servicio systemd en lugar de un endpoint.

## 2. Raspberry Pi

- **Precios (noviembre de 2026):**
  - Pi 5 de 8 GB: unos 175 $.
  - Pi 5 de 16 GB: unos 385 $, tras varias subidas por el coste de la RAM.
  - Un kit completo de 16 GB con NVMe ronda los 475–500 $.
- **Recomendación: Pi 5 de 8 GB + carcasa con ventilador + fuente oficial de 27 W + adaptador NVMe + SSD de 256–512 GB.**
  - El bot, SQLite, Streamlit y Claude Code caben de sobra en 8 GB. La IA se ejecuta en los servidores de Anthropic, no en la Raspberry.
  - **SSD en vez de tarjeta microSD:** las escrituras continuas de la base de datos y los logs desgastan las tarjetas.
- **Alternativa:** con estos precios, un mini PC x86 de segunda mano o de gama baja cuesta parecido. Además evita los problemas de Claude Code en ARM:
  - hay incidencias abiertas en GitHub sobre el instalador nativo en Raspberry (arm64), con instalaciones que dicen terminar bien sin haberlo hecho;
  - hay problemas de login en Pi 4.
- **Decisión pendiente:** Pi 5 de 8 GB (más bonito, menos consumo) o mini PC (menos riesgo con Claude Code, misma inversión).

## 3. Repos existentes que se pueden aprovechar

**Para la IA de tickets y gastos** (ideas o código; ninguno usa Claude):
- **Dompetku** (ilramdhan, MIT): finanzas personales autoalojadas con bot de Telegram, lectura de tickets, presupuestos y copias de seguridad. Es el más parecido.
- **Ledger** (Evy0210): foto del ticket, correo o una línea al bot de Telegram, y lo categoriza.
- **TaxHacker** (vas3k): contabilidad con IA y extracción de documentos. Buen ejemplo de esquemas de extracción.

**Para traer datos de los bancos:**
- **Trade Republic:** **pytr** (`pytr-org/pytr`) exporta transacciones a CSV/JSON con `export_transactions`. No es oficial: usa la API privada de Trade Republic.
- **MyInvestor:** desde la web, un "Resumen de movimientos" en Excel para la cuenta. Las operaciones con valores van por Inversis.
- **BBVA:** descarga de movimientos desde la web o la app. Hay que comprobar el formato con un archivo real.

**Skills, hooks y agentes para Claude Code:**
- **Listas:** `hesreallyhim/awesome-claude-code` (la más citada) y `VoltAgent/awesome-agent-skills`.
- **Finanzas personales:** `afrexai-personal-finance` (de aAAaqwq/AGI-Super-Team) cubre presupuestos, inversión y patrimonio neto. Hay que pasarlo por `skill-scanner` antes de usarlo, como marca tu playbook.
- **Ya en tu kit:** `find-bugs`, `security-review`, `security-audit` y `skill-scanner` (vendorizados), y el pipeline personal (guardian, continuidad, diario y tareas).

**Para portfolio** (seguimos con el módulo propio y su estrategia fija):
- **Ghostfolio** y **Portfolio Performance**: hay un fork de pytr (`pytrpp2`) que exporta a formato Portfolio Performance.

No he comprobado estrellas, mantenimiento ni licencias de cada repo. Se revisan antes de copiar nada.
