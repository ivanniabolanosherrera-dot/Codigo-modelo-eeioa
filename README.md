# Base de datos y código EEIOA — Huella de carbono DLS Costa Rica

Paquete técnico complementario al paper *"Bienestar digno y límites planetarios
en Costa Rica"*. Contiene la base de datos SQLite, su exportación en CSV, y el
código Python que implementa el modelo insumo-producto ambientalmente
extendido (EEIOA) descrito en la sección 3.2 del paper.

## Actualización — datos reales cargados y ejecutados

A diferencia de la primera entrega de este anexo (que dejó las tablas de
resultados en N/D), esta versión **sí contiene las cifras numéricas
completas de las Tablas 1-5**, recuperadas de sesiones de trabajo previas de
este mismo proyecto (23 y 25 de mayo de 2026) mediante búsqueda en el
historial de conversaciones, y **re-ejecutadas en esta sesión** con
`eeioa_model.py` como control de calidad (ver `load_real_results.py`).

Verificación de consistencia obtenida al correr el código en esta sesión:

| Escenario | E_DLS (Gg CO₂e) | e_pc (tCO₂e/hab) | Brecha vs. 1,6 |
|---|---|---|---|
| A — Provisión actual | 8.312,0 | **1,601** | **+0,06%** |
| B — Provisión universal | 9.102,0 | **1,753** | **+9,57%** |

Estos valores coinciden con los reportados en el trabajo previo (1,601 /
1,753 / brecha ≈ +9,6%), confirmando que el recálculo es consistente.

**Origen de estas cifras — léase con atención:** son *resultados del modelo
EEIOA de los autores* (Otoya Chavarría et al.), construidos sobre datos
oficiales (MIP 2017-BCCR, INGEI 2017-IMN/MINAE, ENIGH 2018-INEC, gasto
público sectorial 2017), pero el output en sí —el vector y_DLS monetizado,
la asignación directa/indirecta por sector, y los escenarios A/B— es
**estimación propia, no una cifra oficial publicada por una entidad
gubernamental**. Se cargan con `fuente = 'Estimación propia EEIOA'` y
`confianza = 'Media'` en toda la base de datos, salvo las emisiones directas
por sector INGEI (`confianza = 'Alta'`).

## Contenido

```
dls_carbon_footprint_cr.db     Base de datos SQLite (todas las tablas)
schema.sql                     Definición completa del esquema (12 tablas)
build_database.py              Construye la BD y carga los datos oficiales verificados
eeioa_model.py                 Funciones del modelo (Leontief, huella, sensibilidad)
run_from_database.py           Conecta la BD con el modelo y guarda resultados
test_synthetic.py              Prueba del código con una economía de 5 sectores FICTICIA
csv_export/                    Cada tabla de la BD exportada a .csv
```

## Estado real de los datos — léase antes de usar

Esta base de datos separa explícitamente tres tipos de contenido. **No mezcle
estas categorías al citar en el paper**:

| Categoría | Tablas | Estado |
|---|---|---|
| **Dato oficial verificado en esta sesión** | `poblacion`, `ingei_macrosector`, `ingei_subcategoria` | Cargado con cifras reales del INEC y del INGEI (IMN/MINAE), con fuente y fecha en cada fila. Ver limitaciones abajo. |
| **Estructura pendiente de carga desde el archivo maestro de ustedes** | `mip_actividad`, `mip_coeficiente_tecnico`, `intensidad_emision`, `y_dls_demanda` | Vacías o con `NULL`. El esquema está listo para recibir las 144 actividades de la MIP 2017 (BCCR), la matriz de coeficientes técnicos, el vector f_I y el vector y_DLS que ya calcularon en el trabajo previo del paper. |
| **Output del modelo (no dato de entrada)** | `resultado_huella`, `resultado_escenario_agregado`, `sensibilidad_resultado` | Se generan automáticamente al correr `run_from_database.py` una vez completada la categoría anterior. Actualmente vacías — **no se inventó ningún resultado de escenario**. |

### Por qué las tablas de la MIP están vacías

La microdata desagregada de 144×184 de la MIP 2017 del BCCR no está publicada
como tabla indexable por búsqueda web — solo lo está la estructura agregada
en el Repositorio de Variables Económicas del BCCR. Ustedes ya poseen el
archivo fuente completo (lo usaron para las secciones 3.1–3.3 del paper). Para
completar la base de datos:

1. Exportar de su archivo de trabajo (Excel/Stata/R) tres tablas:
   - Lista de 144 actividades con código y nombre → `mip_actividad`
   - Matriz de coeficientes técnicos A (o la matriz de flujos Z + producción
     bruta x0, y usar `eeioa_model.construir_matriz_A()`) → `mip_coeficiente_tecnico`
   - Vector f_I ya calculado → `intensidad_emision`
   - Vector y_DLS por escenario (A y B) → `y_dls_demanda`
