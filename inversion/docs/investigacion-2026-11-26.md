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

**Arreglado (2026-11-26)** en la rama `claude/elegant-noether-8104mp` de los dos playbooks. Se ha verificado ejecutando `kit.py seleccionar/tabla` y el instalador completo (generar → instalar → verificar → deshacer) con el perfil de ejemplo de la documentación.

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
- **Decidido: Pi 5 de 8 GB + SSD.** Lista de la compra:
  - Raspberry Pi 5 de 8 GB.
  - Fuente oficial USB-C de 27 W.
  - Carcasa con ventilador activo, o la Active Cooler oficial.
  - Adaptador M.2 NVMe (HAT oficial o equivalente).
  - SSD NVMe 2230/2242 de 256–512 GB.
  - Tarjeta microSD pequeña, solo para el primer arranque si hace falta.
- Instalar Raspberry Pi OS Lite de 64 bits en el SSD. Al instalar Claude Code, comprobar después que el binario existe de verdad (`claude --version`), por la incidencia del instalador en arm64.

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

## 4. Raspberry Pi 5 o mini PC (Black Friday 2026)

No he encontrado ofertas de Black Friday confirmadas en España para estas configuraciones. Los precios son los que aparecen en las tiendas y comparadores a finales de noviembre de 2026. Los de los accesorios son aproximados.

| | A) Pi 5 de 8 GB + SSD | B) Mini PC N150 16 GB / 512 GB | C) Mini PC Ryzen 7 32 GB |
|---|---|---|---|
| Equipo | Placa: 146 € (lo más barato en Amazon) – 230 € (tiendas oficiales) | 285–305 € (p. ej. Blackview MP60 a 304,99 € en PcComponentes); en EE. UU. el Beelink EQ14 está a 379 $ (-15 %) | 500–900 € |
| Extras | Fuente ~13 € + ventilador ~6 € + carcasa ~10–15 € + SSD Kit 256 GB ~55 € | Incluidos (fuente, SSD, carcasa) | Incluidos |
| **Total** | **~230–320 €** | **~285–305 €** | **~500–900 €** |
| Consumo en reposo (estimado) | ~3–5 W → ~6 €/año | ~6–10 W → ~13 €/año | ~10–15 W → ~20 €/año |
| RAM | 8 GB soldada | 16 GB (ampliable a 32 GB en el GMKtec G3 Plus) | 32 GB |
| Arquitectura | ARM (incidencias con Claude Code) | x86 (lo mismo que el CI y Docker) | x86 |
| IA en local | No | Modelos pequeños, lentos | Sí, modelos medianos |

(Electricidad calculada a 0,18 €/kWh.)

**Recomendación:** un mini PC N150 con 16 GB y 512 GB. Por un precio parecido al de la Pi completa:
- tiene el doble de RAM;
- es x86, así que no tiene los problemas de Claude Code en ARM y Docker usa las mismas imágenes que el CI;
- el SSD se puede ampliar, y la RAM también en algunos modelos;
- la diferencia de luz frente a la Pi es de unos 7 € al año.

**Modelos:**
- **GMKtec G3 Plus:** RAM ampliable.
- **Beelink EQ14:** fuente integrada y doble puerto de red de 2,5 GbE.

**Cuándo comprar:**
- ≤ 250 € → buena oferta, comprar.
- 250–300 € → precio normal.
- > 300 € → esperar o volver a la Pi.

Comprar en Amazon.es (vendido o enviado por Amazon) o en PcComponentes, por la devolución de 30 días y la garantía europea de 3 años. Se le borra Windows y se instala Ubuntu Server 24.04 LTS.

### Actualización (27-11-2026, Black Friday): "este proyecto y alguno más"

Para tener margen para varios proyectos (Docker, varios servicios, proyectos de datos), sube un escalón: un **Ryzen 5 con RAM DDR5 ampliable (SO-DIMM)**. No he podido verificar precios de Black Friday en euros en directo, así que los umbrales son orientativos.

| Gama | Ejemplos | Comprar si cuesta… |
|---|---|---|
| Ahorro | N150 16/512 (GMKtec G3 Plus, Beelink EQ14) | ≤ 250 € |
| **Recomendada** | Ryzen 5 6600H / 7430U / 7640HS, 16 GB DDR5 SO-DIMM, 512 GB–1 TB (GMKtec M6 Ultra; Blackview MP100PRO marcado "Top Black Friday" en PcComponentes) | ≤ 350 € con 16/512; ≤ 450 € con 32 GB/1 TB |
| Solo para IA en local | Ryzen 7 8745HS/8845HS 32 GB (Beelink SER8, GMKtec K8 Plus) | ≤ 600 € |

Antes de comprar:
- Que la RAM sea **SO-DIMM**: muchos Ryzen AI llevan LPDDR5X soldada y no se puede ampliar.
- Mirar el historial de precios (Keepa o camelcamelcamel en Amazon.es). Varias marcas subieron precios en noviembre.
- Mejor marcas con soporte y BIOS actualizada (GMKtec, Beelink, Minisforum), compradas en Amazon.es o PcComponentes.
