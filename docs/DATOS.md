# Datos

Los ficheros van en `datos/` y **no se suben a git** (pesan cientos de MB). Cada miembro los
descarga desde las fuentes originales.

| Fuente | Qué contiene | Qué podemos afirmar | Uso |
|---|---|---|---|
| [MT-LIFT (Meituan)](https://mtdjdsp.github.io/MT-LIFT/) | 5.541.842 registros reales de campañas de una app de reparto de comida, con clic y conversión | Qué promociones generan clics y compras | Conjunto principal |
| [Censo de locales de Madrid](https://datos.madrid.es/dataset/209548-0-censo-locales-historico) | Locales con actividad, distrito y ubicación | Que los restaurantes de la app existen | Tabla `restaurantes` |
| [OTTO](https://github.com/otto-de/recsys-dataset) | 216,7 M de eventos reales de clic, carrito y pedido por sesión (e-commerce) | Recorridos reales y abandono | Plan B si el profesor exige recorridos reales |
| Nuestra app | Clics que hagamos durante la demo (`origen = 'app_real'`) | Que el sistema funciona de extremo a extremo | `eventos_app` |
| `scripts/simular_sesiones.py` | Sesiones generadas (`origen = 'simulado'`) | **Nada sobre usuarios reales**: solo prueba de escala | `eventos_app` |

## Límite que hay que explicar

MT-LIFT registra clic y conversión de **promociones**, pero no dice si el usuario pasó por
búsqueda, menú o carrito. El embudo por secciones sale de nuestra app y de las sesiones simuladas.
Los usuarios de MT-LIFT y los de nuestra app son distintos: **no se cruzan**.

## Pendiente

- [ ] Descargar MT-LIFT, ver sus columnas reales y escribir `scripts/cargar_mtlift.sql`
      (tabla `mtlift_promos`, `ENGINE = MergeTree ORDER BY (tratamiento, fila)`).
- [ ] Descargar el censo, filtrar la hostelería y escribir `scripts/cargar_censo.sql`
      (tabla `restaurantes`).
