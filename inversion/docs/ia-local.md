# IA local en el mini PC — ideas para el proyecto finanzas-personales

> Resumen de la conversación del 27-11-2026. Las velocidades son **estimaciones**, no medidas: se miden en el periodo de prueba.

## 1. Hardware: GMKtec M6 Ultra (comprado)

- Ryzen 5 7640HS (6 núcleos, 12 hilos), gráfica integrada Radeon 760M.
- 16 GB de RAM DDR5-4800 en dos módulos SO-DIMM de 8 GB, ampliable a 32 o 64 GB.
- SSD M.2 NVMe PCIe 3.0 de 512 GB.
- Comprado por 449,99 € en la tienda europea de GMKtec, con el código BLACKFRIDAY20.
- **Ampliar la RAM hoy no compensa:** un kit de 32 GB (2×16) SO-DIMM cuesta unos 590 € por la crisis de la memoria. Esperar a que bajen los precios. Si algún día se amplía, cambiar siempre los dos módulos a la vez, para mantener el doble canal.

## 2. Cómo funciona la IA local en este equipo

- La gráfica es **integrada**: no tiene memoria propia. Usa la misma RAM que el sistema, así que los 16 GB son para todo.
  - En la BIOS, la opción "UMA Frame Buffer Size" reserva una parte fija para la gráfica.
  - En Linux, la gráfica puede tomar más RAM según la necesite, pero siempre de esos 16 GB.
- La velocidad al generar texto depende sobre todo de lo rápido que se lee la RAM (~75 GB/s como máximo teórico). La gráfica acelera mucho la lectura del texto de entrada (el *prompt*), pero poco la escritura de la respuesta.
- **Escenario elegido:** mini PC dedicado a IA local y al bot, **sin Docker**. Docker se queda en el PC de desarrollo. Ubuntu Server sin escritorio ocupa ~1 GB, así que quedan **~13–14 GB para el modelo**.

### Qué modelos caben (estimado)

| Tamaño (cuantizado a 4 bits) | Ejemplos | Velocidad | ¿Viable? |
|---|---|---|---|
| 1–4B (~1–2,5 GB) | Llama 3.2 3B, Qwen 3B | ~20–30 tokens/s | ✅ Muy fluido |
| 7–8B (~5 GB) | Llama 3.1 8B, Qwen 7B | ~10–15 tokens/s | ✅ Usable |
| 12–14B (~9 GB) | Qwen 14B, Gemma 3 12B | ~5–7 tokens/s | ⚠️ Lento |
| 30B o más | — | — | ❌ No cabe |

### Para qué sirve (y para qué no)

- ✅ Clasificar gastos a partir de texto ("Mercadona 45 €" → Supermercado), con un modelo de 3–8B y sin que los datos salgan de casa.
- ✅ Transcribir notas de voz con **Whisper**: el usuario manda un audio al bot y el gasto se apunta solo.
- ✅ Embeddings para buscar por significado en notas y movimientos.
- ⚠️ Leer tickets con un modelo de visión pequeño: funciona, pero es más lento y menos preciso que Claude.
- ❌ Programar con agentes, analizar la cartera o razonar en serio: eso se queda en Claude (Sonnet u Opus).

## 3. Experimento: lectura de tickets con IA local

### Opciones a comparar

| Opción | Cómo funciona | RAM | Tiempo por ticket (estimado) |
|---|---|---|---|
| **A. OCR + modelo de texto pequeño** | PaddleOCR o Tesseract extraen el texto, y un modelo de 3–8B lo estructura en JSON (comercio, fecha, total, líneas) | ~3–6 GB | ~5–15 s |
| **B. Modelo de visión de 7B** (Qwen2.5-VL 7B, MiniCPM-V) | Recibe la foto y devuelve el JSON directamente | ~6–8 GB | ~20–40 s |
| **C. Modelo de visión de 12B** (Gemma 3 12B) | Igual que B, algo más preciso | ~9–10 GB | ~40–90 s |

Lo esperable: los tickets claros salen bien y los arrugados, borrosos o largos, peor. La opción A suele ser la más rápida y estable en este hardware.

### Encaje en la escalera de modelos (ver VISION.md)

El modelo local pasa a ser **el primer peldaño, gratuito**:

```
Ticket → local (gratis)
           ¿suma de líneas = total (±0,02 €)? ¿hay fecha y comercio? ¿confianza alta?
             sí → se muestra con botones ✅ Guardar / ✏️ Corregir / ❌ Descartar
             no → Haiku 5.5 → Sonnet 5.5 (→ Opus 5.5)
```

- Las comprobaciones automáticas, que no usan IA, deciden cuándo hace falta Claude.
- Si el usuario corrige un resultado, cuenta como fallo de ese modelo.
- En `modelos.yaml` se añade el proveedor `local`:
  ```yaml
  proveedores: [local, suscripcion, api]
  tickets:
    escalera: [local, haiku, sonnet]
  ```

### Montaje técnico

- **Servidor de modelos en el mini PC:** Ollama o llama.cpp con el backend Vulkan, que aprovecha la Radeon 760M. Se mide cuál de los dos va más rápido.
- Se expone una API compatible con OpenAI **solo dentro de la red de casa**. El bot la llama igual que a cualquier otro proveedor.
- OCR (opción A): PaddleOCR o Tesseract instalados en el mismo mini PC.
- El bot sigue funcionando como servicio systemd, sin Docker.

### Prueba (dentro del periodo de prueba de modelos)

1. Reunir 20–30 fotos de tickets reales, mezclando fáciles y difíciles.
2. Procesar cada ticket con: local A, local B, Haiku 5.5 y Sonnet 5.5.
3. La confirmación del usuario en el bot es la respuesta correcta.
4. Medir con `/evaluacion`: acierto por campo (total, fecha, comercio, categoría de cada línea), tiempo por ticket, coste y cuántas veces hubo que subir de peldaño.
5. **Decisión:** el modelo local entra como primer peldaño si acierta sin necesidad de subir en una parte relevante de los tickets (umbral a fijar con los datos) y en un tiempo aceptable (por ejemplo, < 30 s).

## 4. Próximos pasos

- [ ] Añadir este experimento a la fase 5 (IA) de VISION.md del proyecto.
- [ ] Cuando llegue el mini PC: Ubuntu Server 24.04, encendido automático tras un corte de luz, Ollama o llama.cpp con Vulkan, y una prueba de velocidad (`llama-bench`) con un modelo de 3B, uno de 7B y uno de visión de 7B.
- [ ] Implementar la interfaz de proveedores (`local | suscripcion | api`) en el módulo de IA.
- [ ] Reunir las fotos de tickets para la prueba.
