"""Bus de eventos: guarda el estado de la corrida y lo transmite a todos los navegadores.

Cada evento es un dict con "type". El estado (snapshot) se reconstruye aplicando los
eventos en orden; un navegador que se conecta tarde recibe el snapshot y luego los
eventos en vivo.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import time

AGENTES = [
    {"id": "diagnostico", "nombre": "Diagnóstico", "rol": "Mide capas, tramos y jefaturas"},
    {"id": "capacidades", "nombre": "Mapa de capacidades", "rol": "Encuentra capacidades duplicadas"},
    {"id": "disenador", "nombre": "Diseñador producto-plataforma", "rol": "Propone el modelo objetivo"},
    {"id": "optimizador", "nombre": "Optimizador span & layers", "rol": "Diseña las jefaturas desde la base"},
    {"id": "impacto", "nombre": "Impacto", "rol": "Calcula posiciones, costo y movimientos"},
    {"id": "chro", "nombre": "CHRO escéptico", "rol": "Revisa riesgos y objeta"},
]


def estado_inicial() -> dict:
    return {
        "corrida": {"estado": "lista", "modo": None, "inicio": None, "fin": None, "fase": "Esperando al partner"},
        "agentes": {a["id"]: {**a, "estado": "en espera", "texto": "", "herramientas": [], "ronda": 1}
                    for a in AGENTES},
        "datos": {},
        "bitacora": [],
    }


def aplicar(estado: dict, ev: dict) -> None:
    t = ev["type"]
    if t == "reset":
        nuevo = estado_inicial()
        estado.clear()
        estado.update(nuevo)
    elif t == "run_start":
        nuevo = estado_inicial()
        estado.clear()
        estado.update(nuevo)
        estado["corrida"].update({"estado": "corriendo", "modo": ev.get("modo"), "inicio": ev["ts"]})
    elif t == "phase":
        estado["corrida"]["fase"] = ev["name"]
        estado["bitacora"].append({"ts": ev["ts"], "texto": ev["name"], "agente": None})
    elif t == "agent_status":
        a = estado["agentes"][ev["agent"]]
        a["estado"] = ev["status"]
        if ev.get("ronda"):
            a["ronda"] = ev["ronda"]
            if ev["status"] == "pensando" and ev["ronda"] > 1:
                a["texto"] += "\n\n— Ronda 2 —\n"
    elif t == "agent_text":
        estado["agentes"][ev["agent"]]["texto"] += ev["delta"]
    elif t == "agent_tool":
        estado["agentes"][ev["agent"]]["herramientas"].append({"herramienta": ev["tool"], "resumen": ev["summary"]})
        estado["bitacora"].append({"ts": ev["ts"], "texto": ev["summary"], "agente": ev["agent"]})
    elif t == "data":
        estado["datos"][ev["key"]] = ev["value"]
        if ev["key"] == "tobe":
            estado["datos"].setdefault("tobe_historial", []).append(
                {k: ev["value"]["metricas"][k] for k in ("capas", "jefaturas", "tramo_promedio")})
    elif t == "run_end":
        estado["corrida"].update({"estado": ev.get("estado", "terminada"), "fin": ev["ts"],
                                  "fase": ev.get("fase", "Diseño listo")})
    estado["bitacora"] = estado["bitacora"][-60:]


class Bus:
    def __init__(self) -> None:
        self.estado = estado_inicial()
        self.subs: set[asyncio.Queue] = set()
        self.grabacion: list[dict] = []
        self.t0 = time.time()

    async def emit(self, ev: dict) -> None:
        ev = {**ev, "ts": round(time.time(), 3)}
        if ev["type"] == "run_start":
            self.grabacion = []
            self.t0 = ev["ts"]
        self.grabacion.append(ev)
        aplicar(self.estado, ev)
        for q in list(self.subs):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass

    def snapshot(self) -> dict:
        return copy.deepcopy(self.estado)

    def guardar_grabacion(self, carpeta: str) -> str | None:
        if not self.grabacion:
            return None
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, time.strftime("corrida-%Y%m%d-%H%M%S.jsonl"))
        with open(ruta, "w", encoding="utf-8") as f:
            for ev in self.grabacion:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ruta

    def reiniciar(self) -> None:
        self.estado = estado_inicial()
        self.grabacion = []
