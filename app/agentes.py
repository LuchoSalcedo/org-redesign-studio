"""Los seis agentes y su orquestación.

Tres modos de correr:
  - "vivo":      agentes reales con la API de Claude (requiere ANTHROPIC_API_KEY).
  - "guion":     plan B sin IA: mismo flujo y mismos cálculos reales, textos pre-escritos.
  - "grabacion": repite la última corrida en vivo grabada (runs/*.jsonl) con su ritmo original.

Los cálculos SIEMPRE los hace app/motor.py; los agentes deciden el diseño.
"""
from __future__ import annotations

import asyncio
import glob
import json
import os

from app import motor
from app.bus import Bus

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELO = os.environ.get("ORG_MODEL", "claude-sonnet-5-5")
MODELO_CHRO = os.environ.get("ORG_MODEL_CHRO", MODELO)
VELOCIDAD = float(os.environ.get("VELOCIDAD_GUION", "0.65"))  # 0.65 ≈ 4 minutos; >1 = más rápido

CASO = (
    "Cliente: Consumo Andino S.A.A. (empresa FICTICIA de consumo masivo en Perú, 3,744 colaboradores; "
    "plantas en Lima, Arequipa y Trujillo; categorías Galletas, Pastas y Harinas, Salsas y Condimentos, "
    "Bebidas y Cuidado del Hogar). Hoy tiene tres unidades de negocio con capacidades duplicadas, "
    "funciones corporativas y una gran operación de plantas y fuerza de ventas. "
    "El CEO pide: (1) pasar a un modelo producto-plataforma, (2) máximo 7 capas, (3) subir los tramos "
    "de control, sin comprometer la seguridad en planta ni la cobertura comercial."
)

ESTILO = (
    "Escribes en español para 50 gerentes que leen tu texto proyectado en vivo. Frases cortas. "
    "Antes de usar una herramienta, di en una línea qué vas a hacer. Después de los resultados, da "
    "máximo 5 viñetas con números concretos. Nada de introducciones ni despedidas. Nunca inventes cifras: "
    "usa solo las que devuelven las herramientas."
)

PROMPTS = {
    "diagnostico": f"Eres el analista de diagnóstico organizacional del equipo. {ESTILO} "
                   "Mide span & layers con tu herramienta y explica los 4 problemas más importantes "
                   "(capas, tramos bajos, jefes de un solo reporte, áreas críticas).",
    "capacidades": f"Eres el analista de capacidades del equipo. {ESTILO} "
                   "Usa tu herramienta para ver dónde vive cada capacidad hoy. Señala cuáles están duplicadas "
                   "entre unidades de negocio y cuáles deberían ser plataformas compartidas.",
    "disenador": f"Eres el diseñador del modelo producto-plataforma. {ESTILO} "
                 "Productos = equipos por categoría con marketing de marca, innovación y category management. "
                 "Plataformas = capacidades compartidas que sirven a todos los productos (supply, go-to-market, "
                 "datos y RGM, digital, etc.). Habilitadores = finanzas, gestión humana, tecnología, legal. "
                 "Reglas de diseño: no pongas plantas (manufactura) y distribución (logística) en el mismo bloque; "
                 "un bloque con más de 10 equipos obliga a una capa de dirección y suma una capa; el CEO no debe tener "
                 "más de 12 reportes directos. Llama a proponer_modelo con un modelo válido: te devuelve una vista "
                 "previa. Si la vista previa trae alertas, corrige y vuelve a proponer (máximo 2 veces). "
                 "Explica en 3 viñetas la lógica del diseño.",
    "optimizador": f"Eres el especialista en span & layers. {ESTILO} "
                   "Llama a disenar_organizacion con reglas de tramo por tipo de trabajo. Si el resultado trae "
                   "alertas (por ejemplo más de 7 capas), ajusta las reglas y vuelve a llamar (máximo 3 intentos). "
                   "Rangos razonables: operativo 12-15, comercial de campo 8-12, profesional 6-8, especialista 4-6, "
                   "gerencial 5-8, tramo_lider_bloque 6-8 (más de 8 el CHRO lo objeta). Si las capas de más vienen de "
                   "una capa de dirección en un bloque con muchos equipos, no fuerces los tramos: dilo claramente para "
                   "que el diseñador divida el bloque. Explica qué ajustaste y por qué.",
    "impacto": f"Eres el analista de impacto. {ESTILO} Calcula el impacto con tu herramienta y resume: "
               "posiciones de jefatura, capas, tramo promedio, ahorro anual y consolidaciones hacia plataformas.",
    "chro": f"Eres el CHRO de la empresa: exigente, con experiencia en plantas y fuerza de ventas, y escéptico de "
            f"los rediseños hechos en Excel. {ESTILO} Usa revisar_riesgos y agrega tu criterio. "
            "Criterios de la empresa: hasta 12 reportes directos para el CEO es aceptable en un modelo "
            "producto-plataforma; la diferencia entre personas de hoy y posiciones propuestas son jefaturas "
            "eliminadas, no personas sin asignar. Objeta (OBJETADO) solo por problemas que el equipo puede corregir "
            "ahora en el diseño. En la PRIMERA revisión eres especialmente exigente: si encuentras al menos un "
            "problema que el equipo puede corregir en el diseño (líderes de bloque con 2 reportes, bloques "
            "demasiado chicos, tramos al límite de lo seguro, un bloque que mezcla negocios distintos), objeta y "
            "pide el cambio concreto: es mejor corregirlo antes de que llegue al directorio. Lo que requiere datos de campo, "
            "validaciones con líderes o planes de transición va como condición de implementación en "
            "cambios_pedidos al aprobar. En una segunda revisión, aprueba si los riesgos altos se resolvieron. "
            "Antes de emitir el veredicto, escribe tus objeciones o condiciones en viñetas; luego llama SIEMPRE a "
            "emitir_veredicto.",
}

