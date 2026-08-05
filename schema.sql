-- ============================================================================
-- Esquema de base de datos: Huella de carbono EEIOA asociada a DLS en Costa Rica
-- Autores del paper: [Ivannia] & Marco Otoya Chavarría (CINPE-UNA)
-- Generado como anexo técnico. Ver README.md para el estado de cada tabla
-- (dato oficial real / N/D pendiente de fuente primaria / placeholder de
-- estructura a poblar por los autores desde el archivo maestro BCCR-MIP2017).
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. POBLACIÓN OFICIAL (INEC)
-- ----------------------------------------------------------------------------
CREATE TABLE poblacion (
    anio            INTEGER PRIMARY KEY,
    poblacion_total INTEGER NOT NULL,
    poblacion_mujeres INTEGER,
    poblacion_hombres INTEGER,
    fuente          TEXT NOT NULL,
    fecha_fuente    TEXT NOT NULL,
    confianza       TEXT NOT NULL CHECK (confianza IN ('Alta','Media','Baja'))
);

-- ----------------------------------------------------------------------------
-- 2. INVENTARIO NACIONAL DE GEI (INGEI, IMN/MINAE) - nivel macrosector IPCC
-- ----------------------------------------------------------------------------
CREATE TABLE ingei_macrosector (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    anio             INTEGER NOT NULL,
    macrosector_ipcc TEXT NOT NULL,          -- Energia | IPPU | AFOLU | Residuos | FOLU
    emisiones_gg_co2e REAL,                  -- NULL = N/D
    pct_participacion REAL,                  -- NULL = N/D
    es_absorcion     INTEGER NOT NULL DEFAULT 0,  -- 1 = absorción neta (signo negativo ya aplicado)
    fuente           TEXT NOT NULL,
    fecha_fuente     TEXT NOT NULL,
    confianza        TEXT NOT NULL CHECK (confianza IN ('Alta','Media','Baja')),
    nota             TEXT
);

-- Subcategorías conocidas dentro de un macrosector (p.ej. transporte dentro de Energía)
CREATE TABLE ingei_subcategoria (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    anio                INTEGER NOT NULL,
    macrosector_ipcc    TEXT NOT NULL,
    subcategoria        TEXT NOT NULL,
    emisiones_gg_co2e   REAL,
    pct_del_macrosector REAL,
    fuente              TEXT NOT NULL,
    fecha_fuente        TEXT NOT NULL,
    confianza           TEXT NOT NULL CHECK (confianza IN ('Alta','Media','Baja'))
);

-- ----------------------------------------------------------------------------
-- 3. SECTORES MIP 2017 (BCCR) - 144 actividades x 184 productos
--    Esta tabla debe poblarse desde el archivo maestro BCCR-MIP2017 que
--    ya posee el equipo de investigación. Se deja la estructura lista.
-- ----------------------------------------------------------------------------
CREATE TABLE mip_actividad (
    codigo_actividad   TEXT PRIMARY KEY,     -- código interno MIP 2017 (144 actividades)
    nombre_actividad   TEXT NOT NULL,
    codigo_ciiu_rev4   TEXT,                 -- correspondencia CIIU Rev.4 (a validar)
    grupo_dls          TEXT,                 -- FK conceptual -> dls_categoria.codigo
    valor_produccion_bruta_mm_colones REAL,  -- de la MIP 2017; NULL = pendiente de carga
    fuente             TEXT DEFAULT 'BCCR - Matriz Insumo-Producto 2017',
    confianza          TEXT DEFAULT 'Pendiente de carga'
);

-- Matriz de coeficientes técnicos A (formato largo: fila = actividad compradora,
-- columna = actividad vendedora). Pendiente de carga desde archivo BCCR.
CREATE TABLE mip_coeficiente_tecnico (
    fila_actividad      TEXT NOT NULL REFERENCES mip_actividad(codigo_actividad),
    columna_actividad   TEXT NOT NULL REFERENCES mip_actividad(codigo_actividad),
    coeficiente_a       REAL,                -- a_ij ; NULL = pendiente de carga
    PRIMARY KEY (fila_actividad, columna_actividad)
);