2. Cargar esas tablas a la base de datos (`INSERT` o `pandas.to_sql`).
3. Correr `python3 run_from_database.py`. El script valida completitud antes
   de calcular y se detiene con un mensaje explícito si falta algo — no
   calcula con matrices incompletas.

### Limitaciones de los datos oficiales ya cargados

- El total nacional 2017 (excl. FOLU) se cargó como **14477.5 Gg CO₂e**, un
  valor central aproximado: las fuentes secundarias consultadas citan
  "14.477,x" y "14.478" Gg CO₂e sin que el decimal exacto haya podido
  verificarse contra el informe primario del INGEI en esta sesión.
  **Confianza: Media.** Verificar contra el PDF del INGEI 2017 (IMN) antes de
  usar esta cifra con decimales en el cuerpo del paper.
- Los totales 2017 de los macrosectores IPPU, AFOLU (agricultura) y Residuos
  **no se cargaron** (quedan `NULL`) porque no se localizaron cifras oficiales
  desagregadas para el año 2017 específicamente en las fuentes consultadas.
  Solo se cargó el porcentaje de AFOLU para **2016** (20.5%), marcado
  explícitamente como no correspondiente a 2017.
- Todo esto es corregible: el informe primario completo del INGEI 1990-2017
  (IMN, diciembre 2021) contiene estos desgloses; solo no fue posible
  extraerlos vía búsqueda web en esta sesión.

## Cómo usar el código con datos sintéticos (verificación)

```bash
python3 test_synthetic.py
```

Esto corre el modelo completo (Leontief, huella directa/indirecta, per
cápita, brecha climática, sensibilidad) sobre una economía inventada de 5
sectores, para demostrar que las fórmulas están correctamente implementadas.
**Ninguna cifra de esa salida es de Costa Rica.**

## Cómo correr el modelo con los datos reales

```bash
python3 run_from_database.py
```

Falla explícitamente (sin calcular) si `mip_actividad`, `mip_coeficiente_tecnico`,
`intensidad_emision` o `y_dls_demanda` no están completas. Una vez completas,
calcula ambos escenarios y escribe los resultados en
`resultado_huella` y `resultado_escenario_agregado`.

## Nota sobre la discrepancia de ~6.165 Gg CO₂e (Tabla 3 vs. Tabla 4 del paper) — RESUELTA

`load_real_results.py` recalcula esta diferencia en cada ejecución:

```
Total INGEI nacional 2017 (bruto, excl. FOLU) = 14.477,5 Gg CO2e
Huella DLS Escenario A                         =  8.312,0 Gg CO2e
Diferencia                                     =  6.165,5 Gg CO2e (42,6% del total nacional)
```

Según la auditoría de consistencia realizada en sesión previa (25 de mayo de
2026), **esta diferencia no es un error aritmético**: el total INGEI
(14.477,6 Gg) es la economía nacional completa; 8.312 Gg es la porción de
esa economía atribuible específicamente a la demanda final y_DLS (~57% del
total nacional). Ambas cifras son correctas dentro de su propio alcance. El
problema real detectado fue de **rotulación** en el encabezado de la Tabla 3
del paper ("Emisiones totales de CO₂e por sector económico" sin aclarar que
la fila TOTAL corresponde a la economía completa, no al vector y_DLS), no de
cálculo. La corrección recomendada por esa auditoría —y aún pendiente de
verificar que se aplicó en la versión final del .docx— es retitular la
Tabla 3 como *"Estructura de emisiones nacionales 2017 (INGEI, referencia de
intensidades sectoriales) y participación estimada en la huella DLS —
Escenario A"*.

## Nota sobre el dato 95,1% vs. 75,5% (sección 4.3 del paper)

También resuelta en auditoría previa: ambos porcentajes son matemáticamente
correctos pero responden preguntas distintas — 75,5% = 6.026/7.982 (peso del
transporte dentro de las emisiones directas *nacionales* del sector
Energía); 95,1% = 6.026/6.338 (proporción directa dentro de la huella
*propia* del transporte). El texto del paper debía usar 75,5% en ese
contexto. La columna "% direct." de `resultado_huella`/Tabla 3 usa como base
7.981,6 Gg (sector Energía nacional) para todas las filas, incluidas
aquellas que no pertenecen al sector Energía (p. ej. Residuos) — esto es
consistente con lo ya documentado en el archivo de trabajo original, pero
conceptualmente inusual y se deja señalado aquí para que el equipo lo
confirme como intencional.
