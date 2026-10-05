# Plataforma ficticia de comida a domicilio: alcance y diseño

Estado: **diseño propuesto; pendiente de implementación y medición**. Añadido el 5 de octubre de 2026 a partir de la orientación del profesor transmitida por el grupo.

## Objetivo

Crear una plataforma ficticia inspirada en Uber Eats/Glovo y su infraestructura de analítica de navegación. Debe recibir eventos, conservarlos, agregarlos y mostrarlos en un dashboard mientras llegan nuevos lotes. El caso permite diseñar con datos semirreales ahora y conectar fuentes reales compatibles en el futuro.

El entregable principal de BD2 es el modelo y funcionamiento de la base analítica, con un pequeño recorrido de aplicación para generar eventos. Las cuentas, cobros y asignación real de repartidores quedan fuera de este alcance.

## Recorrido mínimo de aplicación

1. Elegir una ciudad y explorar restaurantes.
2. Buscar y filtrar resultados.
3. Abrir un restaurante y su menú.
4. Abrir un producto y añadirlo al carrito.
5. Completar un pedido simulado o terminar la sesión.

Registrar por separado impresiones, clics, acciones de carrito y pedido simulado. Una impresión solo se registra si el elemento cumple el criterio de visibilidad definido por la aplicación; no se deduce de una etiqueta negativa de Ele.me. Un pedido simulado no es una venta real.

## Arquitectura propuesta

```text
Miniapp de reparto ─────┐
Generador reproducible ├─→ API de eventos Python → validación → inserción por lotes
Fuente real + adaptador┘                                      │
                                                        ClickHouse
                                                  eventos → agregados
                                                              │
                                                        API → dashboard
```

Inicialmente basta una API Python y un nodo ClickHouse. Una cola externa o varios nodos solo se añaden si una medición identifica su necesidad o se eligen como experimento de clase. Definir límites de lote y cola, respuesta ante saturación y política de reintentos antes de aceptar un generador de alto volumen.

## Contrato de eventos v1, pendiente de concretar en código

| Campo | Función |
|---|---|
| `schema_version` | Versión del formato para evolucionar sin reinterpretar eventos antiguos |
| `event_id` | ID estable del evento, conservado en reintentos |
| `event_time` / `ingested_at` | Momento del suceso y momento de entrada en la infraestructura |
| `event_type` / `section` | Acción y lugar de la aplicación |
| `session_id` / `user_id` | Identificadores de la sesión y usuario ficticio o seudónimo |
| `restaurant_id` / `product_id` | Referencias opcionales según el evento |
| `city_id` | Contexto geográfico, sin inventar nombres para códigos anónimos |
| `source` / `source_kind` | Fuente y procedencia: `synthetic`, `demo_live`, `public_historical` o `historical_replay` |
| `source_record_id` / `simulation_run_id` | Trazabilidad de origen o ejecución del generador |

Los IDs de fuentes independientes requieren un espacio de nombres; una coincidencia numérica no demuestra que sean el mismo usuario o producto. Conservar los campos desconocidos como ausentes y registrar eventos rechazados con su motivo.

`event_id` por sí solo no evita duplicados en `MergeTree`: antes de activar agregados incrementales hay que implementar y probar cómo se detectan reintentos y cómo se cuentan eventos únicos. No prometer entrega exactamente una vez sin comprobar ese mecanismo.

## Papel de los datos actuales

| Fuente | Uso permitido en este diseño |
|---|---|
| Glovo FooDI-ML | Posible base de catálogo semirreal, con atribución y revisión de condiciones; los clics generados sobre él serían simulados |
| Ele.me | Caso real separado de recomendaciones; inspirar campos y distribuciones de prueba, identificando cualquier distribución sintetizada |
| OTTO | Referencia de clickstream, replay y experimento de volumen; adaptador solo para acciones y campos equivalentes |
| REES46 | Referencia de vistas, carrito, compra y filtros temporales; mantener las diferencias semánticas |
| Escenarios OTTO derivados | Prueba de estrés ya ejecutada, separada de la carga que genere la nueva aplicación |

Ele.me contiene muestras para aprendizaje, no un registro completo de cada paso de una sesión: sus negativos no se transforman en impresiones, ni sus historiales repetidos en nuevos clics. Las fuentes permanecen en sus tablas originales para conservar evidencia. Un adaptador común solo admite eventos con correspondencia semántica comprobada.

No se atribuye a Glovo España el comportamiento de usuarios de Ele.me/OTTO/REES46. Si el generador combina un catálogo y usuarios ficticios, el manifiesto lo declara como datos semirreales y documenta todas las suposiciones.

## Qué mostraría el dashboard

- Eventos y clics por tiempo, ciudad, sección y tipo.
- Sesiones y acciones de navegación, con definición explícita de sesión.
- Recorrido por etapas, contando sesiones únicas y respetando el orden temporal y una ventana definida. Una razón entre recuentos de clics y pedidos no basta para medir conversión.
- Tasa de entrada, retraso entre `event_time` e `ingested_at`, rechazos y reintentos.
- Volumen, tamaño en disco y comparación entre consulta al histórico y al agregado, con respuesta idéntica verificada.
- Filtro visible por procedencia; las métricas simuladas no se presentan como demanda real del mercado.

## Criterios de aceptación antes de presentarlo como terminado

1. Un recorrido manual llega desde la miniapp hasta ClickHouse y aparece en el dashboard.
2. El generador tiene semilla, parámetros y manifiesto de ejecución; reproduce la misma carga lógica y documenta horarios, sesiones y probabilidades inventados.
3. Se comprueban filas recibidas, aceptadas, rechazadas y duplicadas, incluyendo un reintento deliberado. Los reintentos no aumentan los eventos lógicos del dashboard.
4. Una carga grande se ejecuta y mide realmente: tasa efectiva, latencia de consulta y retraso de visualización, condiciones y recursos. No hay aún un objetivo de rendimiento alcanzado para esta plataforma.
5. Histórico y agregado responden a la misma consulta con resultados iguales. Guardar tiempo, filas y bytes leídos; no trasladar los benchmarks anteriores a una tabla distinta.
6. Un compañero reproduce la ruta principal siguiendo las guías, sin descargar datos durante la exposición.

## Incorporación futura de datos reales

Solicitar formato, campos disponibles, significado de acciones, zona horaria, estabilidad de IDs y condiciones de uso. Implementar un adaptador versionado y comprobar una muestra antes de publicar datos completos. Si faltan campos para una métrica, deshabilitarla o señalar su cobertura; no completarlos con hechos inventados.

El contrato reduce cambios en el dashboard, pero no garantiza aceptar cualquier fichero sin adaptar nada. La incorporación se comprueba comparando recuentos, procedencia y significado con la fuente. La infraestructura se considera preparada cuando ese procedimiento se haya implementado y ensayado.
