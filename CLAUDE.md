# Org Redesign Studio

App web de demostración: seis agentes de IA rediseñan la organización de una empresa
FICTICIA de consumo masivo peruana (Consumo Andino S.A.A., 3,744 personas) hacia un
modelo producto-plataforma, ajustando span & layers. La interfaz muestra en vivo cómo
trabajan los agentes. Se usa en demos en vivo frente a audiencias de negocio:
**todo cambio debe ser pequeño, seguro y verificable en menos de 3 minutos.**

## Arquitectura (4 archivos importan)

| Archivo | Qué hace |
|---|---|
| `app/motor.py` | Toda la aritmética: diagnóstico, mapa de capacidades, validación del modelo, diseño del organigrama desde la base (`disenar_org`), riesgos del CHRO (`revisar_riesgos`), impacto. Determinístico. |
| `app/agentes.py` | Prompts, herramientas y orquestación de los 6 agentes. Modos: `vivo` (API de Claude), `guion` (plan B sin IA, textos pre-escritos con números reales) y `grabacion` (repite la última corrida en vivo de `runs/`). |
| `app/bus.py` | Eventos y estado de la corrida. `aplicar()` es el reducer; `static/index.html` tiene un espejo en JS (`aplicar`) que debe mantenerse igual. |
| `static/index.html` | Interfaz completa en un solo archivo (HTML + CSS + JS, sin build, sin dependencias). Dibuja con SVG a mano. Tres vistas: Organización actual, Rediseño con agentes y Cómo funciona (con el popup de configuración de cada agente). |
| `app/main.py` | FastAPI: `/` interfaz, `/api/eventos` SSE, `/api/organizacion` (vista previa a la corrida), `/api/agentes` (configuración visible de cada agente), `/api/correr?modo=…&token=…`, `/api/reiniciar`, `/api/descargar/{actual|propuesta}.csv`. |
| `app/generar_org.py` | Genera la organización sintética (semilla fija). |

Flujo de una corrida: Diagnóstico + Capacidades (en paralelo) → Diseñador → Optimizador → Impacto → CHRO.
Si el CHRO objeta, hay una ronda 2 (Diseñador → Optimizador → Impacto → CHRO).

Los datos que ve la interfaz llegan como eventos `{"type":"data","key":…}` con estas llaves:
`asis` (diagnóstico), `capacidades`, `modelo`, `tobe` (diseño: `metricas`, `bloques`, `reglas`, `alertas`),
`impacto`, `riesgos`, `veredicto`. Cada bloque de `tobe.bloques` trae `nombre`, `tipo`, `personas`,
`jefaturas`, `equipos`, `reportes_del_lider`, `capas`, `costo_musd`.

## Reglas para cambios

- **Diseño visual: sistema RGMx.** Usa solo las variables CSS de `:root` en `index.html` (nada de hex sueltos),
  botones en MAYÚSCULAS con un solo primario por zona, cada KPI con delta y referencia, y deltas en verde o rojo
  según si el cambio es bueno para ese KPI (menos capas o jefaturas = verde).

- Los números los calcula `motor.py`, nunca los agentes ni la interfaz.
- Textos visibles en español, frases cortas.
- No agregues dependencias ni pasos de build. La interfaz sigue siendo un solo archivo.
- Si agregas un tipo de evento o una llave de estado, actualiza `bus.aplicar` Y el `aplicar` de `index.html`.
- Si cambias reglas del motor que afectan el guion de respaldo, revisa que los textos de `correr_guion` sigan siendo ciertos.

## Cómo verificar (siempre, después de cada cambio)

```
python3 -m app.prueba                 # corrida completa sin IA a alta velocidad; debe imprimir "OK · …"
uvicorn app.main:app --port 8000      # luego abre http://localhost:8000/?admin=demo y corre el guion
```
