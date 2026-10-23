"""Las cuatro organizaciones de la demo (todas FICTICIAS, con datos sintéticos).

Cada empresa define su vocabulario: capacidades, categorías de producto, grupos de áreas,
qué no debe mezclarse en un bloque, el brief del CEO, el perfil del CHRO y el guion de respaldo.
El motor (app/motor.py) y los agentes (app/agentes.py) son los mismos para las cuatro.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app import generar_org as G


@dataclass(frozen=True)
class Empresa:
    id: str
    nombre: str                 # nombre legal visible
    corto: str                  # para el breadcrumb y los títulos
    iniciales: str
    pais: str
    sector: str
    descripcion: str            # una línea para la tarjeta de selección
    capacidades: dict           # clave → nombre visible
    cap_producto: frozenset     # capacidades que viven dentro de los equipos de producto
    categorias: list            # líneas de producto (cada una va en un solo equipo de producto)
    etiqueta_categoria: str     # "categoría", "línea de negocio"…
    grupos_area: dict           # área → grupo (4 grupos; el último es "Funciones corporativas")
    orden_grupos: list
    abrev: dict                 # área → abreviatura para la matriz
    tipos: dict                 # tipo de trabajo → etiqueta
    pares_incompatibles: list   # [(capacidad A, capacidad B, "descripción")]: no deben ir en el mismo bloque
    riesgo_operativo: str       # plantilla con {s}: tramo operativo por encima de 15
    bloque_operativo: str       # dónde vive ese riesgo
    factor_costo: float         # escala del costo de las jefaturas nuevas
    caso: str                   # brief del CEO, plantilla con {personas}
    productos_txt: str
    plataformas_txt: str
    habilitadores_txt: str
    regla_separar: str
    chro_perfil: str
    modelo_respaldo: dict
    guion: dict = field(default_factory=dict)

    @property
    def grupo_unidades(self) -> str:
        return self.orden_grupos[2]

    def grupo(self, area: str) -> str:
        return self.grupos_area.get(area, self.orden_grupos[-1])

    def es_unidad(self, area: str) -> bool:
        return self.grupos_area.get(area) == self.grupo_unidades

    def construir(self) -> list[dict]:
        return G.CONSTRUCTORES[self.id]()


TIPOS_BASE = {"operativo": "Operativo", "comercial_campo": "Comercial de campo", "profesional": "Profesional",
              "especialista": "Especialista"}

# =========================================================================== Consumo Andino (CPG, Perú)
CPG = Empresa(
    id="cpg", nombre="Consumo Andino S.A.A.", corto="Consumo Andino", iniciales="CA", pais="Perú",
    sector="Consumo masivo",
    descripcion="Alimentos, bebidas y cuidado del hogar · 3 plantas y fuerza de ventas propia",
    capacidades={
        "manufactura": "Manufactura", "mantenimiento": "Mantenimiento", "calidad": "Calidad",
        "logistica": "Logística", "compras": "Compras", "planeamiento_suministro": "Planeamiento de suministro",
        "planeamiento_demanda": "Planeamiento de demanda", "ventas_tradicional": "Ventas canal tradicional",
        "ventas_moderno": "Ventas canal moderno (key accounts)", "trade_marketing": "Trade marketing",
        "pricing_rgm": "Pricing y RGM", "analytics": "Analytics e inteligencia comercial",
        "digital_ecommerce": "Digital y e-commerce", "marketing_marca": "Marketing de marca",
        "innovacion": "Innovación e I+D", "category_management": "Category management",
        "finanzas": "Finanzas", "rrhh": "Gestión humana", "ti": "Tecnología", "legal": "Legal y asuntos corporativos",
    },
    cap_producto=frozenset({"marketing_marca", "innovacion", "category_management"}),
    categorias=["Galletas", "Pastas y Harinas", "Salsas y Condimentos", "Bebidas", "Cuidado del Hogar"],
    etiqueta_categoria="categoría",
    grupos_area={"Supply Chain": "Supply Chain", "Ventas Canal Tradicional": "Fuerza de ventas",
                 "BU Alimentos": "Unidades de negocio", "BU Bebidas": "Unidades de negocio",
                 "BU Cuidado del Hogar": "Unidades de negocio"},
    orden_grupos=["Supply Chain", "Fuerza de ventas", "Unidades de negocio", "Funciones corporativas"],
    abrev={"Supply Chain": "Supply", "Ventas Canal Tradicional": "Ventas CT", "BU Alimentos": "BU Alim.",
           "BU Cuidado del Hogar": "BU Hogar", "BU Bebidas": "BU Bebidas", "Gestión Humana": "G. Humana",
           "Legal y Asuntos Corporativos": "Legal"},
    tipos={**TIPOS_BASE, "operativo": "Operativo (plantas y almacenes)"},
    pares_incompatibles=[("manufactura", "logistica", "plantas y distribución")],
    riesgo_operativo="Un supervisor de planta con {s} operarios por turno compromete la seguridad industrial; "
                     "en plantas de alimentos el estándar ronda 12-15.",
    bloque_operativo="Plantas", factor_costo=1.0,
    caso="Cliente: Consumo Andino S.A.A. (empresa FICTICIA de consumo masivo en Perú, {personas:,} colaboradores; "
         "plantas en Lima, Arequipa y Trujillo; categorías Galletas, Pastas y Harinas, Salsas y Condimentos, "
         "Bebidas y Cuidado del Hogar). Hoy tiene tres unidades de negocio con capacidades duplicadas, "
         "funciones corporativas y una gran operación de plantas y fuerza de ventas. "
         "El CEO pide: (1) pasar a un modelo producto-plataforma, (2) máximo 7 capas, (3) subir los tramos "
         "de control, sin comprometer la seguridad en planta ni la cobertura comercial.",
    productos_txt="equipos por categoría con marketing de marca, innovación y category management",
    plataformas_txt="supply, go-to-market, datos y RGM, digital, etc.",
    habilitadores_txt="finanzas, gestión humana, tecnología, legal",
    regla_separar="no pongas plantas (manufactura) y distribución (logística) en el mismo bloque",
    chro_perfil="con experiencia en plantas y fuerza de ventas",
    modelo_respaldo={
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
    },
    guion={
        "plataformas_r1": [
            {"nombre": "Supply Chain", "descripcion": "Plantas, logística, compras y planeamiento integrado",
             "capacidades": ["manufactura", "mantenimiento", "calidad", "logistica", "compras", "planeamiento_suministro", "planeamiento_demanda"]},
            {"nombre": "Go-to-Market", "descripcion": "Canal tradicional, canal moderno y trade marketing",
             "capacidades": ["ventas_tradicional", "ventas_moderno", "trade_marketing"]},
            {"nombre": "RGM y Analytics", "descripcion": "Pricing, promociones e inteligencia comercial",
             "capacidades": ["pricing_rgm", "analytics"]},
            {"nombre": "Comercio Digital", "descripcion": "E-commerce y canales digitales", "capacidades": ["digital_ecommerce"]}],
        "per_op": "operarios", "riesgo_corto": "compromete la seguridad en planta",
        "separar": "plantas de distribución", "cubierto": "La seguridad en planta está cubierta",
        "condiciones": ["Definir con cada planta el plan de transición de líderes de grupo a supervisores.",
                        "Acordar los niveles de servicio entre productos y plataformas antes del lanzamiento."],
    },
)

# =========================================================================== Banco Cumbre (banca, México)
BANCO = Empresa(
    id="banco", nombre="Banco Cumbre", corto="Banco Cumbre", iniciales="BC", pais="México", sector="Banca",
    descripcion="Banco enfocado en empresas · crédito, divisas y banca patrimonial",
    capacidades={
        "contact_center": "Contact center", "operaciones_pagos": "Procesamiento de pagos y divisas",
        "cobranza": "Cobranza", "control_operativo": "Control operativo", "mesa_control": "Mesa de control de crédito",
        "red_sucursales": "Venta en sucursales", "caja": "Caja y servicio en sucursal",
        "banca_relacion": "Banca de relación (empresas)", "originacion": "Originación de crédito",
        "pricing_tasas": "Pricing de tasas y comisiones", "analytics": "Analytics e inteligencia comercial",
        "canales_digitales": "Canales digitales", "gestion_producto": "Gestión de producto",
        "marketing_segmento": "Marketing de segmento", "experiencia_cliente": "Experiencia de cliente",
        "riesgos": "Riesgos", "finanzas": "Finanzas", "rrhh": "Capital humano", "ti": "Tecnología",
        "legal": "Cumplimiento y legal",
    },
    cap_producto=frozenset({"gestion_producto", "marketing_segmento", "experiencia_cliente"}),
    categorias=["Crédito PyME", "Crédito Corporativo", "Divisas", "Pagos Internacionales", "Inversión Patrimonial"],
    etiqueta_categoria="línea de negocio",
    grupos_area={"Operaciones y Servicio": "Operaciones", "Red de Sucursales": "Red de sucursales",
                 "Banca Empresarial": "Unidades de negocio", "Divisas y Pagos": "Unidades de negocio",
                 "Banca Patrimonial": "Unidades de negocio"},
    orden_grupos=["Operaciones", "Red de sucursales", "Unidades de negocio", "Funciones corporativas"],
    abrev={"Operaciones y Servicio": "Operaciones", "Red de Sucursales": "Sucursales",
           "Banca Empresarial": "B. Empresas", "Divisas y Pagos": "Divisas", "Banca Patrimonial": "B. Patrim.",
           "Gestión Humana": "C. Humano", "Cumplimiento y Legal": "Cumplim."},
    tipos={**TIPOS_BASE, "operativo": "Operativo (caja, back office y contact center)",
           "comercial_campo": "Comercial (sucursales y banca de relación)"},
    pares_incompatibles=[("caja", "contact_center", "sucursales y operaciones centrales")],
    riesgo_operativo="Un supervisor con {s} agentes o cajeros no alcanza a revisar calidad ni a detectar fraude; "
                     "en servicios financieros el estándar ronda 12-15.",
    bloque_operativo="Caja y contact center", factor_costo=1.25,
    caso="Cliente: Banco Cumbre (banco FICTICIO de México enfocado en empresas, {personas:,} colaboradores; "
         "contact centers en Monterrey y Guadalajara, 53 sucursales en cuatro regiones y back office en CDMX; "
         "líneas de negocio Crédito PyME, Crédito Corporativo, Divisas, Pagos Internacionales e Inversión "
         "Patrimonial). Hoy tiene tres unidades de negocio con capacidades duplicadas, funciones corporativas y "
         "una gran operación de sucursales, contact center y back office. El CEO pide: (1) pasar a un modelo "
         "producto-plataforma, (2) máximo 7 capas, (3) subir los tramos de control, sin debilitar el control "
         "operativo, la prevención de fraude ni la atención al cliente.",
    productos_txt="equipos por línea de negocio con gestión de producto, marketing de segmento y experiencia de cliente",
    plataformas_txt="red de sucursales, operaciones centrales, banca de relación y crédito, datos y pricing, etc.",
    habilitadores_txt="riesgos, finanzas, capital humano, tecnología, cumplimiento y legal",
    regla_separar="no pongas las sucursales (caja y venta en sucursal) y las operaciones centrales (contact center, "
                  "procesamiento y cobranza) en el mismo bloque",
    chro_perfil="con experiencia en operación bancaria, sucursales y contact center",
    modelo_respaldo={
        "productos": [{"nombre": "Crédito Empresarial", "categorias": ["Crédito PyME", "Crédito Corporativo"]},
                      {"nombre": "Divisas y Pagos", "categorias": ["Divisas", "Pagos Internacionales"]},
                      {"nombre": "Inversión Patrimonial", "categorias": ["Inversión Patrimonial"]}],
        "plataformas": [{"nombre": "Red de Sucursales", "capacidades": ["red_sucursales", "caja"]},
                        {"nombre": "Operaciones Centrales", "capacidades": ["contact_center", "operaciones_pagos", "cobranza", "control_operativo", "mesa_control"]},
                        {"nombre": "Banca de Relación y Crédito", "capacidades": ["banca_relacion", "originacion"]},
                        {"nombre": "Datos, Pricing y Digital", "capacidades": ["pricing_tasas", "analytics", "canales_digitales"]}],
        "habilitadores": [{"nombre": "Riesgos", "capacidades": ["riesgos"]}, {"nombre": "Finanzas", "capacidades": ["finanzas"]},
                          {"nombre": "Capital Humano", "capacidades": ["rrhh"]}, {"nombre": "Tecnología", "capacidades": ["ti"]},
                          {"nombre": "Cumplimiento y Legal", "capacidades": ["legal"]}],
    },
    guion={
        "plataformas_r1": [
            {"nombre": "Operaciones y Red", "descripcion": "Sucursales, contact center, back office y cobranza",
             "capacidades": ["red_sucursales", "caja", "contact_center", "operaciones_pagos", "cobranza", "control_operativo", "mesa_control"]},
            {"nombre": "Banca de Relación y Crédito", "descripcion": "Banqueros de empresas y originación",
             "capacidades": ["banca_relacion", "originacion"]},
            {"nombre": "Pricing y Analytics", "descripcion": "Tasas, comisiones e inteligencia comercial",
             "capacidades": ["pricing_tasas", "analytics"]},
            {"nombre": "Canales Digitales", "descripcion": "Banca en línea y app", "capacidades": ["canales_digitales"]}],
        "per_op": "agentes y cajeros", "riesgo_corto": "debilita el control de calidad y de fraude",
        "separar": "sucursales de operaciones centrales", "cubierto": "El control en caja y contact center está cubierto",
        "condiciones": ["Validar con Riesgos y Cumplimiento los nuevos tramos en caja y contact center.",
                        "Acordar los niveles de servicio entre productos y plataformas antes del lanzamiento."],
    },
)

# =========================================================================== Tiendas Esquina (retail, México)
RETAIL = Empresa(
    id="retail", nombre="Tiendas Esquina", corto="Tiendas Esquina", iniciales="TE", pais="México",
    sector="Retail de proximidad",
    descripcion="Cadena de tiendas de conveniencia · 5 plazas y 4 centros de distribución",
    capacidades={
        "operacion_tiendas": "Operación de tiendas", "prevencion_perdidas": "Prevención de pérdidas",
        "logistica": "Centros de distribución (CEDIS)", "transporte": "Transporte y reparto",
        "abastecimiento": "Abastecimiento y planeación de demanda", "expansion": "Expansión y bienes raíces",
        "gestion_categoria": "Gestión de categoría", "compras_comerciales": "Compras comerciales",
        "marketing_categoria": "Marketing y promociones", "pricing": "Pricing",
        "analytics": "Analytics e inteligencia comercial", "lealtad_digital": "App y lealtad",
        "espacio_surtido": "Espacio y surtido", "finanzas": "Finanzas", "rrhh": "Capital humano",
        "ti": "Tecnología", "legal": "Legal",
    },
    cap_producto=frozenset({"gestion_categoria", "compras_comerciales", "marketing_categoria"}),
    categorias=["Bebidas", "Abarrotes y Botanas", "Comida para Llevar", "Café", "Servicios y Pagos"],
    etiqueta_categoria="categoría",
    grupos_area={"Operación de Tiendas": "Operación de tiendas", "Logística": "Logística",
                 "BU Bebidas y Abarrotes": "Unidades de negocio", "BU Comida para Llevar": "Unidades de negocio",
                 "BU Servicios y Pagos": "Unidades de negocio"},
    orden_grupos=["Operación de tiendas", "Logística", "Unidades de negocio", "Funciones corporativas"],
    abrev={"Operación de Tiendas": "Tiendas", "BU Bebidas y Abarrotes": "BU Bebidas",
           "BU Comida para Llevar": "BU Comida", "BU Servicios y Pagos": "BU Servicios",
           "Gestión Humana": "C. Humano"},
    tipos={**TIPOS_BASE, "operativo": "Operativo (tiendas, CEDIS y reparto)"},
    pares_incompatibles=[("operacion_tiendas", "logistica", "tiendas y centros de distribución")],
    riesgo_operativo="Un supervisor con {s} colaboradores de tienda pierde el control de mermas y del servicio; "
                     "en tiendas de proximidad el estándar ronda 12-15.",
    bloque_operativo="Tiendas", factor_costo=0.9,
    caso="Cliente: Tiendas Esquina (cadena FICTICIA de tiendas de conveniencia en México, {personas:,} "
         "colaboradores; unas 360 tiendas en Monterrey, Saltillo, CDMX, Puebla y Guadalajara, y cuatro centros de "
         "distribución; categorías Bebidas, Abarrotes y Botanas, Comida para Llevar, Café, y Servicios y Pagos). "
         "Hoy tiene tres unidades de negocio con capacidades duplicadas, funciones corporativas y una gran "
         "operación de tiendas y logística. El CEO pide: (1) pasar a un modelo producto-plataforma, (2) máximo "
         "7 capas, (3) subir los tramos de control, sin perder el control de las tiendas ni el abasto.",
    productos_txt="equipos por categoría con gestión de categoría, compras comerciales y marketing y promociones",
    plataformas_txt="operación de tiendas, cadena de suministro, datos y pricing, lealtad, expansión, etc.",
    habilitadores_txt="finanzas, capital humano, tecnología, legal",
    regla_separar="no pongas la operación de tiendas y los centros de distribución (logística) en el mismo bloque",
    chro_perfil="con experiencia en operación de tiendas y centros de distribución",
    modelo_respaldo={
        "productos": [{"nombre": "Bebidas y Abarrotes", "categorias": ["Bebidas", "Abarrotes y Botanas"]},
                      {"nombre": "Comida para Llevar", "categorias": ["Comida para Llevar", "Café"]},
                      {"nombre": "Servicios y Pagos", "categorias": ["Servicios y Pagos"]}],
        "plataformas": [{"nombre": "Operación de Tiendas", "capacidades": ["operacion_tiendas", "prevencion_perdidas"]},
                        {"nombre": "Cadena de Suministro", "capacidades": ["logistica", "transporte", "abastecimiento"]},
                        {"nombre": "Datos, Pricing y Lealtad", "capacidades": ["pricing", "analytics", "lealtad_digital", "espacio_surtido"]},
                        {"nombre": "Expansión", "capacidades": ["expansion"]}],
        "habilitadores": [{"nombre": "Finanzas", "capacidades": ["finanzas"]}, {"nombre": "Capital Humano", "capacidades": ["rrhh"]},
                          {"nombre": "Tecnología", "capacidades": ["ti"]}, {"nombre": "Legal", "capacidades": ["legal"]}],
    },
    guion={
        "plataformas_r1": [
            {"nombre": "Operaciones y Logística", "descripcion": "Tiendas, CEDIS, reparto y abastecimiento",
             "capacidades": ["operacion_tiendas", "prevencion_perdidas", "logistica", "transporte", "abastecimiento"]},
            {"nombre": "Pricing y Surtido", "descripcion": "Precios, promociones y planogramas",
             "capacidades": ["pricing", "analytics", "espacio_surtido"]},
            {"nombre": "App y Lealtad", "descripcion": "Programa de lealtad y app", "capacidades": ["lealtad_digital"]},
            {"nombre": "Expansión", "descripcion": "Nuevas tiendas", "capacidades": ["expansion"]}],
        "per_op": "colaboradores de tienda", "riesgo_corto": "deja las tiendas sin control de mermas",
        "separar": "tiendas de centros de distribución", "cubierto": "La operación de tiendas está cubierta",
        "condiciones": ["Probar el nuevo tramo de asesores en una plaza piloto antes de escalar.",
                        "Acordar los niveles de servicio entre categorías y plataformas antes del lanzamiento."],
    },
)

# =========================================================================== Cóndor Telecom (telecom, Colombia)
TELECOM = Empresa(
    id="telecom", nombre="Cóndor Telecom", corto="Cóndor Telecom", iniciales="CT", pais="Colombia",
    sector="Telecomunicaciones",
    descripcion="Internet, TV y móvil · red propia, cuadrillas y contact center",
    capacidades={
        "mantenimiento_red": "Mantenimiento de red", "noc": "Centro de operación de red (NOC)",
        "despliegue": "Despliegue de fibra", "instalaciones": "Instalaciones en hogar",
        "contact_center": "Contact center", "ventas_masivas": "Ventas masivas",
        "ventas_empresas": "Ventas a empresas (KAM)", "retencion": "Retención y fidelización",
        "pricing": "Pricing y ofertas", "analytics": "Analytics e inteligencia comercial",
        "digital": "Canales digitales", "gestion_producto": "Gestión de producto",
        "marketing_producto": "Marketing de producto", "experiencia_cliente": "Experiencia de cliente",
        "finanzas": "Finanzas", "rrhh": "Gestión humana", "ti": "Tecnología", "legal": "Regulatorio y legal",
    },
    cap_producto=frozenset({"gestion_producto", "marketing_producto", "experiencia_cliente"}),
    categorias=["Internet Hogar", "TV y Entretenimiento", "Móvil Pospago", "Móvil Prepago", "Soluciones Empresariales"],
    etiqueta_categoria="línea de producto",
    grupos_area={"Red": "Red y servicio", "Servicio al Cliente": "Red y servicio",
                 "Ventas Masivas": "Fuerza de ventas", "BU Hogar": "Unidades de negocio",
                 "BU Móvil": "Unidades de negocio", "BU Empresas": "Unidades de negocio"},
    orden_grupos=["Red y servicio", "Fuerza de ventas", "Unidades de negocio", "Funciones corporativas"],
    abrev={"Servicio al Cliente": "Servicio", "Ventas Masivas": "Ventas", "Gestión Humana": "G. Humana",
           "Regulatorio y Legal": "Regulat."},
    tipos={**TIPOS_BASE, "operativo": "Operativo (cuadrillas, instaladores y contact center)",
           "comercial_campo": "Comercial (asesores y KAM)"},
    pares_incompatibles=[("mantenimiento_red", "contact_center", "red y atención al cliente")],
    riesgo_operativo="Un supervisor con {s} técnicos o agentes no alcanza a verificar trabajo en alturas ni calidad "
                     "de atención; en telecomunicaciones el estándar ronda 12-15.",
    bloque_operativo="Cuadrillas y contact center", factor_costo=1.05,
    caso="Cliente: Cóndor Telecom (operador FICTICIO de telecomunicaciones en Colombia, {personas:,} colaboradores; "
         "red y cuadrillas en cinco regiones, contact centers en Bogotá y Medellín, fuerza de ventas masiva; "
         "productos Internet Hogar, TV y Entretenimiento, Móvil Pospago, Móvil Prepago y Soluciones "
         "Empresariales). Hoy tiene tres unidades de negocio con capacidades duplicadas, funciones corporativas "
         "y una gran operación de red, instalaciones y contact center. El CEO pide: (1) pasar a un modelo "
         "producto-plataforma, (2) máximo 7 capas, (3) subir los tramos de control, sin comprometer la "
         "seguridad de las cuadrillas en campo ni la atención al cliente.",
    productos_txt="equipos por línea de producto con gestión de producto, marketing de producto y experiencia de cliente",
    plataformas_txt="operaciones de red, servicio al cliente, ventas, datos y pricing, etc.",
    habilitadores_txt="finanzas, gestión humana, tecnología, regulatorio y legal",
    regla_separar="no pongas la red (mantenimiento, NOC y despliegue) y la atención al cliente (contact center) "
                  "en el mismo bloque",
    chro_perfil="con experiencia en cuadrillas de campo, contact center y fuerza de ventas",
    modelo_respaldo={
        "productos": [{"nombre": "Hogar", "categorias": ["Internet Hogar", "TV y Entretenimiento"]},
                      {"nombre": "Móvil", "categorias": ["Móvil Pospago", "Móvil Prepago"]},
                      {"nombre": "Empresas", "categorias": ["Soluciones Empresariales"]}],
        "plataformas": [{"nombre": "Operaciones de Red", "capacidades": ["mantenimiento_red", "noc", "despliegue"]},
                        {"nombre": "Servicio al Cliente", "capacidades": ["contact_center", "instalaciones", "retencion"]},
                        {"nombre": "Ventas", "capacidades": ["ventas_masivas", "ventas_empresas"]},
                        {"nombre": "Datos, Pricing y Digital", "capacidades": ["pricing", "analytics", "digital"]}],
        "habilitadores": [{"nombre": "Finanzas", "capacidades": ["finanzas"]}, {"nombre": "Gestión Humana", "capacidades": ["rrhh"]},
                          {"nombre": "Tecnología", "capacidades": ["ti"]}, {"nombre": "Regulatorio y Legal", "capacidades": ["legal"]}],
    },
    guion={
        "plataformas_r1": [
            {"nombre": "Red y Servicio", "descripcion": "Red, instalaciones, contact center y retención",
             "capacidades": ["mantenimiento_red", "noc", "despliegue", "contact_center", "instalaciones", "retencion"]},
            {"nombre": "Ventas", "descripcion": "Ventas masivas y a empresas", "capacidades": ["ventas_masivas", "ventas_empresas"]},
            {"nombre": "Pricing y Analytics", "descripcion": "Ofertas, precios e inteligencia comercial",
             "capacidades": ["pricing", "analytics"]},
            {"nombre": "Canales Digitales", "descripcion": "App y e-commerce", "capacidades": ["digital"]}],
        "per_op": "técnicos y agentes", "riesgo_corto": "compromete la seguridad de las cuadrillas en campo",
        "separar": "la red de la atención al cliente", "cubierto": "La seguridad en campo está cubierta",
        "condiciones": ["Certificar en seguridad a los nuevos supervisores de cuadrilla antes del cambio.",
                        "Acordar los niveles de servicio entre productos y plataformas antes del lanzamiento."],
    },
)

EMPRESAS = {e.id: e for e in (CPG, BANCO, RETAIL, TELECOM)}
ORDEN = ["cpg", "banco", "retail", "telecom"]
POR_DEFECTO = "cpg"


def get(empresa_id: str | None) -> Empresa:
    return EMPRESAS.get(empresa_id or POR_DEFECTO, CPG)
