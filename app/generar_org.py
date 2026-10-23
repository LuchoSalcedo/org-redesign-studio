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
    def __init__(self, semilla: int = SEMILLA, costo: dict | None = None, nombres=None, apellidos=None,
                 ubicacion: str = "Lima") -> None:
        self.r = random.Random(semilla)
        self.gente: list[dict] = []
        self.costo = costo or COSTO
        self.nombres, self.apellidos = nombres or NOMBRES, apellidos or APELLIDOS
        self.ubicacion = ubicacion

    def nombre(self) -> str:
        r = self.r
        return f"{r.choice(self.nombres)} {r.choice(self.apellidos)} {r.choice(self.apellidos)}"

    def add(self, jefe, nivel_cargo, cargo, area, subarea, capacidad, tipo_trabajo,
            categoria=None, ubicacion=None) -> int:
        ubicacion = ubicacion or self.ubicacion
        pid = len(self.gente) + 1
        costo = self.costo[nivel_cargo] * self.r.uniform(0.9, 1.1)
        self.gente.append({
            "id": pid, "nombre": self.nombre(), "cargo": cargo, "nivel_cargo": nivel_cargo,
            "jefe_id": jefe, "area": area, "subarea": subarea, "capacidad": capacidad,
            "tipo_trabajo": tipo_trabajo, "categoria": categoria, "ubicacion": ubicacion,
            "costo_anual_usd": round(costo, -2),
        })
        return pid

    # ---------- bloques de construcción ----------
    def cadena(self, jefe, niveles, area, subarea, capacidad, tipo, categoria=None, ubicacion=None):
        """Crea una cadena de jefes con un solo reporte cada uno (problema plantado)."""
        actual = jefe
        for nivel_cargo, cargo in niveles:
            actual = self.add(actual, nivel_cargo, cargo, area, subarea, capacidad, tipo, categoria, ubicacion)
        return actual

    def equipo(self, jefe, n, nivel_cargo, cargo, area, subarea, capacidad, tipo, categoria=None, ubicacion=None):
        return [self.add(jefe, nivel_cargo, cargo, area, subarea, capacidad, tipo, categoria, ubicacion)
                for _ in range(n)]


def funcion_corporativa(o: Org, ceo: int, cargo_vp, area, capacidad, gerencias, tipo="profesional"):
    """VP → gerencias → subgerencias → jefes → analistas (con asistentes al azar)."""
    r = o.r
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


def construir() -> list[dict]:
    """Consumo Andino S.A.A. (consumo masivo, Perú)."""
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
    funcion = lambda *a, **k: funcion_corporativa(o, ceo, *a, **k)
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


# =========================================================================== nombres y costos por país
NOMBRES_MX = ["José", "Luis", "Carlos", "Jorge", "Juan", "Miguel", "Alejandro", "Fernando", "Ricardo", "Eduardo",
              "Arturo", "Rodrigo", "Sergio", "Héctor", "Roberto", "Gerardo", "Mauricio", "Emilio", "Andrés", "Pablo",
              "María", "Guadalupe", "Verónica", "Ana", "Mariana", "Gabriela", "Alejandra", "Claudia", "Fernanda", "Sofía",
              "Daniela", "Paulina", "Lorena", "Adriana", "Karla", "Ximena", "Regina", "Patricia", "Elena", "Mónica"]
APELLIDOS_MX = ["Hernández", "García", "Martínez", "López", "González", "Pérez", "Rodríguez", "Sánchez", "Ramírez",
                "Cruz", "Flores", "Gómez", "Morales", "Vázquez", "Reyes", "Jiménez", "Torres", "Díaz", "Gutiérrez",
                "Ruiz", "Mendoza", "Aguilar", "Ortiz", "Moreno", "Castillo", "Romero", "Álvarez", "Méndez", "Chávez",
                "Rivera", "Juárez", "Ramos", "Garza", "Treviño", "Villarreal", "Cantú", "Elizondo", "Salinas"]
NOMBRES_CO = ["Andrés", "Juan", "Carlos", "Santiago", "Felipe", "Camilo", "Sebastián", "Julián", "Mauricio", "Diego",
              "Alejandro", "Jorge", "Nicolás", "Daniel", "Óscar", "Hernán", "Esteban", "David", "Germán", "Luis",
              "Laura", "Natalia", "Catalina", "Paola", "Diana", "Carolina", "Juliana", "Valentina", "Ángela", "Marcela",
              "Andrea", "Lina", "Sandra", "Mónica", "Claudia", "Daniela", "Tatiana", "Viviana", "Liliana", "Paula"]
APELLIDOS_CO = ["Rodríguez", "Gómez", "González", "Martínez", "García", "López", "Hernández", "Sánchez", "Ramírez",
                "Pérez", "Díaz", "Muñoz", "Rojas", "Moreno", "Jiménez", "Vargas", "Castro", "Ortiz", "Restrepo",
                "Ospina", "Cárdenas", "Gutiérrez", "Suárez", "Arango", "Zapata", "Mejía", "Quintero", "Valencia",
                "Ríos", "Cardona", "Londoño", "Salazar", "Giraldo", "Correa", "Patiño"]

