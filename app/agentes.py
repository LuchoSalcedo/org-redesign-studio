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

from app import empresas, motor
from app.bus import Bus
from app.empresas import Empresa

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELO = os.environ.get("ORG_MODEL", "claude-sonnet-5-5")
MODELO_CHRO = os.environ.get("ORG_MODEL_CHRO", MODELO)
VELOCIDAD = float(os.environ.get("VELOCIDAD_GUION", "0.65"))  # 0.65 ≈ 4 minutos; >1 = más rápido

ESTILO = (
    "Escribes en español para 50 gerentes que leen tu texto proyectado en vivo. Frases cortas. "
    "Antes de usar una herramienta, di en una línea qué vas a hacer. Después de los resultados, da "
    "máximo 5 viñetas con números concretos. Nada de introducciones ni despedidas. Nunca inventes cifras: "
    "usa solo las que devuelven las herramientas. Texto plano: viñetas con '•' y sin markdown (sin asteriscos "
    "ni títulos con #). Nunca comentes sobre las herramientas, las llamadas o el "
    "sistema: si algo falla, corrígelo sin mencionarlo."
)


def caso(e: Empresa) -> str:
    return e.caso.format(personas=len(motor.cargar_asis(e)))


def prompts(e: Empresa) -> dict:
    return {
        "diagnostico": f"Eres el analista de diagnóstico organizacional del equipo. {ESTILO} "
                       "Mide span & layers con tu herramienta y explica los 4 problemas más importantes "
                       "(capas, tramos bajos, jefes de un solo reporte, áreas críticas).",
        "capacidades": f"Eres el analista de capacidades del equipo. {ESTILO} "
                       "Usa tu herramienta para ver dónde vive cada capacidad hoy. Señala cuáles están duplicadas "
                       "entre unidades de negocio y cuáles deberían ser plataformas compartidas.",
        "disenador": f"Eres el diseñador del modelo producto-plataforma. {ESTILO} "
                     f"Productos = {e.productos_txt}. "
                     f"Plataformas = capacidades compartidas que sirven a todos los productos ({e.plataformas_txt}). "
                     f"Habilitadores = {e.habilitadores_txt}. "
                     f"Reglas de diseño: {e.regla_separar}; "
                     "un bloque con más de 10 equipos obliga a una capa de dirección y suma una capa; un líder de "
                     "bloque con más de 8 equipos es demasiado; el CEO no debe tener más de 12 reportes directos. "
                     "Llama a proponer_modelo con un modelo válido: te devuelve una "
                     "vista previa. Si la vista previa trae alertas, corrige y vuelve a proponer (máximo 2 veces). "
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
        "chro": f"Eres el CHRO de la empresa: exigente, {e.chro_perfil}, y escéptico de "
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


def _esquema_modelo(e: Empresa) -> dict:
    no_producto = [c for c in e.capacidades if c not in e.cap_producto]
    bloque = {"type": "object", "properties": {
        "nombre": {"type": "string"}, "descripcion": {"type": "string"},
        "capacidades": {"type": "array", "items": {"type": "string", "enum": no_producto}}},
        "required": ["nombre", "capacidades"]}
    return {"type": "object", "properties": {
        "productos": {"type": "array", "items": {"type": "object", "properties": {
            "nombre": {"type": "string"}, "descripcion": {"type": "string"},
            "categorias": {"type": "array", "items": {"type": "string", "enum": e.categorias}}},
            "required": ["nombre", "categorias"]}},
        "plataformas": {"type": "array", "items": bloque},
        "habilitadores": {"type": "array", "items": bloque}},
        "required": ["productos", "plataformas", "habilitadores"]}


ESQUEMA_REGLAS = {"type": "object", "properties": {
    "tramo_primera_linea": {"type": "object", "properties": {t: {"type": "integer"} for t in motor.TIPOS_TRABAJO}},
    "tramo_gerencial": {"type": "integer"}, "tramo_lider_bloque": {"type": "integer"},
    "justificacion": {"type": "string"}}}


def herramientas(e: Empresa) -> dict:
    modelo = _esquema_modelo(e)
    return {
        "diagnostico": [{"name": "medir_span_and_layers", "description": "Mide capas, tramos, jefaturas y costo de la organización actual, con focos por área.", "input_schema": {"type": "object", "properties": {}}}],
        "capacidades": [{"name": "mapear_capacidades", "description": "Muestra cada capacidad, cuántas personas tiene y en qué áreas vive hoy; marca las duplicadas.", "input_schema": {"type": "object", "properties": {}}}],
        "disenador": [
            {"name": "validar_modelo", "description": "Valida un modelo producto-plataforma sin registrarlo. Devuelve errores de cobertura.", "input_schema": modelo},
            {"name": "proponer_modelo", "description": f"Registra el modelo producto-plataforma propuesto (debe ser válido). Cada capacidad no-producto va en exactamente un bloque; cada {e.etiqueta_categoria} en exactamente un producto.", "input_schema": modelo}],
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


def _publico(diseno: dict) -> dict:
    return {k: v for k, v in diseno.items() if k != "_org"}


class Sesion:
    """Estado de trabajo compartido por los agentes durante una corrida."""

    def __init__(self, bus: Bus, e: Empresa):
        self.bus = bus
        self.e = e
        self.modelo: dict | None = None
        self.diseno: dict | None = None
        self.veredicto: dict | None = None

    async def ejecutar(self, agente: str, nombre: str, entrada: dict) -> dict:
        """Ejecuta una herramienta, publica sus datos en la interfaz y devuelve lo que ve el agente."""
        emit, e = self.bus.emit, self.e
        if nombre == "medir_span_and_layers":
            d = motor.diagnostico(e)
            await emit({"type": "data", "key": "asis", "value": d})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Midió {d["personas"]:,} personas: {d["capas"]} capas, tramo promedio {d["tramo_promedio"]}, {d["jefes_un_reporte"]} jefes con un solo reporte'})
            return {k: v for k, v in d.items() if k not in ("piramide",)}
        if nombre == "mapear_capacidades":
            d = motor.mapa_capacidades(e)
            await emit({"type": "data", "key": "capacidades", "value": d})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'{len(d["duplicadas"])} capacidades viven en más de un área'})
            return d
        if nombre == "validar_modelo":
            errores = motor.validar_modelo(e, entrada)
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": "Modelo válido" if not errores else f"Validación: {len(errores)} ajustes pendientes"})
            return {"valido": not errores, "errores": errores}
        if nombre == "proponer_modelo":
            errores = motor.validar_modelo(e, entrada)
            if errores:
                await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                            "summary": f"Modelo rechazado por validación ({len(errores)} errores)"})
                return {"registrado": False, "errores": errores}
            self.modelo = entrada
            await emit({"type": "data", "key": "modelo", "value": entrada})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Propuso {len(entrada["productos"])} productos, {len(entrada["plataformas"])} plataformas y {len(entrada["habilitadores"])} habilitadores'})
            previa = motor.disenar_org(e, entrada, None)  # vista previa con tramos estándar, para que el diseñador vea las consecuencias
            return {"registrado": True, "vista_previa_con_tramos_estandar": {
                "capas": previa["metricas"]["capas"], "reportes_del_ceo": previa["metricas"]["reportes_del_ceo"],
                "alertas": previa["alertas"],
                "bloques": [{k: b[k] for k in ("nombre", "tipo", "personas", "equipos", "capas")} for b in previa["bloques"]]}}
        if nombre == "disenar_organizacion":
            reglas = {k: v for k, v in entrada.items() if k not in ("justificacion", "capas_max")}
            r = motor.disenar_org(e, self.modelo or e.modelo_respaldo, reglas)
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
            i = motor.impacto(e, self.diseno)
            await emit({"type": "data", "key": "impacto", "value": i})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'{i["posiciones_de_jefatura_menos"]} jefaturas menos, ahorro anual USD {i["ahorro_anual_musd"]} M'})
            return i
        if nombre == "revisar_riesgos":
            if not self.diseno:
                return {"error": "Todavía no hay diseño para revisar"}
            r = motor.revisar_riesgos(e, self.diseno)
            await emit({"type": "data", "key": "riesgos", "value": r})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'{len(r["hallazgos"])} riesgos detectados' if r["hallazgos"] else "Sin riesgos en los chequeos"})
            return {**r, "bloques": [{k: b[k] for k in ("nombre", "tipo", "personas", "reportes_del_lider", "capas")} for b in self.diseno["bloques"]],
                    "reglas": self.diseno["reglas"]}
        if nombre == "emitir_veredicto":
            lista = lambda v: [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])
            entrada = {"veredicto": "APROBADO" if entrada.get("veredicto") == "APROBADO" else "OBJETADO",
                       "objeciones": lista(entrada.get("objeciones")),
                       "cambios_pedidos": lista(entrada.get("cambios_pedidos"))}
            if entrada["veredicto"] == "OBJETADO" and not entrada["objeciones"]:
                return {"error": "Un veredicto OBJETADO necesita al menos una objeción en 'objeciones'. "
                                 "Vuelve a llamar con las objeciones y los cambios pedidos."}
            self.veredicto = entrada
            await emit({"type": "data", "key": "veredicto", "value": entrada})
            await emit({"type": "agent_tool", "agent": agente, "tool": nombre,
                        "summary": f'Veredicto del CHRO: {entrada["veredicto"]}'})
            return {"ok": True}
        return {"error": f"herramienta desconocida {nombre}"}


