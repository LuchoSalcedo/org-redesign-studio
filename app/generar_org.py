"""Genera la organización sintética "Consumo Andino S.A.A." (empresa FICTICIA).

Una empresa de consumo masivo peruana inventada, con ~3,300 personas y los problemas
típicos que un rediseño organizacional busca resolver:
  - 10 capas entre el CEO y la primera línea.
  - Tramos de control bajos (promedio cercano a 3-4 reportes por jefe).
  - Cadenas de jefes con un solo reporte.
  - Capacidades duplicadas en cada unidad de negocio (pricing, analytics, digital,
    planeamiento de demanda, ventas a canal moderno).

Uso: python3 -m app.generar_org            → escribe data/org_asis.json y data/org_asis.csv
Es determinístico (semilla fija): siempre produce la misma organización.
"""
from __future__ import annotations

import csv
import json
import os
import random

SEMILLA = 7
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOMBRES = ["José", "Luis", "Carlos", "Jorge", "Juan", "Miguel", "César", "Víctor", "Raúl", "Diego",
           "Renzo", "Bruno", "Gonzalo", "Alonso", "Martín", "Óscar", "Javier", "Pedro", "Hugo", "Iván",
           "María", "Rosa", "Carmen", "Ana", "Lucía", "Patricia", "Milagros", "Claudia", "Gabriela", "Sofía",
           "Valeria", "Daniela", "Fiorella", "Andrea", "Karina", "Jimena", "Rocío", "Paola", "Elena", "Silvia"]
APELLIDOS = ["Quispe", "Flores", "Sánchez", "Rodríguez", "García", "Rojas", "Huamán", "Mamani", "Vásquez",
             "Chávez", "Ramírez", "Torres", "Mendoza", "Castillo", "Díaz", "Espinoza", "Gutiérrez", "Salazar",
             "Paredes", "Vargas", "Romero", "Cáceres", "Ríos", "Aguilar", "Medina", "Ccori", "Benavides",
             "Zevallos", "Alarcón", "Villanueva", "Delgado", "Herrera", "Pinto", "Cornejo", "Valdivia"]

# Costo anual cargado en USD por tipo de cargo (ficticio, orden de magnitud realista para Perú)
COSTO = {
    "CEO": 480_000, "VP": 230_000, "Gerente General de Unidad": 210_000, "Gerente": 120_000,
    "Subgerente": 78_000, "Jefe": 52_000, "Coordinador": 34_000, "Supervisor": 23_000,
    "Líder de Grupo": 15_500, "Especialista": 40_000, "Analista": 24_000, "Ejecutivo de Cuenta": 26_000,
    "Vendedor": 11_500, "Técnico": 12_500, "Operario": 9_200, "Asistente": 10_500,
}

CATEGORIAS = {
    "BU Alimentos": ["Galletas", "Pastas y Harinas", "Salsas y Condimentos"],
    "BU Bebidas": ["Bebidas"],
    "BU Cuidado del Hogar": ["Cuidado del Hogar"],
}


class Org:
    def __init__(self) -> None:
        self.r = random.Random(SEMILLA)
        self.gente: list[dict] = []

    def nombre(self) -> str:
        r = self.r
        return f"{r.choice(NOMBRES)} {r.choice(APELLIDOS)} {r.choice(APELLIDOS)}"

    def add(self, jefe, nivel_cargo, cargo, area, subarea, capacidad, tipo_trabajo,
            categoria=None, ubicacion="Lima") -> int:
        pid = len(self.gente) + 1
        costo = COSTO[nivel_cargo] * self.r.uniform(0.9, 1.1)
        self.gente.append({
            "id": pid, "nombre": self.nombre(), "cargo": cargo, "nivel_cargo": nivel_cargo,
            "jefe_id": jefe, "area": area, "subarea": subarea, "capacidad": capacidad,
            "tipo_trabajo": tipo_trabajo, "categoria": categoria, "ubicacion": ubicacion,
            "costo_anual_usd": round(costo, -2),
        })
        return pid

    # ---------- bloques de construcción ----------
    def cadena(self, jefe, niveles, area, subarea, capacidad, tipo, categoria=None, ubicacion="Lima"):
        """Crea una cadena de jefes con un solo reporte cada uno (problema plantado)."""
        actual = jefe
        for nivel_cargo, cargo in niveles:
            actual = self.add(actual, nivel_cargo, cargo, area, subarea, capacidad, tipo, categoria, ubicacion)
        return actual

    def equipo(self, jefe, n, nivel_cargo, cargo, area, subarea, capacidad, tipo, categoria=None, ubicacion="Lima"):
        return [self.add(jefe, nivel_cargo, cargo, area, subarea, capacidad, tipo, categoria, ubicacion)
                for _ in range(n)]