CAPS_NO_PRODUCTO = [c for c in motor.CAPACIDADES if c not in motor.CAPACIDADES_PRODUCTO]
_BLOQUE_CAPS = {"type": "object", "properties": {
    "nombre": {"type": "string"}, "descripcion": {"type": "string"},
    "capacidades": {"type": "array", "items": {"type": "string", "enum": CAPS_NO_PRODUCTO}}},
    "required": ["nombre", "capacidades"]}
ESQUEMA_MODELO = {"type": "object", "properties": {
    "productos": {"type": "array", "items": {"type": "object", "properties": {
        "nombre": {"type": "string"}, "descripcion": {"type": "string"},
        "categorias": {"type": "array", "items": {"type": "string", "enum": motor.CATEGORIAS}}},
        "required": ["nombre", "categorias"]}},
    "plataformas": {"type": "array", "items": _BLOQUE_CAPS},
    "habilitadores": {"type": "array", "items": _BLOQUE_CAPS}},
    "required": ["productos", "plataformas", "habilitadores"]}
ESQUEMA_REGLAS = {"type": "object", "properties": {
    "tramo_primera_linea": {"type": "object", "properties": {t: {"type": "integer"} for t in motor.TIPOS_TRABAJO}},
    "tramo_gerencial": {"type": "integer"}, "tramo_lider_bloque": {"type": "integer"},
    "justificacion": {"type": "string"}}}

HERRAMIENTAS = {
    "diagnostico": [{"name": "medir_span_and_layers", "description": "Mide capas, tramos, jefaturas y costo de la organización actual, con focos por área.", "input_schema": {"type": "object", "properties": {}}}],
    "capacidades": [{"name": "mapear_capacidades", "description": "Muestra cada capacidad, cuántas personas tiene y en qué áreas vive hoy; marca las duplicadas.", "input_schema": {"type": "object", "properties": {}}}],
    "disenador": [
        {"name": "validar_modelo", "description": "Valida un modelo producto-plataforma sin registrarlo. Devuelve errores de cobertura.", "input_schema": ESQUEMA_MODELO},
        {"name": "proponer_modelo", "description": "Registra el modelo producto-plataforma propuesto (debe ser válido). Cada capacidad no-producto va en exactamente un bloque; cada categoría en exactamente un producto.", "input_schema": ESQUEMA_MODELO}],
    "optimizador": [{"name": "disenar_organizacion", "description": "Construye el organigrama objetivo desde la base con el modelo registrado y estas reglas de tramo. Devuelve métricas, bloques y alertas.", "input_schema": ESQUEMA_REGLAS}],
    "impacto": [{"name": "calcular_impacto", "description": "Compara la organización actual con el diseño objetivo vigente.", "input_schema": {"type": "object", "properties": {}}}],
    "chro": [
        {"name": "revisar_riesgos", "description": "Chequeos de riesgo sobre el diseño objetivo vigente (tramos, capas, tamaño de bloques).", "input_schema": {"type": "object", "properties": {}}},
        {"name": "emitir_veredicto", "description": "Emite el veredicto final del CHRO.", "input_schema": {"type": "object", "properties": {
            "veredicto": {"type": "string", "enum": ["APROBADO", "OBJETADO"]},
            "objeciones": {"type": "array", "items": {"type": "string"}},
            "cambios_pedidos": {"type": "array", "items": {"type": "string"}}},
            "required": ["veredicto", "objeciones", "cambios_pedidos"]}}],
}

