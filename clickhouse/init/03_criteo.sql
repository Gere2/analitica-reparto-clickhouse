-- Criteo Uplift v2.1: ~14 M de filas REALES de un experimento aleatorizado de publicidad.
-- Provisional hasta tener MT-LIFT (misma estructura: tratamiento + clic/visita + conversión).
-- Fuente: https://huggingface.co/datasets/criteo/criteo-uplift  ·  carga: scripts/cargar_criteo.sh
CREATE TABLE IF NOT EXISTS reparto.criteo_uplift
(
    f0 Float64, f1 Float64, f2 Float64, f3 Float64, f4 Float64,  f5 Float64,
    f6 Float64, f7 Float64, f8 Float64, f9 Float64, f10 Float64, f11 Float64,   -- anónimas
    treatment  UInt8,   -- 1 = vio la campaña (grupo tratado), 0 = grupo de control
    conversion UInt8,   -- compró
    visit      UInt8,   -- visitó la web (equivale al clic)
    exposure   UInt8    -- el anuncio se llegó a mostrar de verdad
)
ENGINE = MergeTree
-- Las etiquetas van en la clave: se repiten muchísimo y así comprimen casi a cero
ORDER BY (treatment, exposure, visit, conversion);
