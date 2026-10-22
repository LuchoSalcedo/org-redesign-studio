"""Prueba rápida de punta a punta (sin IA): corre el guion de respaldo a alta velocidad y
verifica que el resultado sea consistente.

Uso: python3 -m app.prueba
Córrelo después de cualquier cambio al motor, a los agentes o al bus.
"""
import asyncio
import os

os.environ.setdefault("VELOCIDAD_GUION", "200")

from app import agentes, motor  # noqa: E402
from app.bus import Bus  # noqa: E402


async def main() -> None:
    bus = Bus()
    await agentes.correr_guion(bus)
    s = bus.snapshot()
    d = s["datos"]
    assert s["corrida"]["estado"] == "terminada", s["corrida"]
    assert d["veredicto"]["veredicto"] == "APROBADO"
    assert d["asis"]["personas"] == len(motor.cargar_asis())
    assert d["tobe"]["metricas"]["capas"] <= 7
    assert d["tobe"]["metricas"]["jefes_un_reporte"] == 0
    assert all(a["estado"] == "listo" for a in s["agentes"].values())
    # cada contribuidor individual de hoy existe en la propuesta
    ics_hoy = sum(1 for p in motor.cargar_asis() if p["capacidad"] != "direccion") - motor.diagnostico()["jefaturas"] + 1
    r = motor.disenar_org(d["modelo"], d["tobe"]["reglas"])
    ics_prop = sum(1 for p in r["_org"] if p["rol"] == "ic")
    assert abs(ics_prop - ics_hoy) <= 12, (ics_prop, ics_hoy)
    i = d["impacto"]
    print(f"OK · {i['antes']['capas']}→{i['despues']['capas']} capas · {i['antes']['jefaturas']}→{i['despues']['jefaturas']} "
          f"jefaturas · tramo {i['antes']['tramo_promedio']}→{i['despues']['tramo_promedio']} · ahorro USD {i['ahorro_anual_musd']} M")


if __name__ == "__main__":
    asyncio.run(main())