MODELO_RESPALDO = {
    "productos": [{"nombre": "Galletas", "categorias": ["Galletas"]},
                  {"nombre": "Pastas, Harinas y Salsas", "categorias": ["Pastas y Harinas", "Salsas y Condimentos"]},
                  {"nombre": "Bebidas", "categorias": ["Bebidas"]},
                  {"nombre": "Cuidado del Hogar", "categorias": ["Cuidado del Hogar"]}],
    "plataformas": [{"nombre": "Manufactura", "capacidades": ["manufactura", "mantenimiento", "calidad"]},
                    {"nombre": "Logística y Planeamiento", "capacidades": ["logistica", "compras", "planeamiento_suministro", "planeamiento_demanda"]},
                    {"nombre": "Go-to-Market", "capacidades": ["ventas_tradicional", "ventas_moderno", "trade_marketing"]},
                    {"nombre": "Datos, RGM y Digital", "capacidades": ["pricing_rgm", "analytics", "digital_ecommerce"]}],
    "habilitadores": [{"nombre": "Finanzas", "capacidades": ["finanzas"]}, {"nombre": "Gestión Humana", "capacidades": ["rrhh"]},
                      {"nombre": "Tecnología", "capacidades": ["ti"]}, {"nombre": "Legal y Asuntos Corporativos", "capacidades": ["legal"]}],
}


def _publico(diseno: dict) -> dict:
    return {k: v for k, v in diseno.items() if k != "_org"}


