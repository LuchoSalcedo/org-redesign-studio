# Org Redesign Studio

Seis agentes de IA rediseñan en vivo la organización de una empresa ficticia: la bajan de
10 capas a 7 o menos, suben los tramos de control y la reorganizan en un modelo
producto-plataforma. Un CHRO escéptico revisa el diseño y lo objeta; el equipo corrige en
una segunda ronda. El presentador elige una de cuatro empresas (todas con datos sintéticos):

| Empresa | Sector · país | Personas |
|---|---|---|
| Consumo Andino S.A.A. | Consumo masivo · Perú | 3,744 |
| Banco Cumbre | Banca enfocada en empresas · México | 2,140 |
| Tiendas Esquina | Tiendas de conveniencia · México | 3,813 |
| Cóndor Telecom | Telecomunicaciones · Colombia | 2,751 |

- **Vista del público:** `https://<tu-app>/` — cualquiera la sigue en vivo desde el celular.
- **Vista del presentador:** `https://<tu-app>/?admin=<ADMIN_TOKEN>` — muestra los botones. Al cargar,
  la clave se borra de la barra de direcciones, pero usa una clave larga (no `demo`): con ella
  cualquiera podría reiniciar la corrida.
- **Pantalla recomendada:** 1920×1080 en pantalla completa. La vista del rediseño cabe en una sola
  pantalla desde 1280×720; en pantallas bajas algunas tarjetas muestran menos texto.
- **Cambiar de empresa:** en la vista "Organización actual", haz clic en otra empresa (solo el
  presentador). Todas las pantallas conectadas cambian con él. No se puede cambiar durante una corrida.

## Correr en tu laptop (10 minutos)

1. Python 3.11 o superior.
2. En la carpeta del proyecto:
   ```
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env        # pon tu ANTHROPIC_API_KEY y una ADMIN_TOKEN
   python3 -m app.prueba       # debe imprimir "OK · 10→7 capas …"
   uvicorn app.main:app --port 8000
   ```
3. Abre `http://localhost:8000/?admin=<tu clave>` y pulsa **▶ Guion de respaldo** para verla funcionar sin IA.
   Luego **▶ En vivo** para la corrida real con agentes.

## Publicar en la web (Render, ~15 minutos la primera vez)

1. Sube esta carpeta a un repositorio privado de GitHub.
2. En render.com: **New → Blueprint** y elige el repositorio (usa `render.yaml`).
3. Llena `ANTHROPIC_API_KEY` y `ADMIN_TOKEN` cuando te las pida.
4. Usa el plan **Starter**: el gratuito se duerme y tarda un minuto en despertar.
5. Debe quedar **una sola instancia**: el estado de la corrida vive en memoria.

Cualquier servicio que corra un contenedor Docker sirve (Railway, Fly.io, Cloud Run con
instancias mínimas = 1 y máximas = 1).

## Los tres botones

| Botón | Qué hace | Cuándo usarlo |
|---|---|---|
| ▶ En vivo | Agentes reales con la API de Claude. Unos 5-8 minutos. | La demo. |
| ▶ Guion de respaldo | Mismo flujo y mismos cálculos reales; los textos están pre-escritos. Unos 4 minutos. | Si falla internet o la API. |
| ▶ Repetir grabación | Repite la última corrida en vivo, con su ritmo original (pausas largas recortadas a 4 s). | Plan B con textos reales de IA. |

Cada corrida en vivo se graba en `runs/`. Para tener la grabación siempre disponible en la
web, haz una corrida en vivo en tu laptop durante el ensayo y sube el archivo de `runs/` al
repositorio antes de publicar.

## Datos

La organización es sintética (`app/generar_org.py`, semilla fija). Nombres, cargos y
costos son inventados. Descarga el organigrama actual en `/api/descargar/actual.csv` y la
propuesta en `/api/descargar/propuesta.csv`.
