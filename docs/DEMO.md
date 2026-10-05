# Guion de demo en directo: 10 minutos

## Antes de entrar en clase

Completar las cargas siguiendo [INSTALACION.md](INSTALACION.md). Tener abiertos el [panel OTTO](http://127.0.0.1:8000/), el [panel REES46](http://127.0.0.1:8000/rees46.html), el [panel de escala](http://127.0.0.1:8000/scale.html), las [diapositivas](http://127.0.0.1:8000/otto-presentacion.html) y dos terminales. Guardar `data/query-benchmark.json` tras correr `python3 scripts/benchmark.py` y ejecutar `python3 scripts/check.py` para verificar el conjunto. No descargar ni cargar decenas de GB durante la exposición.

Cliente SQL:

```bash
docker exec -it bd2-clickhouse clickhouse-client --user demo --password demo --database delivery
```

## Secuencia

**0:00–1:00 — Fuentes y volumen.** Mostrar el dashboard OTTO y contar:

```sql
SELECT event_type, count() AS eventos
FROM otto_archive GROUP BY event_type ORDER BY event_type;
```

Resultado esperado del conjunto completo: 194.720.954 clics, 16.896.191 carritos, 5.098.951 pedidos. Indicar que son históricos y reales.

**1:00–2:00 — Segunda fuente real.** Abrir REES46. Filtrar un mes, enseñar el volumen por mes, categoría y marca. Explicar que sus `view` son vistas de producto, no clics OTTO; cada fuente está en su propia tabla. Los siete meses permiten una dimensión temporal que OTTO no tiene.

**Alternativa centrada en comida a domicilio:** abrir [Ele.me](http://127.0.0.1:8000/eleme.html). Mostrar 2.170.299 muestras y 38.914 etiquetas positivas del primer ZIP completo; recorrer horas y periodos de comida. Explicar que es una plataforma china, que el 1,79 % no es el CTR de producción y que los 146 millones anunciados por la fuente no están todos cargados. El panel es histórico. La consulta tipada de clics se midió en 0,0581 s; la lectura completa del JSON agotó la memoria local, sin comparación de tiempos finalizada. Consultar [ELEME.md](ELEME.md).

**2:00–4:00 — Ingesta y consultas simultáneas.** En el segundo terminal:

```bash
python3 scripts/otto.py replay --rate 5000 --limit 200000 --reset
```

Ver que el gráfico responde. En SQL, repetir esta consulta a los pocos segundos:

```sql
SELECT event_type, count() AS eventos
FROM otto_replay
WHERE ingested_at >= now64(3) - INTERVAL 30 SECOND
GROUP BY event_type;
```

`event_time` es la fecha real antigua; `ingested_at` es la inserción actual. No llamar al replay «clics nuevos de OTTO».

**4:00–5:00 — Clic genuinamente nuevo.** Pulsar «Explorar producto» y verificar que sube solo el contador de `live_clicks`:

```sql
SELECT section, action, clicked_at
FROM live_clicks ORDER BY clicked_at DESC LIMIT 5;
```

**5:00–7:00 — Experimento bruto frente a agregado.** Mostrar dos consultas con la misma respuesta:

```sql
SELECT toDate(event_time) AS dia, event_type, count() AS eventos
FROM otto_archive GROUP BY dia, event_type ORDER BY dia, event_type;

SELECT event_date AS dia, event_type, sum(events) AS eventos
FROM otto_daily_rollup GROUP BY dia, event_type ORDER BY dia, event_type;
```

Para no gastar tiempo imprimiendo 87 líneas dos veces, puede ejecutarse `python3 scripts/benchmark.py` antes de clase y abrir [RESULTADOS.md](RESULTADOS.md) o el [panel de escala](http://127.0.0.1:8000/scale.html) durante la demo. Enseñar `rows_read` y `bytes_read` medidos y que el script comparó las respuestas. El agregado tiene 87 claves día/tipo, aunque `SummingMergeTree` pueda conservar varias filas físicas por clave antes de fusionarlas.

**7:00–8:00 — Mil millones con procedencia clara.**

```sql
SELECT scenario, count() AS eventos
FROM otto_scale_benchmark GROUP BY scenario ORDER BY scenario;
```

Cada escenario contiene 216.716.096 filas. Los cinco escenarios son **derivados de OTTO**, no cinco conjuntos de clientes reales. Mostrar `data/scale-benchmark.json` y el informe de consultas.

**8:00–9:00 — Python y CRUD.** Ejecutar:

```bash
python3 scripts/crud_demo.py
```

La tabla de ensayo muestra inserción, lectura, actualización y borrado sin alterar el histórico. Señalar por qué el patrón principal en analítica es añadir eventos y consultar agregados.
El script pausa brevemente las fusiones de las tablas grandes para que la mutación síncrona de la tabla de ensayo no espere detrás de una compactación masiva; las reanuda en `finally`.

**9:00–10:00 — Arquitectura y preguntas.** Enseñar `sql/schema.sql`: `MergeTree`, particiones mensuales, claves de orden, vista materializada. Recordar que se ha ejecutado un nodo local; shards y réplicas son opciones explicadas, no presentes aquí.

## Si una parte falla durante la clase

- El replay es independiente del archivo ya cargado: los dos dashboards históricos siguen funcionando.
- Si el benchmark tarda demasiado, usar el JSON medido antes de clase y mostrar la consulta SQL.
- Si la tabla derivada no está cargada en el equipo de exposición, mantener OTTO + REES46 reales y explicar claramente que la prueba de estrés no se realizó allí.
- Evitar atribuir al conjunto datos de plataformas de reparto o de España.
