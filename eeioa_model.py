"""
eeioa_model.py

Implementacion del modelo input-output ambientalmente extendido (EEIOA)
descrito en la seccion 3.2 del paper:

    x = (I - A)^(-1) y                      [produccion total requerida]
    E = f_I (I - A)^(-1) y                  [huella de carbono total]
    E_DLS = f_I (I - A)^(-1) y_DLS          [huella DLS]
    e_pc = E_DLS / P                        [emisiones per capita]
    brecha_pct = (e_pc - umbral) / umbral * 100

"""

from dataclasses import dataclass
import numpy as np


UMBRAL_TCO2E_PER_CAPITA_DEFAULT = 1.6


@dataclass
class ResultadoHuella:
    x: np.ndarray                  # produccion total requerida por actividad
    emision_directa: np.ndarray    # f_I * x_directo (emision propia por actividad demandada)
    emision_total_por_actividad: np.ndarray  # f_I * (contribucion de cada actividad a x)
    emision_total: float           # escalar: E = f_I (I-A)^-1 y
    pct_indirectas: float          # % de E que es indirecto


def construir_matriz_A(flujos_intermedios: np.ndarray,
                        produccion_bruta: np.ndarray) -> np.ndarray:
    """
    Construye la matriz de coeficientes tecnicos A a partir de la matriz de
    flujos intermedios (Z, de la MIP) y el vector de produccion bruta (x0).

    a_ij = z_ij / x0_j

    Parameters
    ----------
    flujos_intermedios : ndarray (n, n)
        Matriz Z de la MIP: fila i = insumo del sector i, columna j = usado
        por el sector j.
    produccion_bruta : ndarray (n,)
        Produccion bruta total por sector (x0).

    Returns
    -------
    A : ndarray (n, n)
    """
    x0 = np.asarray(produccion_bruta, dtype=float)
    if np.any(x0 == 0):
        raise ValueError(
            "produccion_bruta contiene ceros; no se puede dividir. "
            "Revisar sectores con produccion nula en la MIP."
        )
    return flujos_intermedios / x0[np.newaxis, :]


def inversa_leontief(A: np.ndarray) -> np.ndarray:
    """
    Calcula (I - A)^-1.
    """
    n = A.shape[0]
    I = np.eye(n)
    col_sums = A.sum(axis=0)
    if np.any(col_sums >= 1):
        problematic = np.where(col_sums >= 1)[0]
        raise ValueError(
            f"Las columnas {problematic.tolist()} de A tienen suma >= 1 "
            "(coeficientes tecnicos invalidos o error de escala en los datos "
            "de entrada). Revisar la matriz de flujos intermedios."
        )
    try:
        return np.linalg.inv(I - A)
    except np.linalg.LinAlgError as e:
        raise ValueError(
            "La matriz (I - A) es singular; no se puede invertir. "
            "Verificar independencia lineal de los sectores en la MIP."
        ) from e


def calcular_huella(A: np.ndarray,
                     f_I: np.ndarray,
                     y: np.ndarray) -> ResultadoHuella:
    """
    Calcula E = f_I (I-A)^-1 y, y descompone en directo/indirecto.

    La descomposicion directo/indirecto sigue la convencion:
      - emision "directa" de la demanda y: f_I aplicado directamente a y
        (como si no hubiera encadenamientos, i.e. produccion = y).
      - emision "indirecta": la diferencia entre la huella total (con
        encadenamientos completos via Leontief) y la huella directa.

    Parameters
    ----------
    A : ndarray (n, n)      coeficientes tecnicos
    f_I : ndarray (n,)      intensidad de emision por unidad de produccion
                            (misma unidad monetaria que y), p.ej. tCO2e / mm colones
    y : ndarray (n,)        vector de demanda final (p.ej. y_DLS)

    Returns
    -------
    ResultadoHuella
    """
    f_I = np.asarray(f_I, dtype=float)
    y = np.asarray(y, dtype=float)

    L = inversa_leontief(A)          # (I-A)^-1
    x = L @ y                         # produccion total requerida

    emision_total_por_actividad = f_I * x
    emision_total = float(emision_total_por_actividad.sum())

    emision_directa_por_actividad = f_I * y
    emision_directa_total = float(emision_directa_por_actividad.sum())

    emision_indirecta_total = emision_total - emision_directa_total
    pct_indirectas = (
        100.0 * emision_indirecta_total / emision_total if emision_total != 0 else np.nan
    )

    return ResultadoHuella(
        x=x,
        emision_directa=emision_directa_por_actividad,
        emision_total_por_actividad=emision_total_por_actividad,
        emision_total=emision_total,
        pct_indirectas=pct_indirectas,
    )


def emisiones_per_capita(emision_total_gg: float, poblacion: int) -> float:
    """
    e_pc = E_DLS / P
    E_DLS en Gg CO2e, poblacion en habitantes -> resultado en tCO2e/habitante.
    1 Gg = 1000 t
    """
    return (emision_total_gg * 1000.0) / poblacion


def brecha_climatica(e_pc: float,
                      umbral: float = UMBRAL_TCO2E_PER_CAPITA_DEFAULT) -> float:
    """
    brecha (%) = (e_pc - umbral) / umbral * 100
    Positivo = excede el umbral. Negativo = por debajo del umbral.
    """
    return (e_pc - umbral) / umbral * 100.0


def aplicar_sensibilidad(base: np.ndarray,
                          variacion_pct: float) -> np.ndarray:
    """
    Aplica una variacion porcentual uniforme a un vector (f_I o y_DLS) para
    el analisis de sensibilidad. variacion_pct = -15 implica una reduccion
    del 15%.

    Para variaciones sector-especificas, construir una mascara booleana y
    aplicar la variacion solo a los indices correspondientes (ver ejemplo
    en test_synthetic.py, funcion `demo_sensibilidad`).
    """
    factor = 1.0 + (variacion_pct / 100.0)
    return np.asarray(base, dtype=float) * factor


def resumen_escenario(A: np.ndarray,
                       f_I: np.ndarray,
                       y: np.ndarray,
                       poblacion: int,
                       umbral: float = UMBRAL_TCO2E_PER_CAPITA_DEFAULT) -> dict:
    """
    Corre el pipeline completo para un escenario y devuelve un resumen
    listo para insertar en resultado_escenario_agregado.
    """
    resultado = calcular_huella(A, f_I, y)
    e_pc = emisiones_per_capita(resultado.emision_total, poblacion)
    brecha = brecha_climatica(e_pc, umbral)
    return {
        "emisiones_totales_gg_co2e": resultado.emision_total,
        "poblacion_referencia": poblacion,
        "tco2e_per_capita": e_pc,
        "umbral_tco2e_per_capita": umbral,
        "brecha_pct": brecha,
        "pct_emisiones_indirectas": resultado.pct_indirectas,
    }