COSTO_BANCO = {
    "CEO": 620_000, "VP": 310_000, "Gerente General de Unidad": 280_000, "Gerente": 150_000,
    "Subgerente": 96_000, "Jefe": 64_000, "Coordinador": 42_000, "Supervisor": 26_000,
    "Líder de Grupo": 17_500, "Especialista": 52_000, "Analista": 30_000, "Ejecutivo de Cuenta": 46_000,
    "Ejecutivo": 21_000, "Agente": 11_000, "Cajero": 10_800, "Operador": 12_400, "Asistente": 11_500,
}
COSTO_RETAIL = {
    "CEO": 520_000, "VP": 240_000, "Gerente General de Unidad": 220_000, "Gerente": 115_000,
    "Subgerente": 74_000, "Jefe": 46_000, "Coordinador": 30_000, "Supervisor": 21_000,
    "Líder de Grupo": 11_800, "Encargado": 9_400, "Especialista": 40_000, "Analista": 22_000,
    "Colaborador": 7_300, "Operario": 8_600, "Chofer": 9_800, "Asistente": 9_500,
}
COSTO_TELECOM = {
    "CEO": 560_000, "VP": 260_000, "Gerente General de Unidad": 240_000, "Gerente": 130_000,
    "Subgerente": 84_000, "Jefe": 56_000, "Coordinador": 36_000, "Supervisor": 24_000,
    "Líder de Grupo": 16_000, "Especialista": 46_000, "Analista": 26_000, "Ejecutivo de Cuenta": 38_000,
    "Asesor": 12_000, "Técnico": 13_500, "Agente": 10_200, "Asistente": 10_000,
}


def _contact_center(o: Org, jefe_area, area, sedes):
    """Contact center con la cadena típica: jefe de turno → coordinador (un solo reporte) → supervisores →
    líderes de equipo → agentes. sedes = [(ciudad, subgerencias, turnos por subgerencia)]."""
    r = o.r
    for sede, n_sub, n_turnos in sedes:
        g = o.add(jefe_area, "Gerente", f"Gerente de Contact Center {sede}", area, f"Contact Center {sede}",
                  "contact_center", "gerencial", ubicacion=sede)
        for s in range(n_sub):
            sub = o.add(g, "Subgerente", f"Subgerente de Atención {s + 1} – {sede}", area, f"Contact Center {sede}",
                        "contact_center", "operativo", ubicacion=sede)
            for t in range(n_turnos):
                jt = o.add(sub, "Jefe", f"Jefe de Turno {t + 1}", area, f"Contact Center {sede}", "contact_center",
                           "operativo", ubicacion=sede)
                coord = o.add(jt, "Coordinador", "Coordinador de Turno", area, f"Contact Center {sede}",
                              "contact_center", "operativo", ubicacion=sede)
                for _ in range(r.choice([2, 3])):
                    sup = o.add(coord, "Supervisor", "Supervisor de Atención", area, f"Contact Center {sede}",
                                "contact_center", "operativo", ubicacion=sede)
                    for _ in range(r.choice([3, 4])):
                        lider = o.add(sup, "Líder de Grupo", "Líder de Equipo", area, f"Contact Center {sede}",
                                      "contact_center", "operativo", ubicacion=sede)
                        o.equipo(lider, r.randint(7, 10), "Agente", "Agente de Atención", area,
                                 f"Contact Center {sede}", "contact_center", "operativo", ubicacion=sede)


def _duplicadas_bu(o: Org, g_com, bu, caps):
    """Capacidades que cada unidad de negocio arma por su cuenta (problema plantado).
    caps = [(clave, nombre visible, tipo, forma)] con forma 'sub' (subgerente → jefe → analistas),
    'coord' (jefe → coordinador → analistas) o 'jefe' (jefe → analistas)."""
    r = o.r
    for clave, nombre, tipo, forma in caps:
        if forma == "sub":
            sub = o.add(g_com, "Subgerente", f"Subgerente de {nombre}", bu, nombre, clave, tipo)
            jefe = o.add(sub, "Jefe", f"Jefe de {nombre}", bu, nombre, clave, tipo)
            o.equipo(jefe, r.randint(2, 3), "Analista", f"Analista de {nombre}", bu, nombre, clave, tipo)
        elif forma == "coord":
            jefe = o.add(g_com, "Jefe", f"Jefe de {nombre}", bu, nombre, clave, tipo)
            coord = o.add(jefe, "Coordinador", f"Coordinador de {nombre}", bu, nombre, clave, tipo)
            o.equipo(coord, r.randint(3, 5), "Analista", f"Analista de {nombre}", bu, nombre, clave, tipo)
        else:
            jefe = o.add(g_com, "Jefe", f"Jefe de {nombre}", bu, nombre, clave, tipo)
            o.equipo(jefe, r.randint(2, 4), "Analista", f"Analista de {nombre}", bu, nombre, clave, tipo)


def _producto_bu(o: Org, gg, bu, corto, cats, caps):
    """Capacidades de producto de una unidad, repartidas por categoría. caps = (gestión, marketing, experiencia)
    con (clave, nombre visible, cargo del jefe)."""
    r = o.r
    (c1, n1, j1), (c2, n2, j2), (c3, n3, j3) = caps
    g = o.add(gg, "Gerente", f"Gerente de {n1} {corto}", bu, n1, c1, "gerencial")
    for cat in cats:
        sub = o.add(g, "Subgerente", f"Subgerente de {n1} {cat}", bu, n1, c1, "profesional", categoria=cat)
        for _ in range(2 if len(cats) > 1 else 3):  # unidades de una sola categoría: un product manager más
            jefe = o.add(sub, "Jefe", f"{j1} {cat}", bu, n1, c1, "profesional", categoria=cat)
            o.equipo(jefe, r.randint(2, 3), "Analista", f"Analista de {n1} {cat}", bu, n1, c1, "profesional",
                     categoria=cat)
    sub = o.add(gg, "Subgerente", f"Subgerente de {n2} {corto}", bu, n2, c2, "profesional")
    for cat in cats:
        jefe = o.add(sub, "Jefe", f"{j2} {cat}", bu, n2, c2, "profesional", categoria=cat)
        o.equipo(jefe, r.randint(2, 3), "Analista", f"Analista de {n2} {cat}", bu, n2, c2, "profesional",
                 categoria=cat)
    jefe = o.add(gg, "Jefe", f"{j3} {corto}", bu, n3, c3, "profesional", categoria=cats[0])
    for cat in cats:
        o.equipo(jefe, 2, "Analista", f"Analista de {n3} {cat}", bu, n3, c3, "profesional", categoria=cat)


