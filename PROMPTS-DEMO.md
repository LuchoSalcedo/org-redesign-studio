# Prompts para el cambio en vivo con Claude Code

Antes de la sesión: deja corriendo la app en tu laptop (`uvicorn app.main:app --port 8000`) con
una corrida terminada (guion o en vivo) y abre `http://localhost:8000/?admin=<clave>` en una pestaña.
Abre esta carpeta en VS Code con Claude Code en la terminal.

Después de los cambios 1 y 2: recarga la pestaña. Solo tocan `static/index.html`, así que el
servidor no se reinicia y el cambio aparece con los datos que la sala ya vio.

---

## Cambio 1 (seguro, ~1 minuto): el costo de cada bloque

```
En la vista del modelo producto-plataforma, agrega debajo de las personas de cada bloque su costo
anual en USD millones (ya viene en tobe.bloques como costo_musd). Después corre python3 -m app.prueba.
```

## Cambio 2 (~2 minutos): un indicador que pide la sala

```
Agrega un indicador "Costo de jefaturas" en la columna de KPIs, con el formato de los demás:
hoy → propuesta en USD millones y el % de cambio. Los datos están en asis.costo_jefaturas_musd y
tobe.metricas.costo_jefaturas_musd. Después corre python3 -m app.prueba.
```

## Cambio 3 (solo si lo ensayaste, ~5 minutos): una regla nueva del CHRO

Este cambio toca el motor, así que obliga a reiniciar el servidor local (se pierde la corrida
local, no la publicada) y a correr los agentes otra vez.

```
Agrega una regla al CHRO en motor.revisar_riesgos: si alguna plataforma tiene un líder con más de
6 reportes directos, es un riesgo medio porque no le alcanza el tiempo para gestionar a sus equipos.
Revisa que el guion de respaldo siga siendo coherente y corre python3 -m app.prueba.
```

Luego: Ctrl+C en la terminal del servidor, `uvicorn app.main:app --port 8000` otra vez y
**▶ En vivo** en tu laptop para que la sala vea al CHRO usar la regla nueva.
