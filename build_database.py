

import sqlite3
import os

DB_PATH = "dls_carbon_footprint_cr.db"
SCHEMA_PATH = "schema.sql"


def build_schema(conn):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def load_poblacion(conn):
    """
    Fuente: INEC, Estimacion de Poblacion 2025.
    """
    conn.execute(
        """
        INSERT INTO poblacion
        (anio, poblacion_total, poblacion_mujeres, poblacion_hombres,
         fuente, fecha_fuente, confianza)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (2025, 5191716, 2599732, 2591984,
         "INEC - Estimacion de Poblacion 2025", "2025", "Alta"),
    )


def load_ingei_macrosector(conn):
    """
    Fuente: Inventario Nacional de GEI 1990-2017 (IMN / Direccion de Cambio
    Climatico, MINAE), publicado 2021-12. Cifras agregadas verificadas via
    fuentes secundarias oficiales (MINAE, PNUD) en esta sesion.
    """
    rows = [
        # (anio, macrosector, Gg CO2e, % participacion, es_absorcion,
        #  fuente, fecha_fuente, confianza, nota)
        (2017, "Energia", 7981.6, 55.1, 0,
         "IMN/MINAE - Direccion de Cambio Climatico, INGEI 1990-2017",
         "2021-12-01", "Alta",
         "Incluye transporte, industrias energeticas, manufactura/construccion, otras."),
        (2017, "IPPU", None, None, 0,
         "IMN/MINAE - INGEI 1990-2017", "2021-12-01", "Baja",
         "Total del macrosector 2017 no localizado en esta sesion; solo se "
         "verifico la subcategoria refrigeracion y aire acondicionado = "
         "633.7 Gg CO2e (2017), y que el sector aporto 12% del CO2 total "
         "segun una fuente secundaria (ladatacuenta.com, sin especificar año)."),
        (2017, "AFOLU_excl_FOLU", None, 20.5, 0,
         "IMN/MINAE - INGEI 1990-2017 via PNUD", "2022-01-19", "Media",
         "El 20.5% corresponde a 2016, no a 2017; no debe usarse como cifra "
         "de 2017 sin verificacion adicional contra el informe primario."),
        (2017, "Residuos", None, None, 0,
         "IMN/MINAE - INGEI 1990-2017", "2021-12-01", "Baja",
         "Total del macrosector 2017 no localizado en esta sesion."),
        (2017, "Total_nacional_excl_FOLU", 14477.5, 100.0, 0,
         "IMN/MINAE via PNUD Costa Rica", "2022-01-19", "Media",
         "Fuentes secundarias citan 14,477.x y 14,478 Gg CO2e sin decimal "
         "exacto verificable en esta sesion; usar 14477.5 solo como valor "
         "central aproximado, NO como cifra de precision para publicacion. "
         "Verificar contra informe primario IMN antes de citar con decimales."),
        (2017, "FOLU", -2968.35, None, 1,
         "IMN/MINAE via PNUD Costa Rica", "2022-01-19", "Alta",
         "Absorcion neta (signo negativo ya aplicado)."),
    ]
    conn.executemany(
        """
        INSERT INTO ingei_macrosector
        (anio, macrosector_ipcc, emisiones_gg_co2e, pct_participacion,
         es_absorcion, fuente, fecha_fuente, confianza, nota)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def load_ingei_subcategoria(conn):
    rows = [
        (2017, "Energia", "Transporte (% del total nacional de GEI)",
         None, 42.0,
         "IMN/MINAE via PNUD Costa Rica", "2022-01-19", "Alta"),
        (2017, "IPPU", "Refrigeracion y aire acondicionado",
         633.7, None,
         "IMN/MINAE via PNUD Costa Rica", "2022-01-19", "Alta"),
        (2017, "AFOLU_excl_FOLU", "Fermentacion enterica (% del sector agricultura)",
         None, 62.3,
         "IMN/MINAE via PNUD Costa Rica", "2022-01-19", "Media"),
        (2017, "Residuos", "Disposicion de desechos solidos (% del sector residuos)",
         None, 56.34,
         "IMN/MINAE via PNUD Costa Rica", "2022-01-19", "Media"),
    ]
    conn.executemany(
        """
        INSERT INTO ingei_subcategoria
        (anio, macrosector_ipcc, subcategoria, emisiones_gg_co2e,
         pct_del_macrosector, fuente, fecha_fuente, confianza)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def load_dls_categorias(conn):
    rows = [
        ("ALIM", "Alimentacion adecuada", "Nutricion y disponibilidad calorica minima"),
        ("AGUA", "Agua potable y saneamiento", None),
        ("ENER", "Energia electrica y combustibles domesticos", None),
        ("VIV", "Vivienda digna", "Construccion, materiales, mantenimiento, servicios habitacionales"),
        ("TRAN", "Transporte basico", "Publico y privado esencial"),
        ("EDU", "Educacion primaria y secundaria", None),
        ("SALUD", "Salud primaria, preventiva y hospitalaria", None),
        ("TIC", "Informacion y telecomunicaciones basicas", None),
    ]
    conn.executemany(
        "INSERT INTO dls_categoria (codigo, nombre, descripcion) VALUES (?, ?, ?)",
        rows,
    )


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        build_schema(conn)
        load_poblacion(conn)
        load_ingei_macrosector(conn)
        load_ingei_subcategoria(conn)
        load_dls_categorias(conn)
        conn.commit()
        print(f"Base de datos construida: {DB_PATH}")

        cur = conn.cursor()
        for tabla in ["poblacion", "ingei_macrosector", "ingei_subcategoria",
                      "dls_categoria", "mip_actividad", "y_dls_demanda",
                      "resultado_escenario_agregado"]:
            cur.execute(f"SELECT COUNT(*) FROM {tabla}")
            print(f"  {tabla}: {cur.fetchone()[0]} filas")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