# =========================================================================== modo en vivo
# Herramienta que cada agente DEBE llamar con éxito antes de terminar; si no lo hace, se le recuerda.
OBLIGATORIA = {"diagnostico": "medir_span_and_layers", "capacidades": "mapear_capacidades",
               "disenador": "proponer_modelo", "optimizador": "disenar_organizacion",
               "impacto": "calcular_impacto", "chro": "emitir_veredicto"}


async def _agente_vivo(cliente, sesion: Sesion, agente: str, mensaje: str, ronda: int = 1, max_turnos: int = 8) -> str:
    emit = sesion.bus.emit
    sistema, tools = prompts(sesion.e)[agente], herramientas(sesion.e)[agente]
    await emit({"type": "agent_status", "agent": agente, "status": "pensando", "ronda": ronda})
    mensajes = [{"role": "user", "content": mensaje}]
    texto_final = ""
    cumplio, recordatorios = False, 0
    for _ in range(max_turnos):
        async with cliente.messages.stream(
            model=MODELO_CHRO if agente == "chro" else MODELO, max_tokens=8000, system=sistema,
            tools=tools, messages=mensajes,
        ) as stream:
            async for delta in stream.text_stream:
                await emit({"type": "agent_text", "agent": agente, "delta": delta})
                texto_final += delta
            final = await stream.get_final_message()
        if final.content:
            mensajes.append({"role": "assistant", "content": final.content})
        usos = [b for b in final.content if b.type == "tool_use"]
        if not usos:
            if cumplio or recordatorios >= 2:
                break
            # terminó sin hacer su trabajo (respuesta vacía o cortada): se le pide que lo haga
            recordatorios += 1
            if not final.content:
                mensajes.append({"role": "assistant", "content": "(sin respuesta)"})
            mensajes.append({"role": "user", "content": f"Todavía no completas tu trabajo. Llama ahora a "
                                                        f"{OBLIGATORIA[agente]} y después resume en viñetas."})
            continue
        await emit({"type": "agent_status", "agent": agente, "status": "trabajando"})
        resultados = []
        for u in usos:
            try:
                res, err = await sesion.ejecutar(agente, u.name, u.input if isinstance(u.input, dict) else {}), False
            except Exception as e:  # noqa: BLE001 — un error de herramienta no debe tumbar la corrida
                res, err = {"error": f"{type(e).__name__}: {e}. Revisa el formato y vuelve a intentar."}, True
            if (u.name == OBLIGATORIA[agente] and not err and isinstance(res, dict)
                    and not res.get("error") and res.get("registrado", True) and res.get("ok", True) is not False):
                cumplio = True
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
    e = empresas.get(bus.estado.get("empresa"))
    s = Sesion(bus, e)
    CASO = caso(e)
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
                s.modelo = e.modelo_respaldo
                await emit({"type": "data", "key": "modelo", "value": e.modelo_respaldo})
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
            bus.guardar_grabacion(os.path.join(RAIZ, "runs"), prefijo=e.id)


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


