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

from app import agentes, empresas, motor  # noqa: E402
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


def _activa() -> empresas.Empresa:
    return empresas.get(bus.estado.get("empresa"))


def _ficha(e: empresas.Empresa) -> dict:
    return {"id": e.id, "nombre": e.nombre, "corto": e.corto, "iniciales": e.iniciales, "pais": e.pais,
            "sector": e.sector, "descripcion": e.descripcion, "personas": len(motor.cargar_asis(e)),
            "grabacion_disponible": agentes.ultima_grabacion(e.id) is not None}


@app.get("/api/empresa")
async def empresa(empresa: str = Query("")):
    e = empresas.get(empresa) if empresa else _activa()
    return {**_ficha(e), "nota": "Empresa ficticia con datos sintéticos", "agentes": AGENTES,
            "areas": motor.resumen_asis_por_area(e),
            "vivo_disponible": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "empresas": [_ficha(empresas.get(i)) for i in empresas.ORDEN]}


@app.get("/api/organizacion")
async def organizacion(empresa: str = Query("")):
    return motor.organizacion_actual(empresas.get(empresa) if empresa else _activa())


@app.get("/api/agentes")
async def agentes_config(empresa: str = Query("")):
    return agentes.configuracion_agentes(empresas.get(empresa) if empresa else _activa())


@app.post("/api/seleccionar")
async def seleccionar(empresa: str = Query(...), token: str = Query("")):
    _check(token)
    if empresa not in empresas.EMPRESAS:
        raise HTTPException(status_code=400, detail="Empresa desconocida")
    if tarea and not tarea.done():
        raise HTTPException(status_code=409, detail="Hay una corrida en curso: reinicia antes de cambiar de empresa")
    await bus.emit({"type": "empresa", "empresa": empresa})
    return {"ok": True, "empresa": empresa}


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
    e = _activa()
    if cual == "actual":
        filas = motor.cargar_asis(e)
    elif cual == "propuesta":
        s = bus.snapshot()
        if "modelo" not in s["datos"] or "tobe" not in s["datos"]:
            raise HTTPException(status_code=404, detail="Todavía no hay propuesta")
        r = motor.disenar_org(e, s["datos"]["modelo"], s["datos"]["tobe"]["reglas"])
        filas = [{k: p.get(k) for k in ("id", "jefe_id", "cargo", "rol", "bloque", "equipo", "tipo_trabajo",
                                        "persona_id", "area_actual", "costo_anual_usd")} for p in r["_org"]]
    else:
        raise HTTPException(status_code=404)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="organigrama-{e.id}-{cual}.csv"'})
