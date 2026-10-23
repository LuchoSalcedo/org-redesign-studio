"""Motor de cálculo del rediseño organizacional.

Todo lo que es aritmética sobre las personas de cada empresa vive aquí y es determinístico:
los agentes deciden el diseño y llaman a estas funciones como herramientas, así los
números siempre cuadran y se calculan en milisegundos.

Conceptos:
- Capa: profundidad en el organigrama (CEO = capa 1).
- Tramo de control: número de reportes directos de un jefe.
- Jefe: toda posición con al menos un reporte.
- Contribuidor individual (IC): toda posición sin reportes. Los ICs se conservan en el
  diseño objetivo; las jefaturas se rediseñan desde la base según reglas de tramo.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from app import generar_org as G
from app.empresas import Empresa

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIPOS_TRABAJO = ["operativo", "comercial_campo", "profesional", "especialista"]

REGLAS_POR_DEFECTO = {
    "tramo_primera_linea": {"operativo": 15, "comercial_campo": 10, "profesional": 7, "especialista": 5},
    "tramo_gerencial": 6,        # jefes de jefes
    "tramo_lider_bloque": 10,    # máximo de reportes del líder de cada bloque antes de crear una capa de dirección
    "capas_max": 7,
    "tamano_minimo_equipo": 4,   # equipos más chicos se fusionan con otros del mismo bloque
}

# Costo anual cargado (USD) de las posiciones de jefatura del diseño objetivo (se escala por empresa)
COSTO_JEFE = {
    "ceo": 480_000, "lider_bloque": 230_000, "director": 150_000, "jefe_equipo": 120_000,
    ("nivel2", "operativo"): 52_000, ("nivel2", "comercial_campo"): 52_000,
    ("nivel2", "profesional"): 78_000, ("nivel2", "especialista"): 78_000,
    ("nivel1", "operativo"): 23_000, ("nivel1", "comercial_campo"): 23_000,
    ("nivel1", "profesional"): 52_000, ("nivel1", "especialista"): 52_000,
}

_ASIS: dict[str, list[dict]] = {}


def cargar_asis(e: Empresa) -> list[dict]:
    if e.id not in _ASIS:
        ruta = G.ruta_datos(e.id)
        if not os.path.exists(ruta):
            G.generar(e.id)
        with open(ruta, encoding="utf-8") as f:
            _ASIS[e.id] = json.load(f)
    return _ASIS[e.id]


# --------------------------------------------------------------------------- métricas
def _indices(org: list[dict]):
    por_id = {p["id"]: p for p in org}
    hijos: dict = defaultdict(list)
    for p in org:
        if p["jefe_id"] is not None:
            hijos[p["jefe_id"]].append(p["id"])
    capa: dict = {}
    raiz = next(p["id"] for p in org if p["jefe_id"] is None)
    pila = [(raiz, 1)]
    while pila:
        pid, c = pila.pop()
        capa[pid] = c
        pila.extend((h, c + 1) for h in hijos.get(pid, []))
    return por_id, hijos, capa


def _bucket(n: int) -> str:
    if n == 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 6:
        return "4-6"
    if n <= 10:
        return "7-10"
    if n <= 15:
        return "11-15"
    return "16+"


BUCKETS = ["1", "2-3", "4-6", "7-10", "11-15", "16+"]


def metricas(org: list[dict]) -> dict:
    por_id, hijos, capa = _indices(org)
    tramos = [len(v) for v in hijos.values()]
    jefes = list(hijos.keys())
    piramide = Counter(capa.values())
    dist = Counter(_bucket(t) for t in tramos)
    costo_total = sum(p["costo_anual_usd"] for p in org)
    costo_jefes = sum(por_id[j]["costo_anual_usd"] for j in jefes)
    return {
        "personas": len(org),
        "capas": max(capa.values()),
        "jefaturas": len(jefes),
        "pct_jefaturas": round(100 * len(jefes) / len(org), 1),
        "tramo_promedio": round(sum(tramos) / len(tramos), 1),
        "jefes_un_reporte": sum(1 for t in tramos if t == 1),
        "pct_jefes_tramo_bajo": round(100 * sum(1 for t in tramos if t <= 3) / len(tramos), 1),
        "costo_total_musd": round(costo_total / 1e6, 1),
        "costo_jefaturas_musd": round(costo_jefes / 1e6, 1),
        "piramide": [{"capa": c, "personas": piramide[c]} for c in sorted(piramide)],
        "distribucion_tramos": [{"tramo": b, "jefes": dist.get(b, 0)} for b in BUCKETS],
    }


# --------------------------------------------------------------------------- diagnóstico
def diagnostico(e: Empresa) -> dict:
    """Span & layers de la organización actual, con los focos por área."""
    org = cargar_asis(e)
    por_id, hijos, capa = _indices(org)
    m = metricas(org)
    focos = []
    por_area = defaultdict(list)
    for j, hs in hijos.items():
        por_area[por_id[j]["area"]].append(len(hs))
    capas_area = defaultdict(int)
    for p in org:
        capas_area[p["area"]] = max(capas_area[p["area"]], capa[p["id"]])
    personas_area = Counter(p["area"] for p in org)
    for area, ts in por_area.items():
        if area == "Dirección General":
            continue
        focos.append({
            "area": area, "personas": personas_area[area], "jefaturas": len(ts),
            "tramo_promedio": round(sum(ts) / len(ts), 1), "jefes_un_reporte": sum(1 for t in ts if t == 1),
            "capa_mas_profunda": capas_area[area],
        })
    focos.sort(key=lambda f: f["tramo_promedio"])
    # ejemplos de cadenas de un solo reporte
    ejemplos = []
    for j, hs in hijos.items():
        if len(hs) == 1 and hijos.get(hs[0]):
            ejemplos.append(f'{por_id[j]["cargo"]} → {por_id[hs[0]]["cargo"]} ({por_id[j]["subarea"]})')
    vistos, unicos = set(), []
    for e in ejemplos:
        clave = e.split(" (")[0]
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(e)
    m.update({"focos_por_area": focos, "ejemplos_cadenas_un_reporte": unicos[:6]})
    return m


def mapa_capacidades(e: Empresa) -> dict:
    """Dónde vive cada capacidad hoy y cuáles están duplicadas entre unidades."""
    org = cargar_asis(e)
    _, hijos, _ = _indices(org)
    resumen = {}
    for p in org:
        c = p["capacidad"]
        if c == "direccion":
            continue
        r = resumen.setdefault(c, {"capacidad": c, "nombre": e.capacidades[c], "personas": 0, "jefaturas": 0,
                                   "areas": set(), "categorias": set()})
        r["personas"] += 1
        r["jefaturas"] += 1 if p["id"] in hijos else 0
        r["areas"].add(p["area"])
        if p["categoria"]:
            r["categorias"].add(p["categoria"])
    filas = []
    for r in resumen.values():
        filas.append({**r, "areas": sorted(r["areas"]), "categorias": sorted(r["categorias"]),
                      "duplicada": len(r["areas"]) > 1})
    filas.sort(key=lambda r: (-len(r["areas"]), -r["personas"]))
    direccion = sum(1 for p in org if p["capacidad"] == "direccion")
    return {
        "posiciones_de_direccion": direccion,
        "nota_direccion": f"{direccion} posiciones de dirección (CEO, vicepresidentes, directores de unidad y gerentes comerciales) no tienen "
                          f"capacidad asignada: se rediseñan como líderes de bloque. Con ellas se suman las "
                          f"{len(org):,} personas.",
        "capacidades": filas,
        "duplicadas": [r["nombre"] for r in filas if r["duplicada"]],
        "capacidades_de_producto": sorted(e.cap_producto),
        "categorias": e.categorias,
        "nota": f"Las capacidades de producto ({', '.join(e.capacidades[c].lower() for c in sorted(e.cap_producto))}) "
                f"se reparten por {e.etiqueta_categoria} entre los equipos de producto; las demás se asignan completas "
                f"a una plataforma o habilitador.",
    }


# --------------------------------------------------------------------------- modelo objetivo
def validar_modelo(e: Empresa, modelo: dict) -> list[str]:
    if not isinstance(modelo, dict):
        return ["El modelo debe ser un objeto con productos, plataformas y habilitadores"]
    for clave in ("productos", "plataformas", "habilitadores"):
        lista = modelo.get(clave) or []
        if not isinstance(lista, list) or not all(isinstance(b, dict) and b.get("nombre") for b in lista):
            return [f'"{clave}" debe ser una lista de bloques, cada uno con "nombre"']
    nombres = Counter(b["nombre"] for c in ("productos", "plataformas", "habilitadores") for b in modelo.get(c) or [])
    errores = [f'Hay dos bloques llamados "{n}"; cada bloque necesita un nombre único' for n, k in nombres.items() if k > 1]
    asignadas = Counter()
    for bloque in (modelo.get("plataformas") or []) + (modelo.get("habilitadores") or []):
        for c in bloque.get("capacidades") or []:
            if c not in e.capacidades:
                errores.append(f'Capacidad desconocida "{c}" en {bloque.get("nombre")}')
            asignadas[c] += 1
    for c, n in asignadas.items():
        if n > 1:
            errores.append(f'La capacidad "{c}" está asignada a {n} bloques; debe estar en uno solo')
        if c in e.cap_producto:
            errores.append(f'"{c}" es una capacidad de producto: va en los equipos de producto, no en una plataforma')
    for c in e.capacidades:
        if c not in e.cap_producto and c not in asignadas:
            errores.append(f'Falta asignar la capacidad "{c}" a una plataforma o habilitador')
    cats = Counter(cat for prod in modelo.get("productos") or [] for cat in prod.get("categorias") or [])
    for cat in e.categorias:
        if cats[cat] == 0:
            errores.append(f'La {e.etiqueta_categoria} "{cat}" no tiene equipo de producto')
        elif cats[cat] > 1:
            errores.append(f'La {e.etiqueta_categoria} "{cat}" está en más de un equipo de producto')
    for cat in cats:
        if cat not in e.categorias:
            errores.append(f'{e.etiqueta_categoria.capitalize()} desconocida "{cat}"')
    if not modelo.get("productos"):
        errores.append("El modelo necesita al menos un equipo de producto")
    return errores


def _entero(v, defecto: int, minimo: int = 2, maximo: int = 30) -> int:
    try:
        return max(minimo, min(maximo, int(float(v))))
    except (TypeError, ValueError):
        return defecto


def _reglas(reglas: dict | None) -> dict:
    """Normaliza las reglas: ignora llaves desconocidas o mal formadas y acota los tramos a 2-30.
    El máximo de capas es un requisito del CEO, no una regla que los agentes puedan mover."""
    r = json.loads(json.dumps(REGLAS_POR_DEFECTO))
    for k, v in (reglas or {}).items() if isinstance(reglas, dict) else []:
        if k == "tramo_primera_linea":
            if isinstance(v, dict):
                for t, x in v.items():
                    if t in TIPOS_TRABAJO:
                        r[k][t] = _entero(x, r[k][t])
        elif k in ("tramo_gerencial", "tramo_lider_bloque", "tamano_minimo_equipo"):
            r[k] = _entero(v, r[k])
    return r


def disenar_org(e: Empresa, modelo: dict, reglas: dict | None = None) -> dict:
    """Construye el organigrama objetivo desde la base.

    Conserva a todos los contribuidores individuales, los agrupa en equipos según el
    modelo producto-plataforma y crea las jefaturas necesarias según los tramos.
    """
    errores = validar_modelo(e, modelo)
    if errores:
        return {"ok": False, "errores": errores}
    R = _reglas(reglas)
    asis = cargar_asis(e)
    costo_jefe = lambda k: round(COSTO_JEFE[k] * e.factor_costo, -2)
    _, hijos_asis, _ = _indices(asis)
    ics = [p for p in asis if p["id"] not in hijos_asis and p["capacidad"] != "direccion"]

    bloque_de_cap, tipo_bloque = {}, {}
    bloques = []
    for tipo, clave in (("producto", "productos"), ("plataforma", "plataformas"), ("habilitador", "habilitadores")):
        for b in modelo.get(clave, []):
            bloques.append({"nombre": b["nombre"], "tipo": tipo, "descripcion": b.get("descripcion", ""),
                            "categorias": b.get("categorias", []), "capacidades": b.get("capacidades", [])})
            tipo_bloque[b["nombre"]] = tipo
            for c in b.get("capacidades", []):
                bloque_de_cap[c] = b["nombre"]
    bloque_de_cat = {cat: b["nombre"] for b in bloques if b["tipo"] == "producto" for cat in b["categorias"]}

    # 1. Asignar cada IC a un bloque y a un equipo
    equipos: dict = defaultdict(list)
    for p in ics:
        if p["capacidad"] in e.cap_producto:
            b = bloque_de_cat[p["categoria"]]
            clave = (b, p["categoria"])
        else:
            b = bloque_de_cap[p["capacidad"]]
            if p["tipo_trabajo"] in ("operativo", "comercial_campo"):
                clave = (b, f'{e.capacidades[p["capacidad"]]} – {p["ubicacion"]}')
            else:
                clave = (b, e.capacidades[p["capacidad"]])
        equipos[clave].append(p)

    # 2. Fusionar equipos demasiado chicos dentro de su bloque
    por_bloque = defaultdict(list)
    for (b, nombre), gente in equipos.items():
        por_bloque[b].append([nombre, gente])
    for b, lista in por_bloque.items():
        chicos = [e for e in lista if len(e[1]) < R["tamano_minimo_equipo"]]
        if len(chicos) >= 1 and len(lista) > 1:
            grandes = [e for e in lista if len(e[1]) >= R["tamano_minimo_equipo"]]
            if len(chicos) >= 2:
                fusion = [" + ".join(e[0] for e in chicos), [x for e in chicos for x in e[1]]]
                if len(fusion[1]) < R["tamano_minimo_equipo"] and grandes:
                    grandes.sort(key=lambda e: len(e[1]))
                    grandes[0][1].extend(fusion[1])
                    grandes[0][0] += " + " + fusion[0]
                    por_bloque[b] = grandes
                else:
                    por_bloque[b] = grandes + [fusion]
            elif grandes:
                grandes.sort(key=lambda e: len(e[1]))
                grandes[0][1].extend(chicos[0][1])
                grandes[0][0] += " + " + chicos[0][0]
                por_bloque[b] = grandes

    # 3. Construir el árbol
    org: list[dict] = []
    nuevo_id = [100000]

    def nueva_pos(jefe, cargo, rol, costo, bloque, equipo, tipo):
        nuevo_id[0] += 1
        org.append({"id": nuevo_id[0], "jefe_id": jefe, "cargo": cargo, "rol": rol, "costo_anual_usd": costo,
                    "bloque": bloque, "equipo": equipo, "tipo_trabajo": tipo, "persona_id": None})
        return nuevo_id[0]

    ceo = nueva_pos(None, "CEO", "ceo", costo_jefe("ceo"), "Dirección General", "Dirección General", "gerencial")
    resumen_bloques = []
    for b in bloques:
        lista = por_bloque.get(b["nombre"], [])
        if not lista:
            continue
        lider = nueva_pos(ceo, f'Líder de {b["nombre"]}', "lider_bloque", costo_jefe("lider_bloque"), b["nombre"],
                          b["nombre"], "gerencial")
        lista.sort(key=lambda e: e[0])
        # capa de dirección si el líder tendría demasiados reportes
        padres = [lider] * len(lista)
        if len(lista) > R["tramo_lider_bloque"]:
            k = math.ceil(len(lista) / R["tramo_lider_bloque"])
            tam = math.ceil(len(lista) / k)
            padres = []
            for i in range(k):
                trozo = lista[i * tam:(i + 1) * tam]
                if not trozo:
                    continue
                d = nueva_pos(lider, f'Director(a) – {trozo[0][0].split(" – ")[0]}', "director",
                              costo_jefe("director"), b["nombre"], "Dirección", "gerencial")
                padres.extend([d] * len(trozo))
        for (nombre_eq, gente), padre in zip(lista, padres):
            tipo = Counter(p["tipo_trabajo"] for p in gente).most_common(1)[0][0]
            s1 = R["tramo_primera_linea"][tipo]
            sg = R["tramo_gerencial"]
            niveles = [len(gente)]
            niveles.append(max(1, math.ceil(len(gente) / s1)))
            while niveles[-1] > 1:
                niveles.append(math.ceil(niveles[-1] / sg))
            # niveles = [ICs, primera línea, ..., 1 jefe de equipo]
            capas_jefes = niveles[1:]
            if len(lista) == 1:
                # bloque de un solo equipo: el líder del bloque dirige el equipo directamente
                actuales = [padre]
            else:
                actuales = [nueva_pos(padre, f"Jefe(a) de {nombre_eq}", "jefe_equipo", costo_jefe("jefe_equipo"),
                                      b["nombre"], nombre_eq, tipo)]
            for idx in range(len(capas_jefes) - 2, -1, -1):
                n = capas_jefes[idx]
                nivel = "nivel1" if idx == 0 else "nivel2"
                cargo = "Supervisor(a)" if idx == 0 and tipo in ("operativo", "comercial_campo") else (
                    "Coordinador(a)" if idx == 0 else "Jefe(a) de área")
                nuevos = []
                for i in range(n):
                    nuevos.append(nueva_pos(actuales[i * len(actuales) // n], f"{cargo} – {nombre_eq}", nivel,
                                            costo_jefe((nivel, tipo)), b["nombre"], nombre_eq, tipo))
                actuales = nuevos
            for i, p in enumerate(gente):
                org.append({"id": p["id"], "jefe_id": actuales[i * len(actuales) // len(gente)], "cargo": p["cargo"],
                            "rol": "ic", "costo_anual_usd": p["costo_anual_usd"], "bloque": b["nombre"],
                            "equipo": nombre_eq, "tipo_trabajo": p["tipo_trabajo"], "persona_id": p["id"],
                            "area_actual": p["area"]})
        resumen_bloques.append({"nombre": b["nombre"], "tipo": b["tipo"], "descripcion": b["descripcion"],
                                "capacidades_bloque": b["capacidades"] or sorted(e.cap_producto),
                                "categorias": b["categorias"]})

    por_id, hijos, capa = _indices(org)
    for rb in resumen_bloques:
        miembros = [p for p in org if p["bloque"] == rb["nombre"]]
        lider = next(p for p in miembros if p["rol"] == "lider_bloque")
        rb.update({
            "personas": len(miembros),
            "jefaturas": sum(1 for p in miembros if p["id"] in hijos),
            "equipos": len({p["equipo"] for p in miembros if p["rol"] == "ic"}),
            "reportes_del_lider": len(hijos[lider["id"]]),
            "capas": max(capa[p["id"]] for p in miembros),
            "costo_musd": round(sum(p["costo_anual_usd"] for p in miembros) / 1e6, 1),
            "nombres_equipos": sorted({p["equipo"] for p in miembros if p["rol"] == "ic"}),
        })
    m = metricas(org)
    alertas = []
    if m["capas"] > R["capas_max"]:
        profundos = sorted({p["bloque"] for p in org if capa[p["id"]] > R["capas_max"]})
        alertas.append(f'El diseño tiene {m["capas"]} capas, más que el máximo de {R["capas_max"]}. '
                       f'Bloques con capas de más: {", ".join(profundos)}.')
        for rb in resumen_bloques:
            if rb["nombre"] in profundos and rb["equipos"] > R["tramo_lider_bloque"]:
                alertas.append(f'{rb["nombre"]} tiene {rb["equipos"]} equipos: su líder necesita una capa de dirección '
                               f'y eso agrega una capa. La forma de quitarla es dividir el bloque en dos '
                               f'(por ejemplo, {e.pares_incompatibles[0][2].replace(" y ", " por un lado y ")} por otro).')
    ics = sum(1 for p in org if p["rol"] == "ic")
    m["reportes_del_ceo"] = len(hijos[org[0]["id"]])
    m["dotacion"] = {
        "personas_hoy": len(cargar_asis(e)),
        "contribuidores_individuales_conservados": ics,
        "posiciones_de_jefatura_propuestas": m["jefaturas"],
        "nota": "Todos los contribuidores individuales de hoy están en el diseño. La diferencia entre las personas "
                "de hoy y las posiciones propuestas son jefaturas eliminadas; no hay personas sin asignar.",
    }
    return {"ok": True, "reglas": R, "metricas": m, "bloques": resumen_bloques, "alertas": alertas, "_org": org}


def revisar_riesgos(e: Empresa, diseno: dict) -> dict:
    """Chequeos que haría un CHRO sobre el diseño objetivo."""
    org = diseno["_org"]
    R = diseno["reglas"]
    _, hijos, capa = _indices(org)
    hallazgos = []
    for b in diseno["bloques"]:
        if b["reportes_del_lider"] > 8:
            hallazgos.append({"severidad": "alta", "bloque": b["nombre"],
                              "hallazgo": f'El líder de {b["nombre"]} tendría {b["reportes_del_lider"]} reportes '
                                          f'directos; por encima de 8 no puede dirigir bien.'})
        if b["tipo"] == "producto" and b["personas"] < 12:
            hallazgos.append({"severidad": "media", "bloque": b["nombre"],
                              "hallazgo": f'El equipo de producto {b["nombre"]} tiene solo {b["personas"]} personas; '
                                          f'es poco para tener P&L propio.'})
        caps = set(b.get("capacidades_bloque", []))
        for a, z, desc in e.pares_incompatibles:
            if {a, z} <= caps:
                hallazgos.append({"severidad": "media", "bloque": b["nombre"],
                                  "hallazgo": f'{b["nombre"]} junta {desc} bajo un solo líder '
                                              f'({b["personas"]:,} personas); son operaciones con indicadores distintos.'})
        if b["tipo"] == "plataforma" and b["personas"] < 20:
            hallazgos.append({"severidad": "media", "bloque": b["nombre"],
                              "hallazgo": f'La plataforma {b["nombre"]} tiene {b["personas"]} personas: muy chica '
                                          f'para justificar un líder de bloque que reporte al CEO.'})
    if len(diseno["bloques"]) > 12:
        hallazgos.append({"severidad": "alta", "bloque": "CEO",
                          "hallazgo": f'El CEO tendría {len(diseno["bloques"])} reportes directos; el máximo razonable '
                                      f'en un modelo producto-plataforma es 12.'})
    for t, s in R["tramo_primera_linea"].items():
        if t == "operativo" and s > 15:
            hallazgos.append({"severidad": "alta", "bloque": e.bloque_operativo,
                              "hallazgo": e.riesgo_operativo.format(s=s)})
        if t in ("profesional", "especialista") and s > 9:
            hallazgos.append({"severidad": "media", "bloque": "Equipos profesionales",
                              "hallazgo": f"Un tramo de {s} para trabajo {t} deja poco espacio para formar talento."})
        if t == "comercial_campo" and s > 14:
            hallazgos.append({"severidad": "media", "bloque": "Fuerza de ventas",
                              "hallazgo": f"Un supervisor con {s} vendedores no alcanza a acompañar rutas."})
    if diseno["metricas"]["capas"] > R["capas_max"]:
        hallazgos.append({"severidad": "alta", "bloque": "Toda la organización",
                          "hallazgo": f'Quedan {diseno["metricas"]["capas"]} capas; el objetivo era {R["capas_max"]}.'})
    return {"hallazgos": hallazgos, "aprobable": not any(h["severidad"] == "alta" for h in hallazgos),
            "reportes_del_ceo": len(diseno["bloques"]), "dotacion": diseno["metricas"].get("dotacion")}


def impacto(e: Empresa, diseno: dict) -> dict:
    asis = metricas(cargar_asis(e))
    tobe = diseno["metricas"]
    tipo_de = {b["nombre"]: b["tipo"] for b in diseno["bloques"]}
    movidos = Counter()
    for p in diseno["_org"]:
        if p["rol"] == "ic" and e.es_unidad(p.get("area_actual", "")) and tipo_de.get(p["bloque"]) != "producto":
            movidos[(p["area_actual"], p["bloque"])] += 1
    consolidaciones = [{"desde": a, "hacia": b, "personas": n} for (a, b), n in movidos.most_common()][:8]
    ahorro = asis["costo_total_musd"] - tobe["costo_total_musd"]
    return {
        "antes": {k: asis[k] for k in ("personas", "capas", "jefaturas", "tramo_promedio", "jefes_un_reporte",
                                       "pct_jefes_tramo_bajo", "costo_jefaturas_musd", "costo_total_musd")},
        "despues": {k: tobe[k] for k in ("personas", "capas", "jefaturas", "tramo_promedio", "jefes_un_reporte",
                                         "pct_jefes_tramo_bajo", "costo_jefaturas_musd", "costo_total_musd")},
        "posiciones_de_jefatura_menos": asis["jefaturas"] - tobe["jefaturas"],
        "ahorro_anual_musd": round(ahorro, 1),
        "ahorro_pct_costo_total": round(100 * ahorro / asis["costo_total_musd"], 1),
        "personas_de_unidades_a_plataformas": sum(movidos.values()),
        "principales_consolidaciones": consolidaciones,
        "nota": "Las jefaturas se cuentan como posiciones. Asignar personas a las nuevas posiciones es un paso "
                "posterior del proyecto.",
    }


def resumen_asis_por_area(e: Empresa) -> list[dict]:
    org = cargar_asis(e)
    _, hijos, _ = _indices(org)
    c = Counter(p["area"] for p in org)
    j = Counter(p["area"] for p in org if p["id"] in hijos)
    return [{"area": a, "personas": n, "jefaturas": j[a]} for a, n in c.most_common() if a != "Dirección General"]


# --------------------------------------------------------------------------- vista "organización actual"
def organizacion_actual(e: Empresa) -> dict:
    """Todo lo que muestra la vista previa a la corrida: KPIs, pirámide por grupo, focos y duplicaciones."""
    org = cargar_asis(e)
    por_id, hijos, capa = _indices(org)
    d = diagnostico(e)
    grupos = e.orden_grupos
    piramide = defaultdict(Counter)
    for p in org:
        piramide[capa[p["id"]]][e.grupo(p["area"])] += 1
    costo_area = defaultdict(float)
    for p in org:
        costo_area[p["area"]] += p["costo_anual_usd"]
    for f in d["focos_por_area"]:
        f["grupo"] = e.grupo(f["area"])
        f["costo_musd"] = round(costo_area[f["area"]] / 1e6, 1)
        f["pct_jefaturas"] = round(100 * f["jefaturas"] / f["personas"], 1)
    areas = [f["area"] for f in sorted(d["focos_por_area"], key=lambda f: -f["personas"])]
    caps = mapa_capacidades(e)
    conteo = Counter((p["capacidad"], p["area"]) for p in org if p["capacidad"] != "direccion")
    matriz = [{"capacidad": c["nombre"], "clave": c["capacidad"], "duplicada": c["duplicada"],
               "celdas": [conteo.get((c["capacidad"], a), 0) for a in areas]}
              for c in caps["capacidades"]]
    tipos = Counter(p["tipo_trabajo"] for p in org if p["id"] not in hijos and p["capacidad"] != "direccion")
    return {
        "empresa": {"id": e.id, "nombre": e.nombre, "corto": e.corto, "iniciales": e.iniciales, "pais": e.pais,
                    "sector": e.sector, "tipos": e.tipos, "abrev": e.abrev,
                    "etiqueta_categoria": e.etiqueta_categoria},
        "metricas": {k: v for k, v in d.items() if k not in ("focos_por_area", "ejemplos_cadenas_un_reporte")},
        "meta_capas": REGLAS_POR_DEFECTO["capas_max"],
        "grupos": grupos,
        "piramide_por_grupo": [{"capa": c, **{g: piramide[c].get(g, 0) for g in grupos}} for c in sorted(piramide)],
        "focos_por_area": sorted(d["focos_por_area"], key=lambda f: -f["personas"]),
        "ejemplos_cadenas_un_reporte": d["ejemplos_cadenas_un_reporte"],
        "areas_matriz": areas,
        "matriz_capacidades": matriz,
        "duplicadas": caps["duplicadas"],
        "contribuidores_por_tipo": [{"tipo": t, "personas": tipos.get(t, 0)} for t in TIPOS_TRABAJO],
    }