class Sesion:
    """Estado de trabajo compartido por los agentes durante una corrida."""

    def __init__(self, bus: Bus):
        self.bus = bus
        self.modelo: dict | None = None
        self.diseno: dict | None = None
        self.veredicto: dict | None = None

    async def ejecutar(self, agente: str, nombre: str, entrada: dict) -> dict:
        """Ejecuta una herramienta, publica sus datos en la interfaz y devuelve lo que ve el agente."""
        emit = self.bus.emit
        if nombre == "medir_span_and_layers":
            d = motor.diagnostico()
            await emit({"type": "data", "key": "asis", "value": d})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Midió {d["personas"]:,} personas: {d["capas"]} capas, tramo promedio {d["tramo_promedio"]}, {d["jefes_un_reporte"]} jefes con un solo reporte'})
            return {k: v for k, v in d.items() if k not in ("piramide",)}
        if nombre == "mapear_capacidades":
            d = motor.mapa_capacidades()
            await emit({"type": "data", "key": "capacidades", "value": d})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'{len(d["duplicadas"])} capacidades viven en más de un área'})
            return d
        if nombre == "validar_modelo":
            errores = motor.validar_modelo(entrada)
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": "Modelo válido" if not errores else f"Validación: {len(errores)} ajustes pendientes"})
            return {"valido": not errores, "errores": errores}
        if nombre == "proponer_modelo":
            errores = motor.validar_modelo(entrada)
            if errores:
                await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                            "summary": f"Modelo rechazado por validación ({len(errores)} errores)"})
                return {"registrado": False, "errores": errores}
            self.modelo = entrada
            await emit({"type": "data", "key": "modelo", "value": entrada})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Propuso {len(entrada["productos"])} productos, {len(entrada["plataformas"])} plataformas y {len(entrada["habilitadores"])} habilitadores'})
            previa = motor.disenar_org(entrada, None)  # vista previa con tramos estándar, para que el diseñador vea las consecuencias
            return {"registrado": True, "vista_previa_con_tramos_estandar": {
                "capas": previa["metricas"]["capas"], "reportes_del_ceo": previa["metricas"]["reportes_del_ceo"],
                "alertas": previa["alertas"],
                "bloques": [{k: b[k] for k in ("nombre", "tipo", "personas", "equipos", "capas")} for b in previa["bloques"]]}}
        if nombre == "disenar_organizacion":
            reglas = {k: v for k, v in entrada.items() if k not in ("justificacion", "capas_max")}
            r = motor.disenar_org(self.modelo or MODELO_RESPALDO, reglas)
            if not r["ok"]:
                return r
            self.diseno = r
            await emit({"type": "data", "key": "tobe", "value": _publico(r)})
            m = r["metricas"]
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Diseño: {m["capas"]} capas, {m["jefaturas"]} jefaturas, tramo promedio {m["tramo_promedio"]}' + (" ⚠ " + r["alertas"][0] if r["alertas"] else "")})
            return _publico(r)
        if nombre == "calcular_impacto":
            if not self.diseno:
                return {"error": "Todavía no hay diseño; primero debe correr el optimizador"}
            i = motor.impacto(self.diseno)
            await emit({"type": "data", "key": "impacto", "value": i})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'{i["posiciones_de_jefatura_menos"]} jefaturas menos, ahorro anual USD {i["ahorro_anual_musd"]} M'})
            return i
        if nombre == "revisar_riesgos":
            if not self.diseno:
                return {"error": "Todavía no hay diseño para revisar"}
            r = motor.revisar_riesgos(self.diseno)
            await emit({"type": "data", "key": "riesgos", "value": r})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'{len(r["hallazgos"])} riesgos detectados' if r["hallazgos"] else "Sin riesgos en los chequeos"})
            return {**r, "bloques": [{k: b[k] for k in ("nombre", "tipo", "personas", "reportes_del_lider", "capas")} for b in self.diseno["bloques"]],
                    "reglas": self.diseno["reglas"]}
        if nombre == "emitir_veredicto":
            entrada = {"veredicto": "APROBADO" if entrada.get("veredicto") == "APROBADO" else "OBJETADO",
                       "objeciones": [str(x) for x in entrada.get("objeciones") or []],
                       "cambios_pedidos": [str(x) for x in entrada.get("cambios_pedidos") or []]}
            self.veredicto = entrada
            await emit({"type": "data", "key": "veredicto", "value": entrada})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Veredicto del CHRO: {entrada["veredicto"]}'})
            return {"ok": True}
        return {"error": f"herramienta desconocida {nombre}"}


# =========================================================================== modo en vivo
async def _agente_vivo(cliente, sesion: Sesion, agente: str, mensaje: str, ronda: int = 1, max_turnos: int = 6) -> str:
    emit = sesion.bus.emit
    await emit({"type": "agent_status", "agent": agente, "status": "pensando", "ronda": ronda})
    mensajes = [{"role": "user", "content": mensaje}]
    texto_final = ""
    for _ in range(max_turnos):
        async with cliente.messages.stream(
            model=MODELO_CHRO if agente == "chro" else MODELO, max_tokens=1600, system=PROMPTS[agente],
            tools=HERRAMIENTAS[agente], messages=mensajes,
        ) as stream:
            async for delta in stream.text_stream:
                await emit({"type": "agent_text", "agent": agente, "delta": delta})
                texto_final += delta
            final = await stream.get_final_message()
        mensajes.append({"role": "assistant", "content": final.content})
        usos = [b for b in final.content if b.type == "tool_use"]
        if not usos:
            break
        await emit({"type": "agent_status", "agent": agente, "status": "trabajando"})
        resultados = []
        for u in usos:
            try:
                res, err = await sesion.ejecutar(agente, u.name, u.input if isinstance(u.input, dict) else {}), False
            except Exception as e:  # noqa: BLE001 — un error de herramienta no debe tumbar la corrida
                res, err = {"error": f"{type(e).__name__}: {e}. Revisa el formato y vuelve a intentar."}, True
            resultados.append({"type": "tool_result", "tool_use_id": u.id, "is_error": err,
                               "content": json.dumps(res, ensure_ascii=False, default=str)[:12000]})
        await emit({"type": "agent_text", "agent": agente, "delta": "\n"})
        mensajes.append({"role": "user", "content": resultados})
        await emit({"type": "agent_status", "agent": agente, "status": "pensando"})
    await emit({"type": "agent_status", "agent": agente, "status": "listo"})
    return texto_final


