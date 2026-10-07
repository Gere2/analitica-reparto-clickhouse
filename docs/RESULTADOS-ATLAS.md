# Delivery Atlas v1: resultados comprobados

Fecha: 7 de octubre de 2026. Evidencia exportada para el equipo: [evidencia-atlas.json](evidencia-atlas.json). Nodo local ClickHouse **25.8.33.6**, API Python y cola persistente. Estos resultados describen la base `delivery_atlas`, no el laboratorio OTTO.

## Carga de un millón de eventos

```bash
python3 scripts/atlas.py generate --events 1000000 --batch 5000 --seed 42 --start 2026-10-06T10:00:00Z
```

- Run ID: `f1a78bc7-67f2-5a8a-af17-a6d9ca6bbfc9`.
- **1.000.000 eventos generados, aceptados y verificados en ClickHouse con `FINAL`**, filtrando ese run ID. No es solo el número solicitado al generador.
- 323,59 segundos de envío, unos 3090 eventos/s. Incluye generar, validar y confirmar recepción en cola; no es una medición aislada de la velocidad de inserción de ClickHouse.
- Al finalizar, pendientes = 0. Hubo un error transitorio de publicación y el publicador se recuperó; el error final era nulo.
- Tres ciudades y sesiones de cinco pasos completos. Son eventos `synthetic`, con horarios simulados, sin abandonos. No describen usuarios, demanda ni conversión reales.

## Integridad y recuperación

| Prueba | Resultado |
|---|---|
| Repetir el mismo evento por HTTP | Segunda petición: aceptados 0, duplicados 1 |
| Reutilizar el ID con otro contenido | HTTP 409; no se acepta el cambio |
| Acción no admitida | HTTP 400 |
| Simular respuesta perdida después de insertar y volver a publicar | 3 filas físicas, **2 eventos lógicos**; detalle y agregado coinciden |
| Parar ClickHouse, aceptar un evento en cola y reiniciar la API | El evento pendiente llegó después, con recuento lógico 1 |
| Repetir ese evento después del reinicio | Aceptados 0, duplicados 1 |

Las cuatro pruebas unitarias de contrato/cola pasaron. Los scripts de integración y recuperación comprobaron el recorrido real con ClickHouse. La recuperación probó **paradas ordenadas y conservación de volúmenes**, no pérdida de disco, corte abrupto de energía ni alta disponibilidad.

La prueba de respuesta perdida usó un publicador temporal. Por ello el total en ClickHouse puede superar en una unidad lo publicado por la cola principal. La recuperación añadió otro evento después del benchmark. No comparar contadores de ámbitos o momentos distintos como si fueran el mismo total.

## Detalle frente al agregado: la misma respuesta, distinto coste

Benchmark sin carga concurrente, cola vacía, caché SQL desactivada, tres consultas por alternativa. **1.000.002 eventos lógicos, 16 grupos**, antes de la prueba de recuperación.

| Consulta | Mediana del tiempo de pared | Filas leídas reportadas por ClickHouse |
|---|---:|---:|
| Detalle `app_events FINAL`, agrupando dimensiones | **0,498 s** | 1.331.610 |
| Agregado exacto `app_daily_counts` | **0,703 s** | 31 |

**El agregado no fue más rápido en esta prueba.** Los estados de IDs únicos protegen el recuento frente a reenvíos, pero cuestan memoria y trabajo de combinación. Leer menos filas no garantiza tardar menos. Los contadores de bytes/filas del servidor no representan toda la memoria ocupada por los estados. La caché del sistema y el calentamiento no se controlaron; esta es una comparación local, no una capacidad garantizada.

La mejora de 27,9 veces medida antes con OTTO corresponde a otro esquema y otra consulta. No se atribuye a Atlas. El siguiente trabajo de Jere es medir el tamaño de estos estados y estudiar una optimización que mantenga las mismas garantías de reintento.

## Estado y límites de la entrega

**Implementado:** SQL aplicado, validación, cola, publicación por lotes, endpoints, generador, pruebas y contenedores con persistencia.

**Pendiente:** miniapp de Anuar, dashboard específico de Echenique, ejecución independiente en otro ordenador, retraso hasta el panel, carga con abandonos y ensayo. El script existente `scripts/crud_demo.py` permite mostrar INSERT/SELECT/UPDATE/DELETE en `delivery.demo_events`; no editar ni borrar el flujo analítico Atlas como si sus agregados se recalcularan solos.

Un nodo ClickHouse, una API y una cola local. No se ha demostrado replicación, sharding ni recuperación ante pérdida de disco. La cola conserva payloads publicados y crece: hace falta medir y diseñar su limpieza antes de llamarla solución de producción.
