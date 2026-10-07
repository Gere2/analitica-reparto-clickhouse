# Ele.me: recomendaciones de comida a domicilio

## Fuente y estado de la integración

[Recommendation Data From Ele.me, Tianchi, ID 131047](https://tianchi.aliyun.com/dataset/131047).
Consulta de la página oficial: **5 de octubre de 2026**.

- La descripción declara **128 millones de muestras de entrenamiento** de D1–D7 y **18 millones de test** de D8: 146 millones de muestras, **no de clics**.
- Proceden del recomendador de Ele.me, una plataforma de comida a domicilio de China. No representan Uber Eats, Glovo ni España.
- La primera columna es una etiqueta binaria: positivo si hubo clic, negativo en otro caso. El procedimiento de muestreo no queda suficientemente especificado para interpretar su proporción como CTR real de la aplicación.
- Se publican atributos anónimos de usuario, restaurante, producto y contexto, e historiales de hasta 50 elementos correspondientes a los 30 días anteriores.
- La descripción divide cada día en diez partes. En la lista visible se observaron **70 ZIP**, correspondientes a D1–D6 y D8. **D7 no aparecía**; la disponibilidad completa de los 146 millones debe verificarse antes de prometer ese volumen.
- Cada ZIP listado ocupa aproximadamente 4–5 GB. La colección visible supone del orden de 330 GB comprimidos; no se ha descargado ni medido localmente. Empezar con una parte, sin extraer el ZIP completo.
- La descarga pide iniciar sesión en Tianchi y confirmar su acuerdo de uso. Se ha comprobado el acceso con una cuenta internacional **sin vincular tarjeta bancaria**. El paso de pago de Alibaba Cloud no fue necesario para esta descarga.
- **Primer archivo oficial descargado:** `D1_0.csv.zip`, 4.993.698.626 bytes comprimidos. Contiene `D1_0.csv`, de 16.411.347.014 bytes sin comprimir. Se ha inspeccionado su estructura: CSV separado por comas, sin cabecera, 39 campos en el orden descrito por el publicador. Etiqueta binaria; `hours` entero 0–23; `time_type` contiene `breakfast`, `lunch`, `tea`, `dinner`, `night` en las primeras filas. La carga completa verifica el resto de filas y el CRC del ZIP.
- La página muestra una etiqueta de licencia CC BY-NC-SA 4.0, pero los enlaces de licencia visibles no son consistentes con ella. Revisar los términos efectivos en Tianchi antes de redistribuir los archivos. Esta integración enlaza la fuente y no redistribuye sus datos.

## Qué está integrado

- `sql/eleme.sql`: tabla `delivery.eleme_samples` y una tabla de staging con el mismo esquema.
- `scripts/eleme.py`: inspección, validación estricta, importación por lotes de hasta 25.000 filas **o 32 MiB** y publicación de archivos completos mediante `MOVE PARTITION`.
- `/eleme.html` y `/api/eleme`: muestras realmente cargadas, etiquetas positivas, proporción positiva, usuarios aproximados, días relativos, horas, ciudades anónimas y archivos importados.
- `/scale.html`: filas y tamaño en disco de Ele.me, separado del total OTTO + REES46.

El formato de **D1_0.csv** se ha contrastado con sus filas y con el orden de atributos de la descripción oficial. Que otro archivo tenga 39 columnas no demuestra su orden. `--confirm-layout` registra que el operador comprobó la correspondencia antes de cargar; no debe usarse para saltarse esta comprobación.

## Descarga e inspección

1. Iniciar sesión en la página oficial, revisar condiciones y descargar una parte, por ejemplo `D1_0.csv.zip`.
2. Guardarla en `data/eleme/` (ignorado por Git).
3. Inspeccionar la estructura:

```bash
python3 scripts/eleme.py inspect data/eleme/D1_0.csv.zip
```

Se prueban tabulador, coma, barra vertical y control-A. Solo se acepta automáticamente un separador si produce 39 campos en las primeras filas. El script no imprime los historiales de usuarios. Si el formato es distinto, adaptar el parser a la evidencia del archivo real; no inventar campos ni reinterpretar datos arbitrariamente.

El orden es: etiqueta; ocho atributos de usuario; trece de candidato; doce listas históricas; cinco de contexto. `FIELDS` contiene sus nombres. Verificar una cabecera o la documentación asociada al archivo. `hours` debe estar entre 0 y 23; `times` se conserva literalmente. Las primeras filas contienen valores compatibles con Unix en segundos de abril de 2022; no se asigna una zona horaria a partir del nombre del país sin verificarla.

## Carga después de comprobar el formato

```bash
docker compose up -d
python3 scripts/eleme.py init
python3 scripts/eleme.py load data/eleme/D1_0.csv.zip --day 1 --confirm-layout
python3 scripts/eleme.py status
python3 dashboard.py
```

`--delimiter comma` especifica el separador verificado en D1_0.csv. La lectura de ZIP es secuencial y no extrae archivos al disco. Se conserva cada campo en `raw_features` y se proyectan columnas tipadas para las consultas. Los historiales hacen que una fila JSON ocupe unos 9 KiB en la muestra inicial; el límite de bytes por lote mantiene la memoria del cliente acotada.

Las inserciones usan el API HTTP de ClickHouse desde Python (`urllib`), con `JSONEachRow`, un hilo, análisis paralelo desactivado y bloques de hasta 4.096 filas. El cliente nativo dentro de Docker se usa para crear tablas y mover particiones. Un error de inserción no se reintenta ciegamente: reanudar coteja las filas que el servidor haya confirmado, incluidas posibles inserciones parciales por bloques.

La huella SHA-256 del archivo y el nombre de su miembro identifican una partición. Una segunda carga del mismo archivo omite las muestras ya publicadas. El manifiesto local registra huella, miembro, día y filas. No debe renombrarse, recomprimirse o reorganizarse el mismo contenido y presentarlo como un dataset nuevo: el control por archivo no detecta duplicados semánticos entre archivos distintos.

Si falla una fila, la partición queda en staging y **no entra en el dashboard**. Un nuevo intento reconstruye solo esa partición de staging. `--resume-staging` permite continuar si el recuento, el mínimo, el máximo y los valores distintos de `source_row` acreditan una secuencia sin huecos ni duplicados. El ZIP vuelve a leerse desde el inicio para comprobar su CRC; se saltan las inserciones ya confirmadas. Tras validar el archivo completo y cotejar filas, `MOVE PARTITION` publica la partición en la tabla de análisis. Se procesa un solo importador a la vez con un bloqueo local. No hay vista materializada sobre esta tabla: mover partes no dispara vistas de inserción.

El cargador pausa las fusiones de las tablas grandes y las reanuda al terminar, también en caso de excepción. Si se mata el proceso a la fuerza, reanudarlas con `SYSTEM START MERGES` para las cinco tablas de la lista `tables` del cargador. Para las muestras anchas de Ele.me, el esquema reduce `merge_max_block_size` a 512 filas y limita el tamaño candidato de una fusión a 256 MiB. Esto se ajustó tras un error real de límite total de memoria en el equipo Docker de unos 4 GiB; la reanudación conserva los lotes confirmados.

## Medición de almacenamiento columnar

Después de completar la carga:

```bash
python3 scripts/eleme_report.py
```

El script mide el conteo de clics positivos mediante la columna `clicked`: tres consultas, un hilo y caché SQL desactivada. Registra filas/bytes leídos, mediana, tamaños de columnas y validez numérica de los timestamps en `data/eleme-benchmark.json`. Pausa las fusiones Ele.me durante las mediciones; la caché del sistema operativo permanece habilitada. Los tiempos son medidas locales.

**Resultado comprobado:** 38.914 clics positivos sobre 2.170.299 filas, mediana de **0,0581 segundos** (tres ejecuciones: 0,0753 / 0,0550 / 0,0581 segundos). Cada ejecución informó 2.170.299 filas y 426.681 bytes leídos. Estos bytes son la estadística del servidor; no representan el tamaño del archivo CSV ni todo el almacenamiento de la tabla.

La consulta equivalente extrayendo `clicked` de `raw_features` **no terminó**: alcanzó el límite total de memoria de 3,50 GiB del servidor. La última ejecución fallida había leído 1.561.645 filas y 12.785.529.641 bytes. No hay tiempo final, igualdad de respuestas verificada entre ambos métodos ni factor de aceleración medido. El informe conserva ese fallo previo del registro del servidor con su identificador de consulta, separado de las mediciones actuales.

Para intentar también esa lectura ancha, de forma opcional:

```bash
python3 scripts/eleme_report.py --include-raw
```

El script guarda el error si falla. Usa bloques de hasta 256 filas, tamaños preferidos de 1 MiB y búferes de lectura de 256 KiB; también con estos ajustes la consulta completa falló en este equipo. `raw_features` es **String** con JSON: esta prueba no evalúa el tipo nativo `JSON`, sus subcolumnas ni PostgreSQL. El límite observado aporta una reflexión sobre proyectar columnas útiles y dimensionar la memoria, sin demostrar que ClickHouse no pueda procesar JSON.

## Consultas para explicar ClickHouse

```sql
SELECT sample_day, count() AS samples, sum(clicked) AS positive_clicks,
       round(100.0 * positive_clicks / samples, 2) AS positive_pct
FROM delivery.eleme_samples
GROUP BY sample_day ORDER BY sample_day;

SELECT request_hour, city_id, count() AS samples, sum(clicked) AS clicks
FROM delivery.eleme_samples
WHERE sample_day = 1
GROUP BY request_hour, city_id
ORDER BY samples DESC LIMIT 20;

SELECT table, sum(rows), sum(bytes_on_disk)
FROM system.parts
WHERE database = 'delivery' AND table IN ('eleme_samples', 'eleme_staging') AND active
GROUP BY table;
```

`PARTITION BY source_id` se elige para publicar y recuperar archivos completos de este corpus finito (unas decenas de partes), **no** como recomendación para particionar una aplicación continua por evento o por usuario. `ORDER BY (sample_day, city_id, request_hour, category_id, shop_id, source_row)` favorece filtros que empiecen por día y ciudad. No se han comparado distintos órdenes físicos: para hacerlo, medir `read_rows`, `read_bytes` y tiempo sobre el mismo archivo real.

## Tiempo real y límites

Estos archivos son históricos. El panel consulta ClickHouse al aplicar un filtro; no está conectado a la plataforma Ele.me. El flujo de tiempo real existente del proyecto continúa siendo el replay etiquetado de OTTO y los nuevos clics en la página de demo. No duplicar historiales de las muestras para anunciar miles de millones de clics únicos.

La validación local de infraestructura puede usar una fixture artificial en tablas de ensayo y borrarla al terminar. Esa fixture no acredita el formato real del dataset ni aumenta los recuentos mostrados al profesor. La validación real se ha realizado sobre el primer ZIP oficial completo, además de la prueba de infraestructura anterior.

**Comprobación local realizada el 5 de octubre de 2026:** una fixture artificial de 25.001 filas atravesó dos lotes y se publicó mediante `MOVE PARTITION` en tablas de ensayo separadas. Repetir la carga mantuvo 25.001 filas; un segundo archivo con una fila inválida dejó sus 25.000 filas previas en staging sin publicarlas. Las tablas de ensayo se eliminaron al terminar. La API real respondió `samples=0`, `clicks=0`, `empty=true`, y el panel mostró la descarga pendiente. Ninguna fixture se cargó en `delivery.eleme_samples`.

## Primera carga real comprobada

Archivo `D1_0.csv.zip`, miembro `D1_0.csv`, leído completo y con CRC verificado por `zipfile`:

| Medida | Resultado |
|---|---:|
| Muestras publicadas | 2.170.299 |
| Etiquetas positivas de clic | 38.914 |
| Proporción positiva en esta parte | 1,79 % |
| Usuarios distintos estimados (`uniqCombined64`) | 1.344.158 |
| Restaurantes distintos estimados (`uniqCombined64`) | 421.934 |
| Filas pendientes en staging al finalizar | 0 |

SHA-256 del ZIP: `b94bbbb9d9bd3e46d1dda796d87610765f4079fc829d788629bbc5b3a3fa16e5`. Huella calculada localmente para trazabilidad; no se presenta como una huella publicada por Tianchi.

| Periodo | Muestras | Etiquetas positivas |
|---|---:|---:|
| Comida (`lunch`) | 730.137 | 12.738 |
| Cena (`dinner`) | 718.594 | 13.011 |
| Noche (`night`) | 447.494 | 8.366 |
| Desayuno (`breakfast`) | 175.257 | 2.969 |
| Merienda (`tea`) | 98.817 | 1.830 |

Los cinco grupos suman exactamente las muestras y etiquetas positivas publicadas. D2–D8 permanecen sin cargar; el panel muestra cero al filtrar por esos días. Estas muestras no se suman al total de eventos de OTTO y REES46.