async def correr_vivo(bus: Bus) -> None:
    from anthropic import AsyncAnthropic

    cliente = AsyncAnthropic(timeout=90, max_retries=2)
    s = Sesion(bus)
    emit = bus.emit
    terminada_bien = False
    paralelas: list[asyncio.Task] = []
    await emit({"type": "run_start", "modo": "vivo"})
    try:
        await emit({"type": "phase", "name": "Ronda 1 · Diagnóstico y mapa de capacidades"})
        paralelas = [
            asyncio.create_task(_agente_vivo(cliente, s, "diagnostico", f"{CASO}\n\nHaz el diagnóstico de span & layers.")),
            asyncio.create_task(_agente_vivo(cliente, s, "capacidades", f"{CASO}\n\nMapea las capacidades y sus duplicaciones.")),
        ]
        diag, caps = await asyncio.gather(*paralelas)
        objeciones = ""
        for ronda in (1, 2):
            if ronda == 2:
                await emit({"type": "phase", "name": "Ronda 2 · El equipo atiende las objeciones del CHRO"})
            else:
                await emit({"type": "phase", "name": "Diseño del modelo producto-plataforma"})
            msg = f"{CASO}\n\nDiagnóstico:\n{diag}\n\nCapacidades:\n{caps}"
            if ronda == 2:
                msg += (f"\n\nModelo anterior:\n{json.dumps(s.modelo, ensure_ascii=False)}\n\n"
                        f"El CHRO objetó el diseño:\n{objeciones}\nCorrige el modelo atendiendo sus pedidos.")
            await _agente_vivo(cliente, s, "disenador", msg, ronda)
            if s.modelo is None:
                s.modelo = MODELO_RESPALDO
                await emit({"type": "data", "key": "modelo", "value": MODELO_RESPALDO})
            await emit({"type": "phase", "name": "Span & layers: diseñando las jefaturas desde la base"})
            msg = f"{CASO}\n\nModelo registrado:\n{json.dumps(s.modelo, ensure_ascii=False)}"
            if ronda == 2 and s.diseno:
                msg += f"\n\nReglas anteriores: {json.dumps(s.diseno['reglas'])}\nObjeciones del CHRO:\n{objeciones}"
            s.diseno = None  # cada ronda parte de un diseño nuevo
            await _agente_vivo(cliente, s, "optimizador", msg, ronda)
            if s.diseno is None or s.diseno.get("metricas") is None:
                await s.ejecutar("optimizador", "disenar_organizacion", {})
            await emit({"type": "phase", "name": "Calculando el impacto"})
            await _agente_vivo(cliente, s, "impacto", f"{CASO}\n\nCalcula y resume el impacto del diseño vigente.", ronda)
            await emit({"type": "phase", "name": "Revisión del CHRO"})
            s.veredicto = None
            extra = "" if ronda == 1 else f"\n\nEsta es la SEGUNDA revisión. Tus objeciones anteriores fueron:\n{objeciones}"
            await _agente_vivo(cliente, s, "chro", f"{CASO}\n\nRevisa el diseño vigente.{extra}", ronda)
            if not s.veredicto or s.veredicto["veredicto"] == "APROBADO" or ronda == 2:
                break
            objeciones = "\n".join(f"- {o}" for o in s.veredicto["objeciones"] + s.veredicto["cambios_pedidos"])
        ok = s.veredicto and s.veredicto["veredicto"] == "APROBADO"
        await emit({"type": "run_end", "fase": "Diseño aprobado por el CHRO" if ok else "Diseño listo con observaciones"})
        terminada_bien = True
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001
        await emit({"type": "phase", "name": f"Error de conexión con la IA ({type(e).__name__}). Usa el guion de respaldo."})
        await emit({"type": "run_end", "estado": "error", "fase": "Error: cambia al guion de respaldo"})
        raise
    finally:
        for t in paralelas:  # que ningún agente siga escribiendo en la pantalla tras un error o un reinicio
            t.cancel()
        if terminada_bien:
            bus.guardar_grabacion(os.path.join(RAIZ, "runs"))


