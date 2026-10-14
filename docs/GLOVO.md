# Glovo FooDI-ML: procedencia y análisis

## Fuente

[FooDI-ML](https://github.com/Glovo/foodi-ml-dataset) fue publicado por Glovo para investigación. El CSV oficial se distribuye desde el bucket público enlazado en su repositorio. El [artículo de los autores](https://arxiv.org/html/2110.02035v2) explica cómo se formó la muestra: productos que tuvieron imagen en la aplicación, de 37 países. La licencia publicada es CC BY-NC-SA. El proyecto no redistribuye el CSV ni descarga las imágenes.

El fichero descargado el 4 de octubre de 2026 tenía **565.423.032 bytes** y SHA-256:

```text
09180fb4d34347dc210138bed9ef8bab588bc541824223a546d19e139a42f683
```

El tamaño y la huella están fijados en `scripts/glovo.py` para detectar cambios o descargas incompletas. Una nueva versión del dataset requeriría comprobar sus campos y actualizar esas constantes de forma explícita.

## Granularidad y campos

Cada fila del CSV representa una muestra de producto. El ETL carga `source_row`, `country_code`, `city_code`, `store_name`, `product_name`, `collection_section`, `product_description`, `has_description`, `aux_store` y `hier`. Los valores de `aux_store` y `hier` vienen del CSV original. `has_description` se deriva de si `product_description` está vacío.

La tabla `delivery.glovo_products` usa `MergeTree ORDER BY (country_code, city_code, store_name, source_row)`. Así, los filtros de país y ciudad del dashboard se alinean con el orden de almacenamiento. Las consultas agrupan millones de filas mediante `count()`, `uniqExact()` y `GROUP BY`. No se une con las tablas de Meituan: los datasets no comparten identificadores, lugar ni periodo.

## Recuentos comprobados

| Ámbito | Productos |
|---|---:|
| Todos los países | 2.887.444 |
| España (`ES`) | 415.137 |
| Barcelona (`ES/BCN`) | 132.568 |
| Madrid (`ES/MAD`) | 68.575 |

Dentro de España aparecen **266 códigos de ciudad**, **12.633 nombres de tienda distintos** y **116.475 productos con descripción** (28,1 %). Son resultados de la carga actual, comprobados contra el CSV y ClickHouse.

## Consultas útiles para la demo

```sql
SELECT count() FROM delivery.glovo_products;
SELECT count() FROM delivery.glovo_products WHERE country_code = 'ES';

SELECT city_code, count() AS productos
FROM delivery.glovo_products
WHERE country_code = 'ES'
GROUP BY city_code ORDER BY productos DESC LIMIT 10;

SELECT collection_section, count() AS productos
FROM delivery.glovo_products
WHERE country_code = 'ES' AND city_code = 'MAD'
GROUP BY collection_section ORDER BY productos DESC LIMIT 10;
```

## Límites de interpretación

- No hay clics, usuarios, pedidos, precios ni marca temporal por producto. El panel mide **oferta del catálogo**, no demanda ni ventas.
- La fuente incluye artículos no alimentarios. Las secciones son texto introducido por tiendas y no categorías uniformes.
- Solo aparecen productos que tuvieron imagen. No se puede estimar el catálogo completo de Glovo a partir de esta muestra.
- `store_name` es un nombre, no una clave única de establecimiento. Las métricas de tiendas cuentan nombres distintos.
- Los 9,5 millones citados por los autores son muestras de texto asociadas a los productos; el CSV cargado contiene 2.887.444 filas de producto.
