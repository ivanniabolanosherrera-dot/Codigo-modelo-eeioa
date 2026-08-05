

import sqlite3
import sys
from datetime import date

import numpy as np

from eeioa_model import resumen_escenario, calcular_huella

DB_PATH = "dls_carbon_footprint_cr.db"


def cargar_actividades(conn):
    cur = conn.execute("SELECT codigo_actividad FROM mip_actividad ORDER BY codigo_actividad")
    return [r[0] for r in cur.fetchall()]


def verificar_completitud(conn, codigos):
    n = len(codigos)
    if n == 0:
        sys.exit(
            "ERROR: la tabla mip_actividad esta vacia. Cargar las 144 "
            "actividades de la MIP 2017 (BCCR) antes de correr el modelo. "
            "Ver README.md."
        )

    cur = conn.execute("SELECT COUNT(*) FROM mip_coeficiente_tecnico WHERE coeficiente_a IS NOT NULL")
    n_coef = cur.fetchone()[0]
    if n_coef < n * n:
        sys.exit(
            f"ERROR: mip_coeficiente_tecnico tiene {n_coef} coeficientes "
            f"no nulos de {n*n} esperados (matriz {n}x{n}). Completar la "
            "carga de la matriz de coeficientes tecnicos A antes de continuar."
        )

    cur = conn.execute("SELECT COUNT(*) FROM intensidad_emision WHERE intensidad_tco2e_por_mm_colones IS NOT NULL")
    n_int = cur.fetchone()[0]
    if n_int < n:
        sys.exit(
            f"ERROR: intensidad_emision tiene {n_int} valores no nulos de "
            f"{n} actividades esperadas. Completar el vector f_I antes de "
            "continuar."
        )

    for escenario in ("A", "B"):
        cur = conn.execute(
            "SELECT COUNT(*) FROM y_dls_demanda WHERE escenario = ? AND demanda_mm_colones IS NOT NULL",
            (escenario,),
        )
        n_y = cur.fetchone()[0]
        if n_y == 0:
            sys.exit(
                f"ERROR: y_dls_demanda no tiene valores cargados para el "
                f"Escenario {escenario}. Completar el vector y_DLS antes de "
                "continuar."
            )


def construir_arrays(conn, codigos):
    n = len(codigos)
    idx = {c: i for i, c in enumerate(codigos)}

    A = np.zeros((n, n))
    cur = conn.execute(
        "SELECT fila_actividad, columna_actividad, coeficiente_a FROM mip_coeficiente_tecnico"
    )
    for fila, columna, a_ij in cur.fetchall():
        A[idx[fila], idx[columna]] = a_ij if a_ij is not None else 0.0

    f_I = np.zeros(n)
    cur = conn.execute(
        "SELECT codigo_actividad, intensidad_tco2e_por_mm_colones FROM intensidad_emision"
    )
    for cod, val in cur.fetchall():
        f_I[idx[cod]] = val if val is not None else 0.0

    y_por_escenario = {}
    for escenario in ("A", "B"):
        y = np.zeros(n)
        cur = conn.execute(
            "SELECT codigo_actividad, SUM(demanda_mm_colones) FROM y_dls_demanda "
            "WHERE escenario = ? GROUP BY codigo_actividad",
            (escenario,),
        )
        for cod, val in cur.fetchall():
            if cod in idx:
                y[idx[cod]] = val if val is not None else 0.0
        y_por_escenario[escenario] = y

    return A, f_I, y_por_escenario, idx


def obtener_poblacion(conn, anio=2025):
    cur = conn.execute("SELECT poblacion_total FROM poblacion WHERE anio = ?", (anio,))
    row = cur.fetchone()
    if row is None:
        sys.exit(f"ERROR: no hay poblacion registrada para el anio {anio} en la tabla poblacion.")
    return row[0]


def guardar_resultados(conn, escenario, codigos, resultado, resumen, version_modelo="v1.0"):
    hoy = date.today().isoformat()
    conn.execute("DELETE FROM resultado_huella WHERE escenario = ?", (escenario,))
    filas = []
    for i, cod in enumerate(codigos):
        emision_total_i = resultado.emision_total_por_actividad[i]
        pct = (100.0 * emision_total_i / resultado.emision_total) if resultado.emision_total else None
        filas.append((
            escenario, cod,
            float(resultado.emision_directa[i]),
            float(emision_total_i - resultado.emision_directa[i]),
            float(emision_total_i),
            pct,
            hoy, version_modelo,
        ))
    conn.executemany(
        """
        INSERT INTO resultado_huella
        (escenario, codigo_actividad, emision_directa_gg, emision_indirecta_gg,
         emision_total_gg, pct_participacion, fecha_calculo, version_modelo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        filas,
    )

    conn.execute("DELETE FROM resultado_escenario_agregado WHERE escenario = ?", (escenario,))
    conn.execute(
        """
        INSERT INTO resultado_escenario_agregado
        (escenario, emisiones_totales_gg_co2e, poblacion_referencia,
         tco2e_per_capita, umbral_tco2e_per_capita, brecha_pct,
         pct_emisiones_indirectas, fecha_calculo, version_modelo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (escenario, resumen["emisiones_totales_gg_co2e"], resumen["poblacion_referencia"],
         resumen["tco2e_per_capita"], resumen["umbral_tco2e_per_capita"], resumen["brecha_pct"],
         resumen["pct_emisiones_indirectas"], hoy, version_modelo),
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        codigos = cargar_actividades(conn)
        verificar_completitud(conn, codigos)
        A, f_I, y_por_escenario, idx = construir_arrays(conn, codigos)
        poblacion = obtener_poblacion(conn)

        for escenario, y in y_por_escenario.items():
            resultado = calcular_huella(A, f_I, y)
            resumen = resumen_escenario(A, f_I, y, poblacion)
            guardar_resultados(conn, escenario, codigos, resultado, resumen)
            print(f"Escenario {escenario}: {resumen}")

        conn.commit()
        print("Resultados guardados en resultado_huella y resultado_escenario_agregado.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