# =========================================================================== modo guion (plan B)
async def _pausa(seg: float) -> None:
    await asyncio.sleep(seg / VELOCIDAD)


async def _escribir(bus: Bus, agente: str, texto: str) -> None:
    for i in range(0, len(texto), 3):
        await bus.emit({"type": "agent_text", "agent": agente, "delta": texto[i:i + 3]})
        await _pausa(0.045)


async def _guion_agente(s: Sesion, agente: str, antes: str, herramientas: list, despues, ronda: int = 1) -> None:
    emit = s.bus.emit
    await emit({"type": "agent_status", "agent": agente, "status": "pensando", "ronda": ronda})
    await _pausa(4.0)
    await _escribir(s.bus, agente, antes)
    resultados = []
    for nombre, entrada in herramientas:
        await emit({"type": "agent_status", "agent": agente, "status": "trabajando"})
        await _pausa(3.5)
        resultados.append(await s.ejecutar(agente, nombre, entrada))
        await emit({"type": "agent_text", "agent": agente, "delta": "\n"})
    await emit({"type": "agent_status", "agent": agente, "status": "pensando"})
    await _pausa(3.0)
    await _escribir(s.bus, agente, despues(*resultados) if callable(despues) else despues)
    await emit({"type": "agent_status", "agent": agente, "status": "listo"})


def _f(n: float) -> str:
    return f"{n:,.1f}" if isinstance(n, float) else f"{n:,}"


