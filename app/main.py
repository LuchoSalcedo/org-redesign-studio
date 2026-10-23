"""Servidor web de Org Redesign Studio.

  uvicorn app.main:app --port 8000

Variables de entorno:
  ANTHROPIC_API_KEY   para el modo en vivo
  ADMIN_TOKEN         clave del presentador (por defecto "demo"); la vista de control es /?admin=<clave>
  ORG_MODEL           modelo de los agentes (por defecto claude-sonnet-5-5)
  VELOCIDAD_GUION     velocidad del guion de respaldo (0.65 por defecto ≈ 4 min; 1.3 ≈ 2 min)
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carga .env si existe (sin dependencias); las variables ya definidas en el entorno mandan.
_env = os.path.join(RAIZ, ".env")
if os.path.exists(_env):
    for _linea in open(_env, encoding="utf-8"):
        _linea = _linea.strip()
        if _linea and not _linea.startswith("#") and "=" in _linea:
            _k, _v = _linea.split("=", 1)
            if _v.strip():
                os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse  # noqa: E402

from app import agentes, motor  # noqa: E402
from app.bus import AGENTES, Bus  # noqa: E402
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "demo")

app = FastAPI(title="Org Redesign Studio")
bus = Bus()
tarea: asyncio.Task | None = None


def _check(token: str) -> None:
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Clave de presentador incorrecta")


@app.get("/")
async def index():
    return FileResponse(os.path.join(RAIZ, "static", "index.html"), headers={"Cache-Control": "no-store"})


@app.get("/api/empresa")
async def empresa():
    org = motor.cargar_asis()
    return {"nombre": "Consumo Andino S.A.A.", "nota": "Empresa ficticia con datos sintéticos",
            "personas": len(org), "areas": motor.resumen_asis_por_area(), "agentes": AGENTES,
            "vivo_disponible": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "grabacion_disponible": agentes.ultima_grabacion() is not None}


@app.get("/api/organizacion")
async def organizacion():
    return motor.organizacion_actual()


@app.get("/api/agentes")
async def agentes_config():
    return agentes.configuracion_agentes()


@app.get("/api/estado")
async def estado():
    return JSONResponse(bus.snapshot(), headers={"Cache-Control": "no-store"})


@app.get("/api/eventos")
async def eventos():
    q: asyncio.Queue = asyncio.Queue(maxsize=5000)
    # snapshot y suscripción en el mismo paso (sin await entre ambos): ningún evento se pierde ni se duplica
    bus.subs.add(q)
    snap = json.dumps(bus.snapshot(), ensure_ascii=False)

    async def stream():
        try:
            yield f"event: snapshot\ndata: {snap}\n\n"
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            bus.subs.discard(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/correr")
async def correr(modo: str = Query("guion"), token: str = Query("")):
    global tarea
    _check(token)
    if tarea and not tarea.done():
        raise HTTPException(status_code=409, detail="Ya hay una corrida en curso")
    if modo == "vivo" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=400, detail="Falta ANTHROPIC_API_KEY en el servidor")
    fn = {"vivo": agentes.correr_vivo, "guion": agentes.correr_guion, "grabacion": agentes.correr_grabacion}.get(modo)
    if not fn:
        raise HTTPException(status_code=400, detail="Modo desconocido")
    tarea = asyncio.create_task(fn(bus))
    return {"ok": True, "modo": modo}


@app.post("/api/reiniciar")
async def reiniciar(token: str = Query("")):
    global tarea
    _check(token)
    if tarea and not tarea.done():
        tarea.cancel()
    bus.reiniciar()
    await bus.emit({"type": "reset"})
    return {"ok": True}


@app.get("/api/descargar/{cual}.csv")
async def descargar(cual: str):
    if cual == "actual":
        filas = motor.cargar_asis()
    elif cual == "propuesta":
        s = bus.snapshot()
        if "modelo" not in s["datos"] or "tobe" not in s["datos"]:
            raise HTTPException(status_code=404, detail="Todavía no hay propuesta")
        r = motor.disenar_org(s["datos"]["modelo"], s["datos"]["tobe"]["reglas"])
        filas = [{k: p.get(k) for k in ("id", "jefe_id", "cargo", "rol", "bloque", "equipo", "tipo_trabajo",
                                        "persona_id", "area_actual", "costo_anual_usd")} for p in r["_org"]]
    else:
        raise HTTPException(status_code=404)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="organigrama-{cual}.csv"'})