def _finanzas_bu(o: Org, gg, bu):
    jefe = o.add(gg, "Jefe", "Jefe de Finanzas de Unidad", bu, "Finanzas de Unidad", "finanzas", "profesional")
    o.equipo(jefe, o.r.randint(2, 3), "Analista", "Analista Financiero", bu, "Finanzas de Unidad", "finanzas",
             "profesional")


# =========================================================================== Banco Cumbre (México)
CATEGORIAS_BANCO = {
    "Banca Empresarial": ["Crédito PyME", "Crédito Corporativo"],
    "Divisas y Pagos": ["Divisas", "Pagos Internacionales"],
    "Banca Patrimonial": ["Inversión Patrimonial"],
}


def construir_banco() -> list[dict]:
    o = Org(semilla=11, costo=COSTO_BANCO, nombres=NOMBRES_MX, apellidos=APELLIDOS_MX, ubicacion="CDMX")
    r = o.r
    ceo = o.add(None, "CEO", "Director General", "Dirección General", "Dirección General", "direccion", "gerencial")

    # ================= OPERACIONES Y SERVICIO =================
    A = "Operaciones y Servicio"
    vp = o.add(ceo, "VP", "Director Ejecutivo de Operaciones", A, "Dirección de Operaciones", "direccion", "gerencial")
    g_cc = o.add(vp, "Gerente", "Director de Contact Center", A, "Contact Center", "contact_center", "gerencial",
                 ubicacion="Monterrey")
    _contact_center(o, g_cc, A, [("Monterrey", 3, 3), ("Guadalajara", 1, 2)])
    g_op = o.add(vp, "Gerente", "Gerente de Procesamiento de Pagos y Divisas", A, "Procesamiento",
                 "operaciones_pagos", "gerencial")
    for sede, n_jefes in [("CDMX", 6), ("Monterrey", 3)]:
        sub = o.add(g_op, "Subgerente", f"Subgerente de Procesamiento {sede}", A, "Procesamiento",
                    "operaciones_pagos", "operativo", ubicacion=sede)
        for _ in range(n_jefes):
            jefe = o.add(sub, "Jefe", "Jefe de Mesa de Operación", A, "Procesamiento", "operaciones_pagos",
                         "operativo", ubicacion=sede)
            for _ in range(r.choice([2, 3])):
                sup = o.add(jefe, "Supervisor", "Supervisor de Procesamiento", A, "Procesamiento",
                            "operaciones_pagos", "operativo", ubicacion=sede)
                o.equipo(sup, r.randint(6, 9), "Operador", "Operador de Back Office", A, "Procesamiento",
                         "operaciones_pagos", "operativo", ubicacion=sede)
    g_cob = o.add(vp, "Gerente", "Gerente de Cobranza", A, "Cobranza", "cobranza", "gerencial")
    for sede, n_sup in [("CDMX", 5), ("Guadalajara", 3)]:
        sub = o.add(g_cob, "Subgerente", f"Subgerente de Cobranza {sede}", A, "Cobranza", "cobranza", "operativo",
                    ubicacion=sede)
        jefe = o.add(sub, "Jefe", f"Jefe de Cobranza {sede}", A, "Cobranza", "cobranza", "operativo", ubicacion=sede)
        for _ in range(n_sup):
            sup = o.add(jefe, "Supervisor", "Supervisor de Cobranza", A, "Cobranza", "cobranza", "operativo",
                        ubicacion=sede)
            o.equipo(sup, r.randint(7, 10), "Operador", "Gestor de Cobranza", A, "Cobranza", "cobranza", "operativo",
                     ubicacion=sede)
    sub = o.add(vp, "Subgerente", "Subgerente de Control Operativo", A, "Control Operativo", "control_operativo",
                "profesional")
    jefe = o.add(sub, "Jefe", "Jefe de Calidad Operativa", A, "Control Operativo", "control_operativo", "profesional")
    coord = o.add(jefe, "Coordinador", "Coordinador de Control Operativo", A, "Control Operativo",
                  "control_operativo", "profesional")
    o.equipo(coord, r.randint(7, 9), "Analista", "Analista de Control Operativo", A, "Control Operativo",
             "control_operativo", "profesional")
    sub = o.add(vp, "Subgerente", "Subgerente de Mesa de Control de Crédito", A, "Mesa de Control", "mesa_control",
                "profesional")
    for _ in range(2):
        jefe = o.add(sub, "Jefe", "Jefe de Mesa de Control", A, "Mesa de Control", "mesa_control", "profesional")
        o.equipo(jefe, r.randint(4, 6), "Analista", "Analista de Mesa de Control", A, "Mesa de Control",
                 "mesa_control", "profesional")

    # ================= RED DE SUCURSALES =================
    A = "Red de Sucursales"
    vp = o.add(ceo, "VP", "Director Ejecutivo de Red Comercial", A, "Dirección de Red", "direccion", "gerencial")
    for region, zonas, sucursales in [("Norte", 3, 5), ("Centro", 4, 5), ("Occidente", 2, 5), ("Sureste", 2, 4)]:
        g = o.add(vp, "Gerente", f"Director Regional {region}", A, f"Región {region}", "red_sucursales", "gerencial",
                  ubicacion=region)
        sub = o.add(g, "Subgerente", f"Subdirector Regional {region}", A, f"Región {region}", "red_sucursales",
                    "comercial_campo", ubicacion=region)
        for z in range(zonas):
            jz = o.add(sub, "Jefe", f"Gerente de Zona {region} {z + 1}", A, f"Región {region}", "red_sucursales",
                       "comercial_campo", ubicacion=region)
            for _ in range(sucursales):
                gs = o.add(jz, "Coordinador", "Gerente de Sucursal", A, f"Región {region}", "red_sucursales",
                           "comercial_campo", ubicacion=region)
                o.equipo(gs, r.randint(3, 5), "Ejecutivo", "Ejecutivo de Sucursal", A, f"Región {region}",
                         "red_sucursales", "comercial_campo", ubicacion=region)
                jc = o.add(gs, "Supervisor", "Jefe de Caja", A, f"Región {region}", "caja", "operativo",
                           ubicacion=region)
                o.equipo(jc, r.randint(3, 6), "Cajero", "Cajero", A, f"Región {region}", "caja", "operativo",
                         ubicacion=region)

    # ================= UNIDADES DE NEGOCIO =================
    sedes_relacion = {"Banca Empresarial": ["CDMX", "Monterrey"], "Divisas y Pagos": ["CDMX", "Guadalajara"],
                      "Banca Patrimonial": ["CDMX", "Monterrey"]}
    for bu, cats in CATEGORIAS_BANCO.items():
        gg = o.add(ceo, "Gerente General de Unidad", f"Director de {bu}", bu, "Dirección de Unidad", "direccion",
                   "gerencial")
        _producto_bu(o, gg, bu, bu, cats, [("gestion_producto", "Producto", "Product Manager"),
                                           ("marketing_segmento", "Marketing", "Jefe de Marketing"),
                                           ("experiencia_cliente", "Experiencia de Cliente", "Jefe de Experiencia de Cliente")])
        g_com = o.add(gg, "Gerente", f"Gerente Comercial {bu}", bu, "Comercial", "direccion", "gerencial")
        _duplicadas_bu(o, g_com, bu, [("pricing_tasas", "Pricing de Tasas y Comisiones", "especialista", "sub"),
                                      ("analytics", "Inteligencia Comercial", "especialista", "coord"),
                                      ("canales_digitales", "Canales Digitales", "especialista", "jefe"),
                                      ("originacion", "Originación de Crédito", "profesional", "sub")])
        sub = o.add(g_com, "Subgerente", "Subgerente de Banca de Relación", bu, "Banca de Relación", "banca_relacion",
                    "comercial_campo")
        for sede in sedes_relacion[bu]:
            jefe = o.add(sub, "Jefe", f"Gerente de Relación {sede}", bu, "Banca de Relación", "banca_relacion",
                         "comercial_campo", ubicacion=sede)
            o.equipo(jefe, r.randint(3, 5), "Ejecutivo de Cuenta", "Banquero de Relación", bu, "Banca de Relación",
                     "banca_relacion", "comercial_campo", ubicacion=sede)
        _finanzas_bu(o, gg, bu)

    # ================= FUNCIONES CORPORATIVAS =================
    funcion = lambda *a, **k: funcion_corporativa(o, ceo, *a, **k)
    funcion("Director de Riesgos", "Riesgos", "riesgos", [
        ("Gerente de Riesgo de Crédito", [("Subgerente de Admisión", 2, (4, 6)), ("Subgerente de Seguimiento", 1, (3, 5))]),
        ("Gerente de Riesgo de Mercado", [("Subgerente de Riesgo de Mercado y Liquidez", 1, (3, 4))]),
        ("Gerente de Riesgo Operacional", [("Subgerente de Prevención de Fraude", 2, (4, 6)), ("Subgerente de Riesgo Operacional", 1, (3, 4))]),
    ], tipo="especialista")
    funcion("Director de Finanzas", "Finanzas", "finanzas", [
        ("Gerente de Contabilidad", [("Subgerente de Contabilidad General", 2, (4, 6)), ("Subgerente de Impuestos", 1, (3, 4))]),
        ("Gerente de Tesorería", [("Subgerente de Tesorería", 1, (3, 5))]),
        ("Gerente de Planeación Financiera", [("Subgerente de Presupuesto", 1, (3, 4)), ("Subgerente de Control de Gestión", 1, (3, 5))]),
    ])
    funcion("Director de Capital Humano", "Gestión Humana", "rrhh", [
        ("Gerente de Talento", [("Subgerente de Atracción de Talento", 1, (3, 5)), ("Subgerente de Desarrollo", 1, (2, 4))]),
        ("Gerente de Compensaciones", [("Subgerente de Nómina", 1, (4, 6)), ("Subgerente de Beneficios", 1, (2, 3))]),
    ])
    funcion("Director de Tecnología", "Tecnología", "ti", [
        ("Gerente de Infraestructura", [("Subgerente de Operaciones TI", 2, (4, 6)), ("Subgerente de Ciberseguridad", 2, (3, 5))]),
        ("Gerente de Desarrollo", [("Subgerente de Core Bancario", 3, (4, 6)), ("Subgerente de Canales", 2, (4, 6))]),
    ], tipo="especialista")
    funcion("Director Jurídico y de Cumplimiento", "Cumplimiento y Legal", "legal", [
        ("Gerente de Cumplimiento", [("Subgerente de Prevención de Lavado de Dinero", 2, (3, 5)), ("Subgerente de Normatividad", 1, (2, 4))]),
        ("Gerente Jurídico", [("Subgerente de Contratos", 1, (2, 3)), ("Subgerente de Litigios", 1, (2, 3))]),
    ], tipo="especialista")
    return o.gente