async def correr_guion(bus: Bus) -> None:
    s = Sesion(bus)
    emit = bus.emit
    await emit({"type": "run_start", "modo": "guion"})
    await emit({"type": "phase", "name": "Ronda 1 · Diagnóstico y mapa de capacidades"})

    def post_diag(d):
        peor = d["focos_por_area"][0]
        return (f"• {d['capas']} capas entre el CEO y la primera línea. El objetivo es 7.\n"
                f"• Tramo promedio de {d['tramo_promedio']}; el {d['pct_jefes_tramo_bajo']}% de los jefes tiene 3 reportes o menos.\n"
                f"• {d['jefes_un_reporte']} jefes con un solo reporte. Ejemplo: {d['ejemplos_cadenas_un_reporte'][0]}.\n"
                f"• {d['jefaturas']} jefaturas ({d['pct_jefaturas']}% de la gente) cuestan USD {d['costo_jefaturas_musd']} M al año.\n"
                f"• Foco más crítico: {peor['area']}, con tramo promedio de {peor['tramo_promedio']}.")

    def post_caps(c):
        dup = [x for x in c["capacidades"] if x["duplicada"] and x["capacidad"] not in motor.CAPACIDADES_PRODUCTO]
        lineas = "\n".join(f"• {x['nombre']}: {x['personas']} personas repartidas en {len(x['areas'])} áreas."
                           for x in dup[:5])
        return (f"{lineas}\n• Cada unidad de negocio arma su propio pricing, analytics y e-commerce con 3-8 personas: "
                f"equipos subescala con jefe propio.\n• Candidatas a plataforma: Pricing y RGM, Analytics, Digital, "
                f"Planeamiento de demanda y Canal moderno.")

    await asyncio.gather(
        _guion_agente(s, "diagnostico", "Voy a medir capas, tramos y jefaturas de las 3,744 personas.\n",
                      [("medir_span_and_layers", {})], post_diag),
        _guion_agente(s, "capacidades", "Voy a mapear dónde vive hoy cada capacidad y qué está duplicado.\n",
                      [("mapear_capacidades", {})], post_caps),
    )

    # ---------------- Ronda 1: diseño
    await emit({"type": "phase", "name": "Diseño del modelo producto-plataforma"})
    modelo1 = json.loads(json.dumps(MODELO_RESPALDO))
    modelo1["plataformas"] = [
        {"nombre": "Supply Chain", "descripcion": "Plantas, logística, compras y planeamiento integrado",
         "capacidades": ["manufactura", "mantenimiento", "calidad", "logistica", "compras", "planeamiento_suministro", "planeamiento_demanda"]},
        {"nombre": "Go-to-Market", "descripcion": "Canal tradicional, canal moderno y trade marketing",
         "capacidades": ["ventas_tradicional", "ventas_moderno", "trade_marketing"]},
        {"nombre": "RGM y Analytics", "descripcion": "Pricing, promociones e inteligencia comercial",
         "capacidades": ["pricing_rgm", "analytics"]},
        {"nombre": "Comercio Digital", "descripcion": "E-commerce y canales digitales", "capacidades": ["digital_ecommerce"]},
    ]
    await _guion_agente(
        s, "disenador",
        "Diseño 4 equipos de producto por categoría, con marketing, innovación y category management dentro. "
        "Todo lo duplicado pasa a plataformas compartidas.\n",
        [("validar_modelo", modelo1), ("proponer_modelo", modelo1)],
        "• Producto: Galletas; Pastas, Harinas y Salsas; Bebidas; Cuidado del Hogar. Cada uno dueño de su categoría.\n"
        "• Plataformas: Supply Chain, Go-to-Market, RGM y Analytics, Comercio Digital. Sirven a todos los productos.\n"
        "• Habilitadores: Finanzas, Gestión Humana, Tecnología y Legal.")

    # ---------------- Ronda 1: span & layers (dos intentos visibles)
    await emit({"type": "phase", "name": "Span & layers: diseñando las jefaturas desde la base"})
    s.modelo = modelo1

    def post_opt1(r1, r2):
        m1, m2 = r1["metricas"], r2["metricas"]
        return (f"• Primer intento con tramos estándar: {m1['capas']} capas. Supply Chain se pasa del máximo.\n"
                f"• Subí el tramo de supervisores de planta a 18 operarios y el gerencial a 8.\n"
                f"• Resultado: {m2['capas']} capas, {m2['jefaturas']} jefaturas, tramo promedio {m2['tramo_promedio']}.\n"
                f"• Cero jefes con un solo reporte.")
    await _guion_agente(
        s, "optimizador", "Primero corro el diseño con los tramos estándar por tipo de trabajo.\n",
        [("disenar_organizacion", {}),
         ("disenar_organizacion", {"tramo_primera_linea": {"operativo": 18}, "tramo_gerencial": 8})],
        post_opt1)

    await emit({"type": "phase", "name": "Calculando el impacto"})

    def post_imp(i):
        a, d = i["antes"], i["despues"]
        return (f"• Capas: {a['capas']} → {d['capas']}. Tramo promedio: {a['tramo_promedio']} → {d['tramo_promedio']}.\n"
                f"• {i['posiciones_de_jefatura_menos']} posiciones de jefatura menos.\n"
                f"• Ahorro anual estimado: USD {i['ahorro_anual_musd']} M ({i['ahorro_pct_costo_total']}% del costo de personal).\n"
                f"• {i['personas_de_unidades_a_plataformas']} personas pasan de las unidades de negocio a plataformas compartidas.")
    await _guion_agente(s, "impacto", "Comparo el diseño vigente contra la organización actual.\n",
                        [("calcular_impacto", {})], post_imp)

    await emit({"type": "phase", "name": "Revisión del CHRO"})
    v1 = {"veredicto": "OBJETADO",
          "objeciones": ["18 operarios por supervisor compromete la seguridad en planta; no lo firmo.",
                         "Supply Chain junta plantas y distribución bajo un solo líder con más de 2,400 personas.",
                         "Comercio Digital, con 9 personas, no justifica un líder que reporte al CEO."],
          "cambios_pedidos": ["Volver a máximo 15 operarios por supervisor.",
                              "Separar Manufactura de Logística y Planeamiento.",
                              "Fusionar Digital con RGM y Analytics en una sola plataforma de datos comerciales."]}

    def post_chro1(r, _):
        return ("No lo firmo todavía.\n" + "\n".join(f"• {o}" for o in v1["objeciones"]) +
                "\nPido: " + " ".join(v1["cambios_pedidos"]))
    await _guion_agente(s, "chro", "Reviso los riesgos del diseño antes de que llegue al directorio.\n",
                        [("revisar_riesgos", {}), ("emitir_veredicto", v1)], post_chro1)

    # ---------------- Ronda 2
    await emit({"type": "phase", "name": "Ronda 2 · El equipo atiende las objeciones del CHRO"})
    modelo2 = json.loads(json.dumps(MODELO_RESPALDO))
    await _guion_agente(
        s, "disenador", "Atiendo al CHRO: separo plantas de distribución y consolido los datos comerciales.\n",
        [("proponer_modelo", modelo2)],
        "• Manufactura (plantas, mantenimiento y calidad) queda separada de Logística y Planeamiento.\n"
        "• Datos, RGM y Digital: una sola plataforma comercial con escala real.\n"
        "• Los 4 equipos de producto no cambian.", ronda=2)
    s.modelo = modelo2
    await emit({"type": "phase", "name": "Span & layers: diseñando las jefaturas desde la base"})

    def post_opt2(r):
        m = r["metricas"]
        return (f"• Vuelvo a 15 operarios por supervisor, como pidió el CHRO.\n"
                f"• Al separar Manufactura ya no hace falta una capa de dirección: {m['capas']} capas.\n"
                f"• {m['jefaturas']} jefaturas y tramo promedio de {m['tramo_promedio']}.")
    await _guion_agente(s, "optimizador", "Rediseño con 15 operarios por supervisor y el nuevo modelo.\n",
                        [("disenar_organizacion", {"tramo_gerencial": 8})], post_opt2, ronda=2)
    await emit({"type": "phase", "name": "Calculando el impacto"})
    await _guion_agente(s, "impacto", "Recalculo el impacto con el diseño corregido.\n",
                        [("calcular_impacto", {})], post_imp, ronda=2)
    await emit({"type": "phase", "name": "Revisión del CHRO"})
    v2 = {"veredicto": "APROBADO",
          "objeciones": [],
          "cambios_pedidos": ["Definir con cada planta el plan de transición de líderes de grupo a supervisores.",
                              "Acordar los niveles de servicio entre productos y plataformas antes del lanzamiento."]}

    def post_chro2(r, _):
        return ("Ahora sí lo firmo. La seguridad en planta está cubierta y cada plataforma tiene escala.\n"
                "Condiciones para implementar:\n" + "\n".join(f"• {c}" for c in v2["cambios_pedidos"]))
    await _guion_agente(s, "chro", "Segunda revisión.\n", [("revisar_riesgos", {}), ("emitir_veredicto", v2)],
                        post_chro2, ronda=2)
    await emit({"type": "run_end", "fase": "Diseño aprobado por el CHRO"})


