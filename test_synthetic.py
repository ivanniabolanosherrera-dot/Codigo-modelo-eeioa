"""
test_synthetic.py

ADVERTENCIA: Este script usa una economia sintetica de 5 sectores, inventada
unicamente para verificar que las funciones de eeioa_model.py son
matematicamente correctas. NINGUNO de los numeros aqui representa a Costa
Rica ni debe citarse en el paper. Sirve como prueba unitaria / demo.

Para correr el modelo con datos reales: cargar A, f_I y y_DLS desde
dls_carbon_footprint_cr.db (tablas mip_coeficiente_tecnico,
intensidad_emision, y_dls_demanda) una vez esas tablas esten completas, y
pasar esos arrays a las mismas funciones.
"""

import numpy as np
from eeioa_model import (
    construir_matriz_A,
    calcular_huella,
    emisiones_per_capita,
    brecha_climatica,
    aplicar_sensibilidad,
    resumen_escenario,
)

# --- Economia sintetica de 5 sectores (ILUSTRATIVA, NO REAL) ----------------
sectores = ["Agropecuario", "Energia", "Transporte", "Construccion", "Servicios"]
n = len(sectores)

# Produccion bruta total (unidad arbitraria: millones de colones ficticios)
x0 = np.array([1000, 1500, 1200, 900, 2500], dtype=float)

# Matriz de flujos intermedios Z (fila = sector proveedor, columna = sector comprador)
Z = np.array([
    [ 50, 100,  30,  20,  80],
    [ 40, 150, 200,  90, 120],
    [ 20,  80, 100,  60, 150],
    [ 10,  30,  20,  80,  60],
    [ 60,  90,  70, 100, 200],
], dtype=float)

# Intensidad de emision (tCO2e ficticias por millon de colones ficticios)
f_I = np.array([0.8, 2.5, 3.2, 1.1, 0.3])

# Demanda final DLS sintetica (Escenario A: provision actual)
y_dls_A = np.array([200, 150, 180, 220, 300], dtype=float)

# Demanda final DLS sintetica (Escenario B: provision universal, mayor volumen)
y_dls_B = np.array([260, 210, 230, 300, 380], dtype=float)

poblacion_ficticia = 5_191_716  # unico valor real de este script (INEC 2025),
                                  # usado solo para mostrar el calculo per capita


def main():
    A = construir_matriz_A(Z, x0)
    print("Matriz de coeficientes tecnicos A (sintetica):")
    print(np.round(A, 3))
    print()

    for nombre, y in [("A (sintetico)", y_dls_A), ("B (sintetico)", y_dls_B)]:
        resultado = calcular_huella(A, f_I, y)
        e_pc = emisiones_per_capita(resultado.emision_total, poblacion_ficticia)
        brecha = brecha_climatica(e_pc)
        print(f"--- Escenario {nombre} ---")
        print(f"  Produccion total requerida (x): {np.round(resultado.x, 1)}")
        print(f"  Emision total: {resultado.emision_total:.2f} (unidad ficticia Gg-equivalente)")
        print(f"  % emisiones indirectas: {resultado.pct_indirectas:.1f}%")
        print(f"  tCO2e per capita (ficticio): {e_pc:.6f}")
        print(f"  Brecha vs umbral 1.6 tCO2e: {brecha:.1f}%")
        print()

    print("--- Demo de sensibilidad: reduccion de 20% en f_I del sector Transporte ---")
    f_I_ajustado = f_I.copy()
    f_I_ajustado[2] = aplicar_sensibilidad(np.array([f_I[2]]), -20)[0]
    resultado_base = calcular_huella(A, f_I, y_dls_A)
    resultado_ajustado = calcular_huella(A, f_I_ajustado, y_dls_A)
    print(f"  Emision total base: {resultado_base.emision_total:.2f}")
    print(f"  Emision total ajustada: {resultado_ajustado.emision_total:.2f}")
    delta = (resultado_ajustado.emision_total / resultado_base.emision_total - 1) * 100
    print(f"  Variacion: {delta:.2f}%")
    print()

    print("--- resumen_escenario() (funcion de conveniencia) ---")
    resumen = resumen_escenario(A, f_I, y_dls_A, poblacion_ficticia)
    for k, v in resumen.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