# =========================================================================== Tiendas Esquina (México)
CATEGORIAS_RETAIL = {
    "BU Bebidas y Abarrotes": ["Bebidas", "Abarrotes y Botanas"],
    "BU Comida para Llevar": ["Comida para Llevar", "Café"],
    "BU Servicios y Pagos": ["Servicios y Pagos"],
}


def construir_retail() -> list[dict]:
    o = Org(semilla=23, costo=COSTO_RETAIL, nombres=NOMBRES_MX, apellidos=APELLIDOS_MX, ubicacion="Monterrey")
    r = o.r
    ceo = o.add(None, "CEO", "Director General", "Dirección General", "Dirección General", "direccion", "gerencial")

    # ================= OPERACIÓN DE TIENDAS =================
    A = "Operación de Tiendas"
    vp = o.add(ceo, "VP", "Director de Operación de Tiendas", A, "Dirección de Operación", "direccion", "gerencial")
    for region, plazas in [("Norte", [("Monterrey", 7), ("Saltillo", 3)]), ("Centro", [("CDMX", 6), ("Puebla", 3)]),
                           ("Occidente", [("Guadalajara", 4)])]:
        dr = o.add(vp, "Gerente", f"Director Regional {region}", A, f"Región {region}", "operacion_tiendas",
                   "gerencial", ubicacion=plazas[0][0])
        for plaza, distritos in plazas:
            gp = o.add(dr, "Gerente", f"Gerente de Plaza {plaza}", A, f"Plaza {plaza}", "operacion_tiendas",
                       "gerencial", ubicacion=plaza)
            sub = o.add(gp, "Subgerente", f"Subgerente de Operación {plaza}", A, f"Plaza {plaza}",
                        "operacion_tiendas", "operativo", ubicacion=plaza)
            for d in range(distritos):
                gd = o.add(sub, "Jefe", f"Gerente de Distrito {plaza} {d + 1}", A, f"Plaza {plaza}",
                           "operacion_tiendas", "operativo", ubicacion=plaza)
                for _ in range(r.choice([3, 4])):
                    asesor = o.add(gd, "Supervisor", "Asesor de Tiendas", A, f"Plaza {plaza}", "operacion_tiendas",
                                   "operativo", ubicacion=plaza)
                    for _ in range(r.choice([4, 5])):
                        lt = o.add(asesor, "Líder de Grupo", "Líder de Tienda", A, f"Plaza {plaza}",
                                   "operacion_tiendas", "operativo", ubicacion=plaza)
                        o.equipo(lt, r.randint(3, 5), "Colaborador", "Colaborador de Tienda", A, f"Plaza {plaza}",
                                 "operacion_tiendas", "operativo", ubicacion=plaza)
                        enc = o.add(lt, "Encargado", "Encargado de Turno Vespertino", A, f"Plaza {plaza}",
                                    "operacion_tiendas", "operativo", ubicacion=plaza)
                        o.equipo(enc, r.randint(2, 3), "Colaborador", "Colaborador de Tienda", A, f"Plaza {plaza}",
                                 "operacion_tiendas", "operativo", ubicacion=plaza)
        jefe = o.add(dr, "Jefe", f"Jefe de Prevención de Pérdidas {region}", A, f"Región {region}",
                     "prevencion_perdidas", "profesional", ubicacion=plazas[0][0])
        o.equipo(jefe, r.randint(4, 6), "Analista", "Auditor de Tiendas", A, f"Región {region}", "prevencion_perdidas",
                 "profesional", ubicacion=plazas[0][0])

    # ================= LOGÍSTICA =================
    A = "Logística"
    vp = o.add(ceo, "VP", "Director de Cadena de Suministro", A, "Dirección de Logística", "direccion", "gerencial")
    g = o.add(vp, "Gerente", "Gerente de Centros de Distribución", A, "CEDIS", "logistica", "gerencial")
    for cedis, n_sup in [("Monterrey", 5), ("CDMX", 5), ("Guadalajara", 3), ("Puebla", 3)]:
        sub = o.add(g, "Subgerente", f"Subgerente CEDIS {cedis}", A, "CEDIS", "logistica", "operativo", ubicacion=cedis)
        jefe = o.add(sub, "Jefe", f"Jefe de Almacén CEDIS {cedis}", A, "CEDIS", "logistica", "operativo",
                     ubicacion=cedis)
        for _ in range(n_sup):
            sup = o.add(jefe, "Supervisor", "Supervisor de Almacén", A, "CEDIS", "logistica", "operativo",
                        ubicacion=cedis)
            o.equipo(sup, r.randint(8, 12), "Operario", "Operario de Almacén", A, "CEDIS", "logistica", "operativo",
                     ubicacion=cedis)
    g = o.add(vp, "Gerente", "Gerente de Transporte", A, "Transporte", "transporte", "gerencial")
    for zona, n_sup in [("Norte", 4), ("Centro", 3)]:
        jefe = o.add(g, "Jefe", f"Jefe de Transporte {zona}", A, "Transporte", "transporte", "operativo",
                     ubicacion=zona)
        for _ in range(n_sup):
            sup = o.add(jefe, "Supervisor", "Supervisor de Rutas", A, "Transporte", "transporte", "operativo",
                        ubicacion=zona)
            o.equipo(sup, r.randint(6, 9), "Chofer", "Chofer Repartidor", A, "Transporte", "transporte", "operativo",
                     ubicacion=zona)
    g = o.add(vp, "Gerente", "Gerente de Abastecimiento", A, "Abastecimiento", "abastecimiento", "gerencial")
    for _ in range(3):
        jefe = o.add(g, "Jefe", "Jefe de Reabasto", A, "Abastecimiento", "abastecimiento", "profesional")
        o.equipo(jefe, r.randint(3, 5), "Analista", "Analista de Reabasto", A, "Abastecimiento", "abastecimiento",
                 "profesional")

    # ================= UNIDADES DE NEGOCIO =================
    for bu, cats in CATEGORIAS_RETAIL.items():
        corto = bu.replace("BU ", "")
        gg = o.add(ceo, "Gerente General de Unidad", f"Director de {corto}", bu, "Dirección de Unidad", "direccion",
                   "gerencial")
        _producto_bu(o, gg, bu, corto, cats, [("gestion_categoria", "Categoría", "Category Manager"),
                                              ("compras_comerciales", "Compras Comerciales", "Jefe de Compras"),
                                              ("marketing_categoria", "Marketing y Promociones", "Jefe de Marketing")])
        g_com = o.add(gg, "Gerente", f"Gerente Comercial {corto}", bu, "Comercial", "direccion", "gerencial")
        _duplicadas_bu(o, g_com, bu, [("pricing", "Pricing", "especialista", "sub"),
                                      ("analytics", "Inteligencia Comercial", "especialista", "coord"),
                                      ("lealtad_digital", "App y Lealtad", "especialista", "jefe"),
                                      ("espacio_surtido", "Espacio y Surtido", "profesional", "jefe"),
                                      ("abastecimiento", "Planeación de Demanda", "profesional", "jefe")])
        _finanzas_bu(o, gg, bu)

    # ================= FUNCIONES CORPORATIVAS =================
    funcion = lambda *a, **k: funcion_corporativa(o, ceo, *a, **k)
    funcion("Director de Expansión", "Expansión", "expansion", [
        ("Gerente de Bienes Raíces", [("Subgerente de Prospección de Sitios", 2, (4, 6))]),
        ("Gerente de Construcción", [("Subgerente de Obra", 2, (4, 6))]),
    ])
    funcion("Director de Finanzas", "Finanzas", "finanzas", [
        ("Gerente de Contabilidad", [("Subgerente de Contabilidad General", 2, (4, 6)), ("Subgerente de Impuestos", 1, (3, 4))]),
        ("Gerente de Tesorería", [("Subgerente de Tesorería", 1, (3, 5)), ("Subgerente de Control de Efectivo en Tiendas", 2, (4, 6))]),
        ("Gerente de Planeación Financiera", [("Subgerente de Presupuesto", 1, (3, 4))]),
    ])
    funcion("Director de Capital Humano", "Gestión Humana", "rrhh", [
        ("Gerente de Talento", [("Subgerente de Reclutamiento de Tiendas", 2, (4, 6)), ("Subgerente de Capacitación", 1, (3, 5))]),
        ("Gerente de Compensaciones", [("Subgerente de Nómina", 2, (4, 6))]),
        ("Gerente de Relaciones Laborales", [("Subgerente de Relaciones Laborales", 1, (3, 5))]),
    ])
    funcion("Director de Tecnología", "Tecnología", "ti", [
        ("Gerente de Infraestructura", [("Subgerente de Soporte a Tiendas", 2, (4, 6)), ("Subgerente de Ciberseguridad", 1, (3, 4))]),
        ("Gerente de Aplicaciones", [("Subgerente de Punto de Venta", 2, (3, 5)), ("Subgerente de ERP", 1, (3, 5))]),
    ], tipo="especialista")
    funcion("Director Jurídico", "Legal", "legal", [
        ("Gerente Legal", [("Subgerente de Contratos y Arrendamientos", 1, (3, 4)), ("Subgerente de Asuntos Regulatorios", 1, (2, 3))]),
    ], tipo="especialista")
    return o.gente