-- ----------------------------------------------------------------------------
-- 4. VECTOR DE INTENSIDADES DE EMISIÓN (f_I) POR ACTIVIDAD MIP
--    tCO2e por millón de colones de producción. Pendiente de cálculo:
--    f_I = emisiones_sectoriales_INGEI_asignadas / valor_produccion_bruta_MIP
-- ----------------------------------------------------------------------------
CREATE TABLE intensidad_emision (
    codigo_actividad    TEXT PRIMARY KEY REFERENCES mip_actividad(codigo_actividad),
    intensidad_tco2e_por_mm_colones REAL,    -- NULL = pendiente
    metodo_asignacion   TEXT,                -- p.ej. 'proporcional a valor bruto de producción sectorial INGEI'
    fuente              TEXT DEFAULT 'INGEI 1990-2017 (IMN/MINAE) + MIP 2017 (BCCR), cálculo propio',
    confianza           TEXT DEFAULT 'Pendiente de cálculo'
);

-- ----------------------------------------------------------------------------
-- 5. CATEGORÍAS DLS Y VECTOR DE DEMANDA FINAL (y_DLS) POR ESCENARIO
-- ----------------------------------------------------------------------------
CREATE TABLE dls_categoria (
    codigo          TEXT PRIMARY KEY,        -- p.ej. 'ALIM','AGUA','ENER','VIV','TRAN','EDU','SALUD','TIC'
    nombre          TEXT NOT NULL,
    descripcion     TEXT
);

CREATE TABLE y_dls_demanda (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_actividad   TEXT NOT NULL REFERENCES mip_actividad(codigo_actividad),
    categoria_dls      TEXT NOT NULL REFERENCES dls_categoria(codigo),
    escenario          TEXT NOT NULL CHECK (escenario IN ('A','B')),
    anio_referencia    INTEGER NOT NULL,     -- 2025
    demanda_mm_colones REAL,                 -- NULL = pendiente de monetización
    fuente             TEXT,
    confianza          TEXT DEFAULT 'Pendiente de cálculo'
);

-- ----------------------------------------------------------------------------
-- 6. RESULTADOS DEL MODELO (huella por actividad y escenario) - OUTPUT, no input
-- ----------------------------------------------------------------------------
CREATE TABLE resultado_huella (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    escenario             TEXT NOT NULL CHECK (escenario IN ('A','B')),
    codigo_actividad      TEXT NOT NULL REFERENCES mip_actividad(codigo_actividad),
    emision_directa_gg    REAL,
    emision_indirecta_gg  REAL,
    emision_total_gg      REAL,
    pct_participacion     REAL,
    fecha_calculo         TEXT,
    version_modelo        TEXT
);

CREATE TABLE resultado_escenario_agregado (
    escenario                  TEXT PRIMARY KEY CHECK (escenario IN ('A','B')),
    emisiones_totales_gg_co2e  REAL,
    poblacion_referencia       INTEGER,
    tco2e_per_capita           REAL,
    umbral_tco2e_per_capita    REAL DEFAULT 1.6,
    brecha_pct                 REAL,         -- (tco2e_per_capita - umbral)/umbral * 100
    pct_emisiones_indirectas   REAL,
    fecha_calculo              TEXT,
    version_modelo             TEXT
);

-- ----------------------------------------------------------------------------
-- 7. ANÁLISIS DE SENSIBILIDAD
-- ----------------------------------------------------------------------------
CREATE TABLE sensibilidad_supuesto (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    sector              TEXT NOT NULL CHECK (sector IN ('Transporte','Energia','Alimentacion')),
    nombre_supuesto     TEXT NOT NULL,       -- p.ej. 'electrificación flota', 'sustitución proteína animal'
    variacion_pct       REAL,                -- NULL = pendiente de definición por autores
    variable_afectada   TEXT,                -- 'f_I' | 'y_DLS'
    fuente_supuesto     TEXT,
    confianza           TEXT DEFAULT 'Pendiente de definición'
);

CREATE TABLE sensibilidad_resultado (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    supuesto_id            INTEGER NOT NULL REFERENCES sensibilidad_supuesto(id),
    escenario_base         TEXT NOT NULL CHECK (escenario_base IN ('A','B')),
    emisiones_totales_gg_ajustadas REAL,
    tco2e_per_capita_ajustado      REAL,
    brecha_pct_ajustada             REAL,
    fecha_calculo           TEXT
);