def _lista(nombres: list[str]) -> str:
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _bloque_con(modelo: dict, capacidad: str) -> str:
    return next(b["nombre"] for c in ("plataformas", "habilitadores") for b in modelo[c] if capacidad in b["capacidades"])


async def correr_guion(bus: Bus) -> None:
    """Plan B sin IA: mismo flujo, cálculos reales del motor y textos armados con esos números."""
    e = empresas.get(bus.estado.get("empresa"))
    g = e.guion
    s = Sesion(bus, e)
    emit = bus.emit
    personas = len(motor.cargar_asis(e))
    await emit({"type": "run_start", "modo": "guion"})
    await emit({"type": "phase", "name": "Ronda 1 · Diagnóstico y mapa de capacidades"})

    def post_diag(d):
        grandes = [f for f in d["focos_por_area"] if f["personas"] >= 100] or d["focos_por_area"]
        peor = min(grandes, key=lambda f: f["tramo_promedio"])
        return (f"• {d['capas']} capas entre el CEO y la primera línea. El objetivo es 7.\n"
                f"• Tramo promedio de {d['tramo_promedio']}; el {d['pct_jefes_tramo_bajo']}% de los jefes tiene 3 reportes o menos.\n"
                f"• {d['jefes_un_reporte']} jefes con un solo reporte. Ejemplo: {d['ejemplos_cadenas_un_reporte'][0]}.\n"
                f"• {d['jefaturas']} jefaturas ({d['pct_jefaturas']}% de la gente) cuestan USD {d['costo_jefaturas_musd']} M al año.\n"
                f"• Foco más crítico: {peor['area']}, con tramo promedio de {peor['tramo_promedio']}.")

    def post_caps(c):
        dup = [x for x in c["capacidades"] if x["duplicada"] and x["capacidad"] not in e.cap_producto]
        lineas = "\n".join(f"• {x['nombre']}: {x['personas']} personas repartidas en {len(x['areas'])} áreas."
                           for x in dup[:5])
        solo_unidades = [x["nombre"] for x in dup if all(e.es_unidad(a) for a in x["areas"])]
        def breve(n):
            n = n.split(" (")[0].lower()
            return n if len(n.split()) <= 3 else n.split(" e ")[0].split(" y ")[0]
        corto = [breve(n) for n in solo_unidades[:3]]
        return (f"{lineas}\n• Cada unidad de negocio arma por su cuenta {_lista(corto)}, "
                f"con equipos chicos y jefe propio.\n• Candidatas a plataforma: {_lista(solo_unidades)}.")

    await asyncio.gather(
        _guion_agente(s, "diagnostico", f"Voy a medir capas, tramos y jefaturas de las {personas:,} personas.\n",
                      [("medir_span_and_layers", {})], post_diag),
        _guion_agente(s, "capacidades", "Voy a mapear dónde vive hoy cada capacidad y qué está duplicado.\n",
                      [("mapear_capacidades", {})], post_caps),
    )

    # ---------------- Ronda 1: diseño (junta lo que no debe ir junto y deja una plataforma chica)
    await emit({"type": "phase", "name": "Diseño del modelo producto-plataforma"})
    modelo1 = json.loads(json.dumps(e.modelo_respaldo))
    modelo1["plataformas"] = json.loads(json.dumps(g["plataformas_r1"]))
    modelo2 = json.loads(json.dumps(e.modelo_respaldo))
    cap_a, cap_b, desc_par = e.pares_incompatibles[0]
    mezcla = _bloque_con(modelo1, cap_a)
    chica = modelo1["plataformas"][-1]
    destino = _bloque_con(modelo2, chica["capacidades"][0])
    prod_caps = _lista([e.capacidades[c].lower() for c in sorted(e.cap_producto)])

    def nombres(m, k):
        return [b["nombre"] for b in m[k]]
    await _guion_agente(
        s, "disenador",
        f"Diseño {len(modelo1['productos'])} equipos de producto por {e.etiqueta_categoria}, con {prod_caps} dentro. "
        "Todo lo duplicado pasa a plataformas compartidas.\n",
        [("validar_modelo", modelo1), ("proponer_modelo", modelo1)],
        f"• Producto: {'; '.join(nombres(modelo1, 'productos'))}. Cada uno dueño de su {e.etiqueta_categoria}.\n"
        f"• Plataformas: {_lista(nombres(modelo1, 'plataformas'))}. Sirven a todos los productos.\n"
        f"• Habilitadores: {_lista(nombres(modelo1, 'habilitadores'))}.")

    # ---------------- Ronda 1: span & layers (dos intentos visibles)
    await emit({"type": "phase", "name": "Span & layers: diseñando las jefaturas desde la base"})
    s.modelo = modelo1

    def post_opt1(r1, r2):
        m1, m2 = r1["metricas"], r2["metricas"]
        uno = "Cero jefes" if not m2["jefes_un_reporte"] else f"{m2['jefes_un_reporte']} jefes"
        return (f"• Primer intento con tramos estándar: {m1['capas']} capas. {mezcla} se pasa del máximo.\n"
                f"• Subí el tramo de primera línea operativa a 18 {g['per_op']} y el gerencial a 8.\n"
                f"• Resultado: {m2['capas']} capas, {m2['jefaturas']} jefaturas, tramo promedio {m2['tramo_promedio']}.\n"
                f"• {uno} con un solo reporte.")
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
    tam = {b["nombre"]: b["personas"] for b in s.diseno["bloques"]}
    v1 = {"veredicto": "OBJETADO",
          "objeciones": [f"18 {g['per_op']} por supervisor {g['riesgo_corto']}; no lo firmo.",
                         f"{mezcla} junta {desc_par} bajo un solo líder con más de {tam[mezcla] // 100 * 100:,} personas.",
                         f"{chica['nombre']}, con {tam[chica['nombre']]} personas, no justifica un líder que reporte al CEO."],
          "cambios_pedidos": [f"Volver a máximo 15 {g['per_op']} por supervisor.",
                              f"Separar {_bloque_con(modelo2, cap_a)} de {_bloque_con(modelo2, cap_b)}.",
                              f"Integrar {chica['nombre']} en una plataforma más grande: {destino}."]}

    def post_chro1(r, _):
        return ("No lo firmo todavía.\n" + "\n".join(f"• {o}" for o in v1["objeciones"]) +
                "\nPido: " + " ".join(v1["cambios_pedidos"]))
    await _guion_agente(s, "chro", "Reviso los riesgos del diseño antes de que llegue al directorio.\n",
                        [("revisar_riesgos", {}), ("emitir_veredicto", v1)], post_chro1)

    # ---------------- Ronda 2
    await emit({"type": "phase", "name": "Ronda 2 · El equipo atiende las objeciones del CHRO"})
    await _guion_agente(
        s, "disenador", f"Atiendo al CHRO: separo {g['separar']} y llevo {chica['nombre']} a {destino}.\n",
        [("proponer_modelo", modelo2)],
        f"• {_bloque_con(modelo2, cap_a)} queda separada de {_bloque_con(modelo2, cap_b)}.\n"
        f"• {destino}: una sola plataforma con escala real.\n"
        f"• Los {len(modelo2['productos'])} equipos de producto no cambian.", ronda=2)
    s.modelo = modelo2
    await emit({"type": "phase", "name": "Span & layers: diseñando las jefaturas desde la base"})

    def post_opt2(r):
        m = r["metricas"]
        return (f"• Vuelvo a 15 {g['per_op']} por supervisor, como pidió el CHRO.\n"
                f"• Al separar {mezcla} ya no hace falta una capa de dirección: {m['capas']} capas.\n"
                f"• {m['jefaturas']} jefaturas y tramo promedio de {m['tramo_promedio']}.")
    await _guion_agente(s, "optimizador", f"Rediseño con 15 {g['per_op']} por supervisor y el nuevo modelo.\n",
                        [("disenar_organizacion", {"tramo_gerencial": 8})], post_opt2, ronda=2)
    await emit({"type": "phase", "name": "Calculando el impacto"})
    await _guion_agente(s, "impacto", "Recalculo el impacto con el diseño corregido.\n",
                        [("calcular_impacto", {})], post_imp, ronda=2)
    await emit({"type": "phase", "name": "Revisión del CHRO"})
    v2 = {"veredicto": "APROBADO", "objeciones": [], "cambios_pedidos": list(g["condiciones"])}

    def post_chro2(r, _):
        return (f"Ahora sí lo firmo. {g['cubierto']} y cada plataforma tiene escala.\n"
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


def ultima_grabacion(empresa_id: str) -> str | None:
    patrones = [f"{empresa_id}-corrida-*.jsonl"] + (["corrida-*.jsonl"] if empresa_id == "cpg" else [])
    archivos = sorted((a for p in patrones for a in glob.glob(os.path.join(RAIZ, "runs", p))),
                      key=lambda a: os.path.basename(a).split("corrida-")[-1])
    archivos = [a for a in archivos if _grabacion_completa(a)]
    return archivos[-1] if archivos else None


async def correr_grabacion(bus: Bus) -> None:
    ruta = ultima_grabacion(bus.estado.get("empresa"))
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


# =========================================================================== "Cómo funciona": configuración visible
def detalle(e: Empresa) -> dict:
    personas = len(motor.cargar_asis(e))
    return {
        "diagnostico": {"fase": "Ronda 1 · en paralelo con Capacidades",
                        "recibe": "El brief del CEO (caso) y la instrucción de diagnosticar span & layers.",
                        "publica": ["Pirámide y KPIs de hoy (asis)"],
                        "calcula_el_codigo": f"Capas, tramos, jefes con un reporte y costo de jefaturas sobre las {personas:,} posiciones."},
        "capacidades": {"fase": "Ronda 1 · en paralelo con Diagnóstico",
                        "recibe": "El brief del CEO y la instrucción de mapear capacidades.",
                        "publica": ["Capacidades duplicadas (capacidades)"],
                        "calcula_el_codigo": "Cuántas personas tiene cada capacidad y en cuántas áreas vive."},
        "disenador": {"fase": "Ronda 1 y ronda 2",
                      "recibe": "El brief, el texto del Diagnóstico y del Mapa de capacidades. En la ronda 2, además, "
                                "el modelo anterior y las objeciones del CHRO.",
                      "publica": ["Modelo producto-plataforma (modelo)"],
                      "calcula_el_codigo": f"Valida que cada capacidad y {e.etiqueta_categoria} quede en un solo bloque y "
                                           "devuelve una vista previa con capas y alertas."},
        "optimizador": {"fase": "Ronda 1 y ronda 2",
                        "recibe": "El brief y el modelo registrado. En la ronda 2, además, las reglas anteriores y las "
                                  "objeciones del CHRO.",
                        "publica": ["Organigrama propuesto (tobe)", "Intentos del optimizador"],
                        "calcula_el_codigo": "Construye el organigrama desde la base: agrupa a los contribuidores en "
                                             "equipos y crea las jefaturas según los tramos elegidos."},
        "impacto": {"fase": "Ronda 1 y ronda 2",
                    "recibe": "El brief y la instrucción de resumir el impacto del diseño vigente.",
                    "publica": ["KPIs antes → después y ahorro (impacto)"],
                    "calcula_el_codigo": "Compara hoy contra la propuesta: jefaturas, capas, tramo, costo y personas "
                                         "que pasan de las unidades a plataformas."},
        "chro": {"fase": "Cierre de cada ronda",
                 "recibe": "El brief y, en la segunda revisión, sus propias objeciones anteriores.",
                 "publica": ["Riesgos detectados (riesgos)", "Veredicto: APROBADO u OBJETADO (veredicto)"],
                 "calcula_el_codigo": "Chequeos de riesgo: reportes por líder, tramos de primera línea, bloques que "
                                      "mezclan operaciones distintas, tamaño de bloques, capas y reportes del CEO."},
    }


TIPOS_ES = {"object": "objeto", "integer": "entero", "string": "texto", "array": "lista", "number": "número"}
PARAM_DESC = {
    "productos": "Equipos de producto: nombre y líneas (categorías) que cubre cada uno.",
    "plataformas": "Capacidades compartidas que sirven a todos los productos.",
    "habilitadores": "Funciones de soporte: finanzas, gente, tecnología, legal.",
    "tramo_primera_linea": "Reportes por supervisor según el tipo de trabajo: operativo, comercial de campo, "
                           "profesional y especialista.",
    "tramo_gerencial": "Reportes de un jefe de jefes.",
    "tramo_lider_bloque": "Reportes del líder de cada bloque antes de crear una capa de dirección.",
    "justificacion": "Por qué eligió esas reglas.",
    "veredicto": "APROBADO u OBJETADO.",
    "objeciones": "Problemas que el equipo debe corregir.",
    "cambios_pedidos": "Cambios concretos o condiciones de implementación.",
}


def _parametros(esquema: dict) -> list[dict]:
    props = (esquema or {}).get("properties", {})
    req = set((esquema or {}).get("required", []))
    out = []
    for nombre, p in props.items():
        tipo = TIPOS_ES.get(p.get("type", ""), p.get("type", ""))
        items = p.get("items") if isinstance(p.get("items"), dict) else {}
        if p.get("type") == "array":
            tipo = f'lista de {TIPOS_ES.get(items.get("type", "object"), "objetos")}'
        out.append({"nombre": nombre, "tipo": tipo, "requerido": nombre in req,
                    "opciones": p.get("enum") or items.get("enum"),
                    "descripcion": PARAM_DESC.get(nombre, p.get("description", ""))})
    return out


def configuracion_agentes(e: Empresa) -> dict:
    from app.bus import AGENTES
    det, pr, he = detalle(e), prompts(e), herramientas(e)
    agentes = []
    for a in AGENTES:
        i = a["id"]
        agentes.append({
            **a, **det[i],
            "modelo": MODELO_CHRO if i == "chro" else MODELO,
            "instrucciones": pr[i],
            "herramienta_obligatoria": OBLIGATORIA[i],
            "herramientas": [{"nombre": h["name"], "descripcion": h["description"],
                              "parametros": _parametros(h["input_schema"])} for h in he[i]],
        })
    return {"empresa": e.id, "caso": caso(e), "estilo_comun": ESTILO, "agentes": agentes,
            "reglas_por_defecto": motor.REGLAS_POR_DEFECTO}