# =========================================================================== Cóndor Telecom (Colombia)
CATEGORIAS_TELECOM = {
    "BU Hogar": ["Internet Hogar", "TV y Entretenimiento"],
    "BU Móvil": ["Móvil Pospago", "Móvil Prepago"],
    "BU Empresas": ["Soluciones Empresariales"],
}


def construir_telecom() -> list[dict]:
    o = Org(semilla=31, costo=COSTO_TELECOM, nombres=NOMBRES_CO, apellidos=APELLIDOS_CO, ubicacion="Bogotá")
    r = o.r
    ceo = o.add(None, "CEO", "Presidente", "Dirección General", "Dirección General", "direccion", "gerencial")

    # ================= RED =================
    A = "Red"
    vp = o.add(ceo, "VP", "Vicepresidente de Red", A, "Vicepresidencia de Red", "direccion", "gerencial")
    g = o.add(vp, "Gerente", "Gerente Nacional de Operación y Mantenimiento", A, "Mantenimiento de Red",
              "mantenimiento_red", "gerencial")
    for region, n_sub, n_cuad in [("Bogotá", 2, 3), ("Medellín", 2, 2), ("Cali", 1, 3), ("Barranquilla", 1, 2),
                                  ("Bucaramanga", 1, 2)]:
        gr = o.add(g, "Gerente", f"Gerente Regional de Red {region}", A, "Mantenimiento de Red", "mantenimiento_red",
                   "gerencial", ubicacion=region)
        for s in range(n_sub):
            sub = o.add(gr, "Subgerente", f"Subgerente de Operación de Red {s + 1} – {region}", A,
                        "Mantenimiento de Red", "mantenimiento_red", "operativo", ubicacion=region)
            for c in range(n_cuad):
                jefe = o.add(sub, "Jefe", f"Jefe de Cuadrillas {c + 1}", A, "Mantenimiento de Red",
                             "mantenimiento_red", "operativo", ubicacion=region)
                coord = o.add(jefe, "Coordinador", "Coordinador de Despacho", A, "Mantenimiento de Red",
                              "mantenimiento_red", "operativo", ubicacion=region)
                for _ in range(r.choice([2, 3])):
                    sup = o.add(coord, "Supervisor", "Supervisor de Campo", A, "Mantenimiento de Red",
                                "mantenimiento_red", "operativo", ubicacion=region)
                    for _ in range(r.choice([2, 3])):
                        lider = o.add(sup, "Líder de Grupo", "Líder de Cuadrilla", A, "Mantenimiento de Red",
                                      "mantenimiento_red", "operativo", ubicacion=region)
                        o.equipo(lider, r.randint(4, 6), "Técnico", "Técnico de Red", A, "Mantenimiento de Red",
                                 "mantenimiento_red", "operativo", ubicacion=region)
    g = o.add(vp, "Gerente", "Gerente del Centro de Operación de Red", A, "NOC", "noc", "gerencial")
    for turno in ("Día", "Noche"):
        sub = o.add(g, "Subgerente", f"Subgerente de Monitoreo {turno}", A, "NOC", "noc", "especialista")
        for _ in range(2):
            jefe = o.add(sub, "Jefe", "Jefe de Monitoreo", A, "NOC", "noc", "especialista")
            o.equipo(jefe, r.randint(4, 6), "Especialista", "Ingeniero de Monitoreo", A, "NOC", "noc", "especialista")
    g = o.add(vp, "Gerente", "Gerente de Despliegue de Fibra", A, "Despliegue", "despliegue", "gerencial")
    for zona in ("Centro", "Occidente"):
        sub = o.add(g, "Subgerente", f"Subgerente de Despliegue {zona}", A, "Despliegue", "despliegue", "profesional")
        for _ in range(2):
            jefe = o.add(sub, "Jefe", "Jefe de Proyectos de Fibra", A, "Despliegue", "despliegue", "profesional")
            o.equipo(jefe, r.randint(3, 5), "Analista", "Ingeniero de Proyectos", A, "Despliegue", "despliegue",
                     "profesional")

    # ================= SERVICIO AL CLIENTE =================
    A = "Servicio al Cliente"
    vp = o.add(ceo, "VP", "Vicepresidente de Servicio al Cliente", A, "Vicepresidencia de Servicio", "direccion",
               "gerencial")
    g_cc = o.add(vp, "Gerente", "Gerente de Contact Center", A, "Contact Center", "contact_center", "gerencial")
    _contact_center(o, g_cc, A, [("Bogotá", 3, 3), ("Medellín", 1, 2)])
    g = o.add(vp, "Gerente", "Gerente de Instalaciones y Soporte en Hogar", A, "Instalaciones", "instalaciones",
              "gerencial")
    for ciudad, n_jefes in [("Bogotá", 4), ("Medellín", 3), ("Cali", 2), ("Barranquilla", 2), ("Bucaramanga", 1)]:
        sub = o.add(g, "Subgerente", f"Subgerente de Instalaciones {ciudad}", A, "Instalaciones", "instalaciones",
                    "operativo", ubicacion=ciudad)
        for _ in range(n_jefes):
            jefe = o.add(sub, "Jefe", "Jefe de Instalaciones", A, "Instalaciones", "instalaciones", "operativo",
                         ubicacion=ciudad)
            for _ in range(r.choice([2, 3])):
                sup = o.add(jefe, "Supervisor", "Supervisor de Instaladores", A, "Instalaciones", "instalaciones",
                            "operativo", ubicacion=ciudad)
                o.equipo(sup, r.randint(6, 9), "Técnico", "Técnico Instalador", A, "Instalaciones", "instalaciones",
                         "operativo", ubicacion=ciudad)

    # ================= VENTAS MASIVAS =================
    A = "Ventas Masivas"
    vp = o.add(ceo, "VP", "Vicepresidente de Ventas Masivas", A, "Vicepresidencia de Ventas", "direccion", "gerencial")
    for region, zonas in [("Bogotá", 4), ("Antioquia", 3), ("Pacífico", 2), ("Caribe", 2), ("Santanderes", 1)]:
        gr = o.add(vp, "Gerente", f"Gerente Regional de Ventas {region}", A, f"Región {region}", "ventas_masivas",
                   "gerencial", ubicacion=region)
        sub = o.add(gr, "Subgerente", f"Subgerente Comercial {region}", A, f"Región {region}", "ventas_masivas",
                    "comercial_campo", ubicacion=region)
        for z in range(zonas):
            jefe = o.add(sub, "Jefe", f"Jefe de Zona {region} {z + 1}", A, f"Región {region}", "ventas_masivas",
                         "comercial_campo", ubicacion=region)
            for _ in range(r.choice([2, 3])):
                sup = o.add(jefe, "Supervisor", "Supervisor de Ventas", A, f"Región {region}", "ventas_masivas",
                            "comercial_campo", ubicacion=region)
                o.equipo(sup, r.randint(6, 9), "Asesor", "Asesor Comercial", A, f"Región {region}", "ventas_masivas",
                         "comercial_campo", ubicacion=region)

    # ================= UNIDADES DE NEGOCIO =================
    for bu, cats in CATEGORIAS_TELECOM.items():
        corto = bu.replace("BU ", "")
        gg = o.add(ceo, "Gerente General de Unidad", f"Vicepresidente {corto}", bu, "Dirección de Unidad", "direccion",
                   "gerencial")
        _producto_bu(o, gg, bu, corto, cats, [("gestion_producto", "Producto", "Product Manager"),
                                              ("marketing_producto", "Marketing", "Jefe de Marketing"),
                                              ("experiencia_cliente", "Experiencia de Cliente", "Jefe de Experiencia de Cliente")])
        g_com = o.add(gg, "Gerente", f"Gerente Comercial {corto}", bu, "Comercial", "direccion", "gerencial")
        _duplicadas_bu(o, g_com, bu, [("pricing", "Pricing y Ofertas", "especialista", "sub"),
                                      ("analytics", "Inteligencia Comercial", "especialista", "coord"),
                                      ("digital", "Canales Digitales", "especialista", "jefe"),
                                      ("retencion", "Retención", "profesional", "jefe")])
        if corto in ("Móvil", "Empresas"):
            sub = o.add(g_com, "Subgerente", "Subgerente de Cuentas Empresariales", bu, "Ventas a Empresas",
                        "ventas_empresas", "comercial_campo")
            for sede in (["Bogotá", "Medellín"] if corto == "Empresas" else ["Bogotá"]):
                jefe = o.add(sub, "Jefe", f"Key Account Manager {sede}", bu, "Ventas a Empresas", "ventas_empresas",
                             "comercial_campo", ubicacion=sede)
                o.equipo(jefe, r.randint(4, 6), "Ejecutivo de Cuenta", "Ejecutivo de Cuenta Empresarial", bu,
                         "Ventas a Empresas", "ventas_empresas", "comercial_campo", ubicacion=sede)
        _finanzas_bu(o, gg, bu)

    # ================= FUNCIONES CORPORATIVAS =================
    funcion = lambda *a, **k: funcion_corporativa(o, ceo, *a, **k)
    funcion("Vicepresidente Financiero", "Finanzas", "finanzas", [
        ("Gerente de Contabilidad", [("Subgerente de Contabilidad General", 2, (4, 6)), ("Subgerente de Impuestos", 1, (3, 4))]),
        ("Gerente de Tesorería", [("Subgerente de Tesorería", 1, (3, 5)), ("Subgerente de Facturación y Cartera", 2, (4, 6))]),
        ("Gerente de Planeación Financiera", [("Subgerente de Presupuesto", 1, (3, 4))]),
    ])
    funcion("Vicepresidente de Gestión Humana", "Gestión Humana", "rrhh", [
        ("Gerente de Talento", [("Subgerente de Selección", 1, (3, 5)), ("Subgerente de Desarrollo", 1, (2, 4))]),
        ("Gerente de Compensaciones", [("Subgerente de Nómina", 2, (4, 6))]),
        ("Gerente de Seguridad y Salud en el Trabajo", [("Subgerente de Seguridad en Campo", 2, (3, 5))]),
    ])
    funcion("Vicepresidente de Tecnología", "Tecnología", "ti", [
        ("Gerente de Sistemas de Negocio", [("Subgerente de Facturación", 2, (4, 6)), ("Subgerente de CRM", 2, (3, 5))]),
        ("Gerente de Infraestructura TI", [("Subgerente de Operaciones TI", 1, (4, 6)), ("Subgerente de Ciberseguridad", 1, (3, 5))]),
    ], tipo="especialista")
    funcion("Vicepresidente de Asuntos Regulatorios y Legales", "Regulatorio y Legal", "legal", [
        ("Gerente Regulatorio", [("Subgerente de Espectro y Licencias", 1, (2, 4)), ("Subgerente de Protección al Usuario", 1, (3, 4))]),
        ("Gerente Legal", [("Subgerente de Contratos", 1, (2, 3))]),
    ], tipo="especialista")
    return o.gente


CONSTRUCTORES = {"cpg": construir, "banco": construir_banco, "retail": construir_retail, "telecom": construir_telecom}


def ruta_datos(empresa: str, ext: str = "json") -> str:
    # la CPG conserva el nombre de archivo original
    nombre = "org_asis" if empresa == "cpg" else f"org_{empresa}"
    return os.path.join(RAIZ, "data", f"{nombre}.{ext}")


def generar(empresa: str) -> list[dict]:
    gente = CONSTRUCTORES[empresa]()
    os.makedirs(os.path.join(RAIZ, "data"), exist_ok=True)
    with open(ruta_datos(empresa), "w", encoding="utf-8") as f:
        json.dump(gente, f, ensure_ascii=False)
    with open(ruta_datos(empresa, "csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(gente[0].keys()))
        w.writeheader()
        w.writerows(gente)
    return gente


def main() -> None:
    for e in CONSTRUCTORES:
        print(f"{e}: {len(generar(e))} personas generadas")


if __name__ == "__main__":
    main()
