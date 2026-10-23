"""Prueba rápida de punta a punta (sin IA): corre el guion de respaldo a alta velocidad y
verifica que el resultado sea consistente.

Uso: python3 -m app.prueba
Córrelo después de cualquier cambio al motor, a los agentes o al bus.
"""
import asyncio
import os

os.environ.setdefault("VELOCIDAD_GUION", "200")

from app import agentes, empresas, motor  # noqa: E402
from app.bus import Bus  # noqa: E402


async def probar(empresa_id: str) -> None:
    e = empresas.get(empresa_id)
    bus = Bus()
    await bus.emit({"type": "empresa", "empresa": empresa_id})
    await agentes.correr_guion(bus)
    s = bus.snapshot()
    d = s["datos"]
    assert s["corrida"]["estado"] == "terminada", s["corrida"]
    assert d["veredicto"]["veredicto"] == "APROBADO"
    assert s["empresa"] == empresa_id
    assert d["asis"]["personas"] == len(motor.cargar_asis(e))
    assert d["tobe"]["metricas"]["capas"] <= 7
    assert d["tobe"]["metricas"]["jefes_un_reporte"] == 0
    assert all(a["estado"] == "listo" for a in s["agentes"].values())
    # cada contribuidor individual de hoy existe en la propuesta
    _, hijos, _ = motor._indices(motor.cargar_asis(e))
    ics_hoy = sum(1 for p in motor.cargar_asis(e) if p["capacidad"] != "direccion" and p["id"] not in hijos)
    r = motor.disenar_org(e, d["modelo"], d["tobe"]["reglas"])
    ics_prop = sum(1 for p in r["_org"] if p["rol"] == "ic")
    assert ics_prop == ics_hoy, (ics_prop, ics_hoy)
    assert not any(h["severidad"] == "alta" for h in d["riesgos"]["hallazgos"]), d["riesgos"]
    texto = " ".join(a["texto"] for a in s["agentes"].values())
    assert "{" not in texto and "None" not in texto, "texto del guion mal armado"
    i = d["impacto"]
    print(f"OK · {e.corto:<16} · {i['antes']['capas']}→{i['despues']['capas']} capas · {i['antes']['jefaturas']}→{i['despues']['jefaturas']} "
          f"jefaturas · tramo {i['antes']['tramo_promedio']}→{i['despues']['tramo_promedio']} · ahorro USD {i['ahorro_anual_musd']} M")


async def main() -> None:
    for empresa_id in empresas.ORDEN:
        await probar(empresa_id)


if __name__ == "__main__":
    asyncio.run(main())