# =========================================================================== modo grabación
def _grabacion_completa(ruta: str) -> bool:
    try:
        with open(ruta, encoding="utf-8") as f:
            tipos = [json.loads(l).get("type") for l in f if l.strip()]
    except (OSError, ValueError):
        return False
    return bool(tipos) and tipos[0] == "run_start" and tipos[-1] == "run_end"


def ultima_grabacion() -> str | None:
    archivos = [a for a in sorted(glob.glob(os.path.join(RAIZ, "runs", "*.jsonl"))) if _grabacion_completa(a)]
    return archivos[-1] if archivos else None


async def correr_grabacion(bus: Bus) -> None:
    ruta = ultima_grabacion()
    if not ruta:
        await correr_guion(bus)
        return
    with open(ruta, encoding="utf-8") as f:
        eventos = [json.loads(l) for l in f if l.strip()]
    previo = eventos[0]["ts"]
    for ev in eventos:
        espera = min(ev["ts"] - previo, 4.0)
        previo = ev["ts"]
        if espera > 0:
            await asyncio.sleep(espera)  # ritmo original, sin el factor del guion
        ev = {k: v for k, v in ev.items() if k != "ts"}
        if ev["type"] == "run_start":
            ev["modo"] = "grabacion"
        await bus.emit(ev)
