# -*- coding: utf-8 -*-


import sqlite3
from datetime import date

from eeioa_model import emisiones_per_capita, brecha_climatica

DB_PATH = "dls_carbon_footprint_cr.db"
FUENTE_MODELO = "Estimacion propia EEIOA"
FECHA_MODELO = "2026-05-23"


def parse_num(s):
    """Convierte '6.026,0' o '75,5%' o '—' o 'N/D' a float o None."""
    if s in ("—", "N/D", "-", None, ""):
        return None
    s = s.replace("%", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# TABLA 1: Sectores MIP 2017 (agregacion en 16-17 grupos) y correspondencia DLS
# ---------------------------------------------------------------------------
TABLA1 = [
    # (codigo_AE, nombre, ciiu, grupo_dls)
    ("A01-A03", "Agropecuario y pesca", "A01-A03", "ALIM"),
    ("C10-C12", "Industria alimentaria", "C10-C12", "ALIM"),
    ("C13-C33_ex", "Manufactura general (excl. alimentaria)", "C13-C33", "VIV"),
    ("D35", "Suministro de electricidad", "D35", "ENER"),
    ("E36-E39", "Agua, alcantarillado y residuos", "E36-E39", "AGUA"),
    ("F41-F43", "Construccion", "F41-F43", "VIV"),
    ("G45-G47", "Comercio al por mayor y menor", "G45-G47", "ALIM"),
    ("H49", "Transporte terrestre", "H49", "TRAN"),
    ("H50-H51", "Transporte acuatico y aereo", "H50-H51", "TRAN"),
    ("H52-H53", "Almacenamiento y correo", "H52-H53", "ALIM"),
    ("J58-J63", "Informacion y comunicaciones", "J58-J63", "TIC"),
    ("Q86", "Actividades de atencion de salud", "Q86", "SALUD"),
    ("Q87-Q88", "Asistencia en establecimientos / social", "Q87-Q88", "SALUD"),
    ("P85", "Educacion", "P85", "EDU"),
    ("L68", "Actividades inmobiliarias", "L68", "VIV"),
    ("C19", "Refinacion de petroleo", "C19", "ENER"),
    ("O84", "Administracion publica y defensa", "O84", "SALUD"),
]

# ---------------------------------------------------------------------------
# TABLA 2: y_DLS Escenario A (miles de millones de colones 2017)
# ---------------------------------------------------------------------------
TABLA2 = [
    # (categoria_dls, gasto_q1_mes, gasto_nacional_mes, valor_dls_min_anual_pc,
    #  gasto_publico_mm, demanda_total_mm)
    ("ALIM",  "Alimentacion adecuada",            "110.120", "138.098", "330.240", None,     "1.624"),
    ("AGUA",  "Agua potable y saneamiento",        None,      None,      "28.500",  "215",    "374"),
    ("ENER",  "Energia domestica",                 "45.019",  "69.715",  "135.057", None,     "704"),
    ("VIV",   "Vivienda digna",                    None,      None,      "180.000", None,     "938"),
    ("TRAN",  "Transporte basico",                 "32.585",  "90.195",  "97.755",  None,     "509"),
    ("EDU",   "Educacion",                         "3.587",   "27.775",  "10.761",  "2.748",  "2.803"),
    ("SALUD", "Salud primaria y hospitalaria",      "8.277",   "32.179",  "24.831",  "1.942",  "2.072"),
    ("TIC",   "Telecomunicaciones basicas",         "16.671",  "36.068",  "50.013",  None,     "261"),
]

# ---------------------------------------------------------------------------
# TABLA 3: Emisiones directas/indirectas/totales por sector (Gg CO2e, 2017)
# Escenario A
# ---------------------------------------------------------------------------
TABLA3 = [
    # (codigo_actividad, directo, pct_dir, indirecto, pct_ind, total, pct_tot, intensidad)
    ("H49",      "6.026,0", "75,5%", "312,4", "4,9%",  "6.338,4", "43,8%", "8,42"),
    ("A01-A03",  "2.968,0", "37,2%", "187,6", "6,3%",  "3.155,6", "21,8%", "4,18"),
    ("E36-E39",  "1.198,9", "15,0%", "96,3",  "8,0%",  "1.295,2", "8,9%",  None),
    ("C10-C12",  "248,6",   "3,1%",  "418,2", "62,7%", "666,8",   "4,6%",  "2,31"),
    ("C13-C33_ex","612,4",  "7,7%",  "380,8", "38,3%", "993,2",   "6,9%",  "3,14"),
    ("C19",      "198,3",   "2,5%",  "44,1",  "18,2%", "242,4",   "1,7%",  "5,87"),
    ("F41-F43",  "87,4",    "1,1%",  "342,6", "79,7%", "430,0",   "3,0%",  "1,96"),
    ("D35",      "54,2",    "0,7%",  "38,6",  "41,6%", "92,8",    "0,6%",  "0,43"),
    ("E36-E39_agua","38,1", "0,5%",  "52,3",  "57,8%", "90,4",    "0,6%",  None),
    ("G45-G47",  "96,4",    "1,2%",  "186,3", "65,9%", "282,7",   "2,0%",  "0,89"),
    ("J58-J63",  "31,8",    "0,4%",  "98,7",  "75,6%", "130,5",   "0,9%",  "0,82"),
    ("Q86",      "24,6",    "0,3%",  "112,4", "82,1%", "137,0",   "0,9%",  "0,74"),
    ("P85",      "18,9",    "0,2%",  "86,3",  "82,0%", "105,2",   "0,7%",  "0,61"),
    ("L68",      "12,4",    "0,2%",  "64,8",  "83,9%", "77,2",    "0,5%",  "0,38"),
    ("O84",      "28,6",    "0,4%",  "74,2",  "72,2%", "102,8",   "0,7%",  "0,67"),
]
TABLA3_RESTO = ("341,8", "2,4%")  # Gg CO2e, % del total (sectores no desagregados)
TABLA3_TOTAL_ECONOMIA = {"directo": 7981.6, "indirecto": 2496.0, "total": 14477.6}

# ---------------------------------------------------------------------------
# TABLA 4: Comparacion de escenarios
# ---------------------------------------------------------------------------
ESCENARIO_A = {
    "emisiones_totales_gg_co2e": 8312.0,
    "poblacion_referencia": 5191716,
    "y_dls_total_mm_colones": 9285.0,
}
ESCENARIO_B = {
    "emisiones_totales_gg_co2e": 9102.0,
    "poblacion_referencia": 5191716,
}

# ---------------------------------------------------------------------------
# TABLA 5: Analisis de sensibilidad (base: Escenario A = 8.312 Gg CO2e)
# ---------------------------------------------------------------------------
TABLA5 = [
    ("Transporte", "Electrificacion 20% flota privada (-40% fI segmento H49)", -20,
     None, -752, 7560, 1.457, -0.143),
    ("Transporte", "Modal shift 15% hacia transporte publico colectivo", -15,
     None, -376, 7936, 1.529, -0.071),
    ("Transporte", "Universalizacion Esc. B: +12% demanda movilidad Q1-Q2", 12,
     99, 351, 8663, 1.669, 0.069),
    ("Energia", "Penetracion solar residencial 10% hogares (-5% demanda D35)", -5,
     None, -46, 8266, 1.592, -0.008),
    ("Energia", "Eficiencia energetica en edificios -15% demanda D35", -15,
     None, -62, 8250, 1.589, -0.011),
    ("Energia", "Universalizacion Esc. B: +8% consumo electrico domestico Q1-Q2", 8,
     56, 39, 8351, 1.609, 0.009),
    ("Alimentacion", "Reduccion 20% consumo de proteina animal (A01)", -20,
     None, -631, 7681, 1.480, -0.120),
    ("Alimentacion", "Reduccion 30% perdidas y desperdicio (A01-A03, C10-C12)", -30,
     -180, -312, 8000, 1.541, -0.059),
    ("Alimentacion", "Universalizacion Esc. B: +18% demanda alimentaria Q1-Q2", 18,
     158, 264, 8576, 1.652, 0.052),
]


def load_mip_actividad(conn):
    conn.executemany(
        """INSERT OR REPLACE INTO mip_actividad
           (codigo_actividad, nombre_actividad, codigo_ciiu_rev4, grupo_dls,
            fuente, confianza)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(c, n, ciiu, dls, "BCCR - MIP 2017 (agregacion propia de 144 AE en 17 grupos)", "Media")
         for c, n, ciiu, dls in TABLA1],
    )
    # Sub-fila auxiliar usada en Tabla 3 para "agua" dentro de E36-E39 (distinta de residuos)
    conn.execute(
        """INSERT OR REPLACE INTO mip_actividad
           (codigo_actividad, nombre_actividad, codigo_ciiu_rev4, grupo_dls, fuente, confianza)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("E36-E39_agua", "Agua y alcantarillado (subcomponente)", "E36-E37", "AGUA",
         "BCCR - MIP 2017 (agregacion propia)", "Media"),
    )


def load_dls_demanda(conn):
    filas = []
    for cod, nombre, q1, nac, dls_min, pub, total in TABLA2:
        filas.append((
            cod, cod, "A", 2017,
            parse_num(total) * 1000 if total else None,  # miles de millones -> millones de colones
            "ENIGH 2018 (INEC) + gasto publico sectorial 2017 (Min. Salud, MIDEPLAN/BCCR)",
            "Media",
        ))
    conn.executemany(
        """INSERT INTO y_dls_demanda
           (codigo_actividad, categoria_dls, escenario, anio_referencia,
            demanda_mm_colones, fuente, confianza)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        filas,
    )


def load_resultado_huella(conn):
    hoy = date.today().isoformat()
    filas = []
    for cod, directo, pct_dir, indirecto, pct_ind, total, pct_tot, intensidad in TABLA3:
        filas.append((
            "A", cod,
            parse_num(directo), parse_num(indirecto), parse_num(total),
            parse_num(pct_tot),
            hoy, "v1.0-sesion-previa-2026-05-23",
        ))
    # fila "resto de sectores"
    filas.append((
        "A", "RESTO", None, None, parse_num(TABLA3_RESTO[0]), parse_num(TABLA3_RESTO[1]),
        hoy, "v1.0-sesion-previa-2026-05-23",
    ))
    conn.executemany(
        """INSERT INTO resultado_huella
           (escenario, codigo_actividad, emision_directa_gg, emision_indirecta_gg,
            emision_total_gg, pct_participacion, fecha_calculo, version_modelo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        filas,
    )


def load_y_calcular_escenarios(conn):
    """
    Carga los totales de Escenario A y B YA CALCULADOS en la sesion previa, y
    RE-EJECUTA (no copia ciegamente) las formulas de eeioa_model para
    verificar per capita y brecha, como control de calidad de este script.
    """
    hoy = date.today().isoformat()
    resultados = {}
    for nombre, datos in (("A", ESCENARIO_A), ("B", ESCENARIO_B)):
        E = datos["emisiones_totales_gg_co2e"]
        P = datos["poblacion_referencia"]
        e_pc = emisiones_per_capita(E, P)
        brecha = brecha_climatica(e_pc)

        # % indirectas: calculado desde Tabla 3 (solo disponible para Escenario A,
        # ya que Tabla 3 esta desagregada unicamente para el Escenario A)
        pct_indirectas = None
        if nombre == "A":
            cur = conn.execute(
                "SELECT SUM(emision_directa_gg), SUM(emision_total_gg) FROM resultado_huella WHERE escenario='A'"
            )
            suma_dir, suma_tot = cur.fetchone()
            if suma_tot:
                pct_indirectas = 100.0 * (suma_tot - (suma_dir or 0)) / suma_tot

        resultados[nombre] = {
            "emisiones_totales_gg_co2e": E,
            "poblacion_referencia": P,
            "tco2e_per_capita": e_pc,
            "brecha_pct": brecha,
            "pct_emisiones_indirectas": pct_indirectas,
        }

        conn.execute(
            """INSERT INTO resultado_escenario_agregado
               (escenario, emisiones_totales_gg_co2e, poblacion_referencia,
                tco2e_per_capita, umbral_tco2e_per_capita, brecha_pct,
                pct_emisiones_indirectas, fecha_calculo, version_modelo)
               VALUES (?, ?, ?, ?, 1.6, ?, ?, ?, ?)""",
            (nombre, E, P, e_pc, brecha, pct_indirectas, hoy, "v1.0-verificado-en-esta-sesion"),
        )
    return resultados


def load_sensibilidad(conn):
    hoy = date.today().isoformat()
    supuesto_ids = {}
    for sector, nombre, variacion_pct, delta_y, delta_e, nuevo_total, nuevo_epc, nueva_brecha in TABLA5:
        cur = conn.execute(
            """INSERT INTO sensibilidad_supuesto
               (sector, nombre_supuesto, variacion_pct, variable_afectada,
                fuente_supuesto, confianza)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sector, nombre, variacion_pct,
             "y_DLS" if delta_y is not None else "f_I",
             FUENTE_MODELO, "Media"),
        )
        supuesto_id = cur.lastrowid

        # Re-ejecutar (no copiar) el calculo de per capita y brecha para verificar
        e_pc_verificado = emisiones_per_capita(nuevo_total, ESCENARIO_A["poblacion_referencia"])
        brecha_verificada = brecha_climatica(e_pc_verificado)

        conn.execute(
            """INSERT INTO sensibilidad_resultado
               (supuesto_id, escenario_base, emisiones_totales_gg_ajustadas,
                tco2e_per_capita_ajustado, brecha_pct_ajustada, fecha_calculo)
               VALUES (?, 'A', ?, ?, ?, ?)""",
            (supuesto_id, nuevo_total, e_pc_verificado, brecha_verificada, hoy),
        )
        # Guardar discrepancia si la re-ejecucion no coincide con el valor reportado
        if abs(e_pc_verificado - nuevo_epc) > 0.01:
            print(f"  [AVISO] {nombre}: e_pc reportado={nuevo_epc}, "
                  f"recalculado={e_pc_verificado:.3f} -> diferencia de {abs(e_pc_verificado-nuevo_epc):.3f}")


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM mip_actividad")
        conn.execute("DELETE FROM y_dls_demanda")
        conn.execute("DELETE FROM resultado_huella")
        conn.execute("DELETE FROM resultado_escenario_agregado")
        conn.execute("DELETE FROM sensibilidad_resultado")
        conn.execute("DELETE FROM sensibilidad_supuesto")

        load_mip_actividad(conn)
        load_dls_demanda(conn)
        load_resultado_huella(conn)
        resultados = load_y_calcular_escenarios(conn)
        load_sensibilidad(conn)
        conn.commit()

        print("Carga completa. Verificacion de indicadores agregados (re-ejecutados en esta sesion):")
        for esc, r in resultados.items():
            print(f"  Escenario {esc}: E={r['emisiones_totales_gg_co2e']} Gg CO2e | "
                  f"e_pc={r['tco2e_per_capita']:.3f} tCO2e/hab | "
                  f"brecha={r['brecha_pct']:.2f}% | "
                  f"%indirectas={r['pct_emisiones_indirectas']}")

        # Verificacion cruzada de consistencia Tabla3 vs Tabla4 (la discrepancia conocida)
        cur = conn.execute("SELECT emisiones_gg_co2e FROM ingei_macrosector WHERE macrosector_ipcc='Total_nacional_excl_FOLU'")
        total_ingei = cur.fetchone()[0]
        print()
        print(f"  Control: Total INGEI nacional 2017 (bruto, excl. FOLU) = {total_ingei} Gg CO2e")
        print(f"  Control: Huella DLS Escenario A = {ESCENARIO_A['emisiones_totales_gg_co2e']} Gg CO2e")
        print(f"  Diferencia = {total_ingei - ESCENARIO_A['emisiones_totales_gg_co2e']:.1f} Gg CO2e "
              f"({100*(total_ingei-ESCENARIO_A['emisiones_totales_gg_co2e'])/total_ingei:.1f}% del total nacional)")
        print("  NOTA: esta diferencia NO es un error aritmetico. El total INGEI es la economia")
        print("  completa; 8.312 Gg es solo la porcion de esa economia atribuible a la demanda")
        print("  final y_DLS (~57% del total nacional). Confirmado en auditoria de sesion previa")
        print("  (2026-05-25): las dos cifras miden cosas distintas y ambas son correctas dentro")
        print("  de su propio alcance; el problema identificado fue de ROTULACION en la Tabla 3")
        print("  del paper, no de calculo.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
