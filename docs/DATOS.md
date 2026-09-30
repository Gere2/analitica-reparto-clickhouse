# Datos

Los ficheros van en `datos/` y **no se suben a git** (pesan cientos de MB). Cada miembro los
descarga desde las fuentes originales.

| Fuente | Qué contiene | Qué podemos afirmar | Uso |
|---|---|---|---|
| [MT-LIFT (Meituan)](https://mtdjdsp.github.io/MT-LIFT/) | 5.541.842 registros reales de campañas de una app de reparto de comida, con clic y conversión | Qué promociones generan clics y compras | Conjunto principal |
| [Censo de locales de Madrid](https://datos.madrid.es/dataset/209548-0-censo-locales-historico) | Locales con actividad, distrito y ubicación | Que los restaurantes de la app existen | Tabla `restaurantes` |
| [Criteo Uplift v2.1](https://huggingface.co/datasets/criteo/criteo-uplift) | 13.979.592 filas reales de un experimento aleatorizado de **publicidad**: tratamiento, exposición, visita y conversión | Cuánto aumenta una campaña las visitas y compras (uplift) | **Cargado.** Provisional mientras llega MT-LIFT (acceso pedido en Drive) |
| [OTTO](https://github.com/otto-de/recsys-dataset) | 216,7 M de eventos reales de clic, carrito y pedido por sesión (e-commerce) | Recorridos reales y abandono | Plan B si el profesor exige recorridos reales |
| Nuestra app | Clics que hagamos durante la demo (`origen = 'app_real'`) | Que el sistema funciona de extremo a extremo | `eventos_app` |
| `scripts/simular_sesiones.py` | Sesiones generadas (`origen = 'simulado'`) | **Nada sobre usuarios reales**: solo prueba de escala | `eventos_app` |

## Límite que hay que explicar

MT-LIFT registra clic y conversión de **promociones**, pero no dice si el usuario pasó por
búsqueda, menú o carrito. El embudo por secciones sale de nuestra app y de las sesiones simuladas.
Los usuarios de MT-LIFT y los de nuestra app son distintos: **no se cruzan**.

## Cargar Criteo

1. Descargar `criteo-uplift-v2.1.csv` (el `.csv.gz` de Hugging Face, 311 MB, se descomprime a 3,2 GB).
2. Dejarlo en `datos/criteo-uplift-v2.1.csv`.
3. `bash scripts/cargar_criteo.sh` → unos 20 s; debe terminar imprimiendo `13979592`.

En ClickHouse ocupa **262 MB** (1,27 GB sin comprimir): las columnas de etiquetas,
que van en la clave de ordenación, se quedan en unos KB.

## Pendiente

- [ ] MT-LIFT: Drive exige permiso (pedido el 30-09); la otra fuente oficial es Baidu
      (https://pan.baidu.com/s/1YmE5g-Y71ULNptiWqpToPA?pwd=06nb, requiere cuenta). Al tenerlo: ver sus columnas reales y escribir `scripts/cargar_mtlift.sql`
      (tabla `mtlift_promos`, `ENGINE = MergeTree ORDER BY (tratamiento, fila)`).
- [ ] Descargar el censo, filtrar la hostelería y escribir `scripts/cargar_censo.sql`
      (tabla `restaurantes`).