def construir() -> list[dict]:
    o = Org()
    r = o.r
    ceo = o.add(None, "CEO", "Gerente General Corporativo", "Dirección General", "Dirección General",
                "direccion", "gerencial")

    # ================= SUPPLY CHAIN =================
    vp_sc = o.add(ceo, "VP", "VP de Supply Chain", "Supply Chain", "Dirección Supply Chain", "direccion", "gerencial")
    g_man = o.add(vp_sc, "Gerente", "Gerente Corporativo de Manufactura", "Supply Chain", "Manufactura",
                  "manufactura", "gerencial")
    plantas = [("Lima", 3, 4), ("Arequipa", 2, 3), ("Trujillo", 2, 3)]  # (planta, subgerencias, líneas por subgerencia)
    for planta, n_sub, n_lineas in plantas:
        g_pl = o.add(g_man, "Gerente", f"Gerente de Planta {planta}", "Supply Chain", f"Planta {planta}",
                     "manufactura", "gerencial", ubicacion=planta)
        for s in range(n_sub):
            sub = o.add(g_pl, "Subgerente", f"Subgerente de Producción {s + 1} – {planta}", "Supply Chain",
                        f"Planta {planta}", "manufactura", "operativo", ubicacion=planta)
            for li in range(n_lineas):
                jefe_linea = o.add(sub, "Jefe", f"Jefe de Línea {li + 1}", "Supply Chain", f"Planta {planta}",
                                   "manufactura", "operativo", ubicacion=planta)
                # Jefe de línea con UN coordinador (cadena de un solo reporte)
                coord = o.add(jefe_linea, "Coordinador", "Coordinador de Turnos", "Supply Chain",
                              f"Planta {planta}", "manufactura", "operativo", ubicacion=planta)
                for t in range(r.choice([2, 3])):
                    sup = o.add(coord, "Supervisor", f"Supervisor de Turno {t + 1}", "Supply Chain",
                                f"Planta {planta}", "manufactura", "operativo", ubicacion=planta)
                    for _ in range(r.choice([3, 4])):
                        lider = o.add(sup, "Líder de Grupo", "Líder de Grupo", "Supply Chain", f"Planta {planta}",
                                      "manufactura", "operativo", ubicacion=planta)
                        o.equipo(lider, r.randint(8, 11), "Operario", "Operario de Producción", "Supply Chain",
                                 f"Planta {planta}", "manufactura", "operativo", ubicacion=planta)
        # Mantenimiento de planta
        j_mant = o.add(g_pl, "Jefe", f"Jefe de Mantenimiento {planta}", "Supply Chain", f"Planta {planta}",
                       "mantenimiento", "operativo", ubicacion=planta)
        for _ in range(3 if planta == "Lima" else 2):
            sup = o.add(j_mant, "Supervisor", "Supervisor de Mantenimiento", "Supply Chain", f"Planta {planta}",
                        "mantenimiento", "operativo", ubicacion=planta)
            o.equipo(sup, r.randint(6, 9), "Técnico", "Técnico de Mantenimiento", "Supply Chain",
                     f"Planta {planta}", "mantenimiento", "operativo", ubicacion=planta)
        # Calidad de planta
        j_cal = o.add(g_pl, "Jefe", f"Jefe de Calidad {planta}", "Supply Chain", f"Planta {planta}",
                      "calidad", "profesional", ubicacion=planta)
        coord = o.add(j_cal, "Coordinador", "Coordinador de Aseguramiento de Calidad", "Supply Chain",
                      f"Planta {planta}", "calidad", "profesional", ubicacion=planta)
        o.equipo(coord, r.randint(9, 14), "Analista", "Analista de Calidad", "Supply Chain", f"Planta {planta}",
                 "calidad", "profesional", ubicacion=planta)

    # Logística
    g_log = o.add(vp_sc, "Gerente", "Gerente de Logística", "Supply Chain", "Logística", "logistica", "gerencial")
    for cd in ["CD Lurín", "CD Callao", "CD Arequipa", "CD Trujillo", "CD Piura"]:
        sub = o.add(g_log, "Subgerente", f"Subgerente {cd}", "Supply Chain", "Logística", "logistica", "operativo",
                    ubicacion=cd.replace("CD ", ""))
        jefe = o.add(sub, "Jefe", f"Jefe de Almacén {cd}", "Supply Chain", "Logística", "logistica", "operativo",
                     ubicacion=cd.replace("CD ", ""))
        for _ in range(r.choice([4, 5]) if cd in ("CD Lurín", "CD Callao") else 3):
            sup = o.add(jefe, "Supervisor", "Supervisor de Almacén", "Supply Chain", "Logística", "logistica",
                        "operativo", ubicacion=cd.replace("CD ", ""))
            o.equipo(sup, r.randint(8, 12), "Operario", "Operario de Almacén", "Supply Chain", "Logística",
                     "logistica", "operativo", ubicacion=cd.replace("CD ", ""))
    # Compras y planeamiento de suministro
    g_com = o.add(vp_sc, "Gerente", "Gerente de Compras", "Supply Chain", "Compras", "compras", "gerencial")
    for fam in ["Materias Primas", "Empaques", "Servicios e Indirectos"]:
        sub = o.add(g_com, "Subgerente", f"Subgerente de Compras {fam}", "Supply Chain", "Compras", "compras",
                    "profesional")
        jefe = o.add(sub, "Jefe", f"Jefe de Compras {fam}", "Supply Chain", "Compras", "compras", "profesional")
        o.equipo(jefe, r.randint(4, 6), "Analista", "Comprador", "Supply Chain", "Compras", "compras", "profesional")
    g_pls = o.add(vp_sc, "Gerente", "Gerente de Planeamiento de Suministro", "Supply Chain", "Planeamiento",
                  "planeamiento_suministro", "gerencial")
    for _ in range(3):
        jefe = o.add(g_pls, "Jefe", "Jefe de Planeamiento", "Supply Chain", "Planeamiento",
                     "planeamiento_suministro", "profesional")
        o.equipo(jefe, r.randint(3, 5), "Analista", "Planner", "Supply Chain", "Planeamiento",
                 "planeamiento_suministro", "profesional")

    # ================= VENTAS CANAL TRADICIONAL =================
    vp_vt = o.add(ceo, "VP", "VP de Ventas Canal Tradicional", "Ventas Canal Tradicional", "Dirección de Ventas",
                  "direccion", "gerencial")
    for region, zonas in [("Lima", 6), ("Norte", 4), ("Sur", 4), ("Centro", 3), ("Oriente", 2)]:
        g_reg = o.add(vp_vt, "Gerente", f"Gerente Regional {region}", "Ventas Canal Tradicional", f"Región {region}",
                      "ventas_tradicional", "gerencial", ubicacion=region)
        sub = o.add(g_reg, "Subgerente", f"Subgerente Comercial {region}", "Ventas Canal Tradicional",
                    f"Región {region}", "ventas_tradicional", "comercial_campo", ubicacion=region)
        for z in range(zonas):
            jefe = o.add(sub, "Jefe", f"Jefe de Zona {region} {z + 1}", "Ventas Canal Tradicional",
                         f"Región {region}", "ventas_tradicional", "comercial_campo", ubicacion=region)
            for _ in range(r.choice([3, 4])):
                sup = o.add(jefe, "Supervisor", "Supervisor de Ventas", "Ventas Canal Tradicional",
                            f"Región {region}", "ventas_tradicional", "comercial_campo", ubicacion=region)
                o.equipo(sup, r.randint(7, 10), "Vendedor", "Vendedor de Ruta", "Ventas Canal Tradicional",
                         f"Región {region}", "ventas_tradicional", "comercial_campo", ubicacion=region)
        # Gestión de distribuidores por región
        jd = o.add(g_reg, "Jefe", f"Jefe de Distribuidores {region}", "Ventas Canal Tradicional",
                   f"Región {region}", "ventas_tradicional", "comercial_campo", ubicacion=region)
        o.equipo(jd, r.randint(2, 4), "Ejecutivo de Cuenta", "Ejecutivo de Distribuidores",
                 "Ventas Canal Tradicional", f"Región {region}", "ventas_tradicional", "comercial_campo",
                 ubicacion=region)

    # ================= UNIDADES DE NEGOCIO (capacidades duplicadas) =================
    for bu, cats in CATEGORIAS.items():
        gg = o.add(ceo, "Gerente General de Unidad", f"Gerente General {bu.replace('BU ', '')}", bu,
                   "Dirección de Unidad", "direccion", "gerencial")
        # Marketing por categoría
        g_mkt = o.add(gg, "Gerente", f"Gerente de Marketing {bu.replace('BU ', '')}", bu, "Marketing",
                      "marketing_marca", "gerencial")
        for cat in cats:
            sub = o.add(g_mkt, "Subgerente", f"Subgerente de Marca {cat}", bu, "Marketing", "marketing_marca",
                        "profesional", categoria=cat)
            for _ in range(3):
                jefe = o.add(sub, "Jefe", f"Brand Manager {cat}", bu, "Marketing", "marketing_marca",
                             "profesional", categoria=cat)
                o.equipo(jefe, r.randint(2, 3), "Analista", f"Asistente de Marca {cat}", bu, "Marketing",
                         "marketing_marca", "profesional", categoria=cat)
        # Innovación / I+D
        g_id = o.add(gg, "Subgerente", f"Subgerente de Innovación {bu.replace('BU ', '')}", bu, "Innovación",
                     "innovacion", "especialista")
        for cat in cats:
            jefe = o.add(g_id, "Jefe", f"Jefe de Desarrollo de Producto {cat}", bu, "Innovación", "innovacion",
                         "especialista", categoria=cat)
            o.equipo(jefe, r.randint(3, 5), "Especialista", f"Especialista de I+D {cat}", bu, "Innovación",
                     "innovacion", "especialista", categoria=cat)
        # Category management
        jefe = o.add(gg, "Jefe", f"Jefe de Category Management {bu.replace('BU ', '')}", bu, "Category Management",
                     "category_management", "profesional", categoria=cats[0])
        for cat in cats:
            o.equipo(jefe, 2, "Analista", f"Analista de Categoría {cat}", bu, "Category Management",
                     "category_management", "profesional", categoria=cat)
        # Trade marketing
        g_tm = o.add(gg, "Subgerente", f"Subgerente de Trade Marketing {bu.replace('BU ', '')}", bu,
                     "Trade Marketing", "trade_marketing", "profesional")
        jefe = o.add(g_tm, "Jefe", "Jefe de Trade Marketing", bu, "Trade Marketing", "trade_marketing", "profesional")
        o.equipo(jefe, r.randint(5, 8), "Analista", "Analista de Trade Marketing", bu, "Trade Marketing",
                 "trade_marketing", "profesional")
        # --- Capacidades duplicadas en cada BU ---
        g_com = o.add(gg, "Gerente", f"Gerente Comercial {bu.replace('BU ', '')}", bu, "Comercial",
                      "direccion", "gerencial")
        # Pricing / RGM: Subgerente → Jefe → 2-3 analistas (cadena)
        sub = o.add(g_com, "Subgerente", "Subgerente de Pricing y RGM", bu, "Pricing y RGM", "pricing_rgm",
                    "especialista")
        jefe = o.add(sub, "Jefe", "Jefe de Pricing", bu, "Pricing y RGM", "pricing_rgm", "especialista")
        o.equipo(jefe, r.randint(2, 3), "Analista", "Analista de Pricing", bu, "Pricing y RGM", "pricing_rgm",
                 "especialista")
        # Analytics
        jefe = o.add(g_com, "Jefe", "Jefe de Inteligencia Comercial", bu, "Analytics", "analytics", "especialista")
        coord = o.add(jefe, "Coordinador", "Coordinador de Analytics", bu, "Analytics", "analytics", "especialista")
        o.equipo(coord, r.randint(3, 5), "Analista", "Analista de Datos", bu, "Analytics", "analytics", "especialista")
        # Digital / e-commerce
        jefe = o.add(g_com, "Jefe", "Jefe de E-commerce", bu, "Digital", "digital_ecommerce", "especialista")
        o.equipo(jefe, r.randint(2, 4), "Analista", "Analista de E-commerce", bu, "Digital", "digital_ecommerce",
                 "especialista")
        # Planeamiento de demanda
        jefe = o.add(g_com, "Jefe", "Jefe de Planeamiento de Demanda", bu, "Planeamiento de Demanda",
                     "planeamiento_demanda", "profesional")
        o.equipo(jefe, r.randint(3, 4), "Analista", "Demand Planner", bu, "Planeamiento de Demanda",
                 "planeamiento_demanda", "profesional")
        # Ventas canal moderno (key accounts)
        sub = o.add(g_com, "Subgerente", "Subgerente de Canal Moderno", bu, "Canal Moderno", "ventas_moderno",
                    "comercial_campo")
        for _ in range(2):
            jefe = o.add(sub, "Jefe", "Key Account Manager", bu, "Canal Moderno", "ventas_moderno",
                         "comercial_campo")
            o.equipo(jefe, r.randint(3, 5), "Ejecutivo de Cuenta", "Ejecutivo de Cuenta Clave", bu, "Canal Moderno",
                     "ventas_moderno", "comercial_campo")
        # Finanzas de la BU (business partners)
        jefe = o.add(gg, "Jefe", "Jefe de Finanzas de Unidad", bu, "Finanzas de Unidad", "finanzas", "profesional")
        o.equipo(jefe, r.randint(2, 3), "Analista", "Analista Financiero", bu, "Finanzas de Unidad", "finanzas",
                 "profesional")

    # ================= FUNCIONES CORPORATIVAS =================
    def funcion(cargo_vp, area, capacidad, gerencias, tipo="profesional"):
        vp = o.add(ceo, "VP", cargo_vp, area, f"Dirección {area}", "direccion", "gerencial")
        for g_nombre, subs in gerencias:
            g = o.add(vp, "Gerente", g_nombre, area, g_nombre.replace("Gerente de ", ""), capacidad, "gerencial")
            for s_nombre, jefes, analistas in subs:
                s = o.add(g, "Subgerente", s_nombre, area, g_nombre.replace("Gerente de ", ""), capacidad, tipo)
                for j in range(jefes):
                    jf = o.add(s, "Jefe", f"Jefe de {s_nombre.replace('Subgerente de ', '')}", area,
                               g_nombre.replace("Gerente de ", ""), capacidad, tipo)
                    o.equipo(jf, r.randint(*analistas), "Analista", f"Analista de {s_nombre.replace('Subgerente de ', '')}",
                             area, g_nombre.replace("Gerente de ", ""), capacidad, tipo)
                    if r.random() < 0.5:
                        o.add(jf, "Asistente", "Asistente Administrativo", area, g_nombre.replace("Gerente de ", ""),
                              capacidad, tipo)

    funcion("VP de Finanzas", "Finanzas", "finanzas", [
        ("Gerente de Contabilidad", [("Subgerente de Contabilidad General", 2, (4, 6)), ("Subgerente de Impuestos", 1, (3, 4))]),
        ("Gerente de Tesorería", [("Subgerente de Tesorería", 1, (3, 5)), ("Subgerente de Créditos y Cobranzas", 2, (4, 6))]),
        ("Gerente de Planeamiento Financiero", [("Subgerente de Presupuesto", 1, (3, 4)), ("Subgerente de Control de Gestión", 2, (3, 5))]),
    ])
    funcion("VP de Gestión Humana", "Gestión Humana", "rrhh", [
        ("Gerente de Talento", [("Subgerente de Selección", 1, (3, 5)), ("Subgerente de Desarrollo", 2, (2, 4))]),
        ("Gerente de Compensaciones", [("Subgerente de Planillas", 2, (4, 6)), ("Subgerente de Beneficios", 1, (2, 3))]),
        ("Gerente de Relaciones Laborales", [("Subgerente de Relaciones Laborales", 2, (3, 5)), ("Subgerente de Seguridad y Salud", 2, (4, 6))]),
    ])
    funcion("VP de Tecnología", "Tecnología", "ti", [
        ("Gerente de Infraestructura", [("Subgerente de Operaciones TI", 2, (4, 6)), ("Subgerente de Ciberseguridad", 1, (3, 4))]),
        ("Gerente de Aplicaciones", [("Subgerente de ERP", 2, (4, 6)), ("Subgerente de Soluciones Comerciales", 2, (3, 5))]),
    ], tipo="especialista")
    funcion("VP Legal y Asuntos Corporativos", "Legal y Asuntos Corporativos", "legal", [
        ("Gerente Legal", [("Subgerente de Asuntos Regulatorios", 1, (3, 4)), ("Subgerente de Contratos", 1, (2, 3))]),
        ("Gerente de Asuntos Corporativos", [("Subgerente de Comunicaciones", 1, (2, 4))]),
    ], tipo="especialista")
    return o.gente


def main() -> None:
    gente = construir()
    os.makedirs(os.path.join(RAIZ, "data"), exist_ok=True)
    with open(os.path.join(RAIZ, "data", "org_asis.json"), "w", encoding="utf-8") as f:
        json.dump(gente, f, ensure_ascii=False)
    with open(os.path.join(RAIZ, "data", "org_asis.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(gente[0].keys()))
        w.writeheader()
        w.writerows(gente)
    print(f"{len(gente)} personas generadas")


if __name__ == "__main__":
    main()
