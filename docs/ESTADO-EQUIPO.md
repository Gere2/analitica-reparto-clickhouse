# Estado del proyecto para el equipo

## Actualización del 7 de octubre de 2026

Se ha implementado la infraestructura v1 en `delivery_atlas`: SQL, contrato, API Python en Docker, cola persistente SQLite, publicador y generador. La miniapp de reparto y el dashboard específico siguen pendientes. El reparto es **Jere: base e ingesta; Anuar: miniapp; Echenique: dashboard y reproducción**. Leer [PLAN-EQUIPO.md](PLAN-EQUIPO.md) y [INFRAESTRUCTURA-ATLAS.md](INFRAESTRUCTURA-ATLAS.md).

El SQL aplicado es `sql/atlas.sql`, con `ReplacingMergeTree` en el detalle y conjuntos de IDs en `AggregatingMergeTree` para los recuentos lógicos. La cola admite reintentos con el mismo ID y contenido; un cambio de contenido devuelve conflicto. La API está en el puerto 8001. El laboratorio histórico conserva su base y sus paneles.

**Guía para los tres:** [PDF del equipo](../output/pdf/Delivery-Atlas-Guia-Equipo.pdf). Se verificó un millón de eventos sintéticos, reintentos y recuperación tras paradas ordenadas. Detalle y agregado coinciden, pero el agregado no fue más rápido en la prueba nueva. [Resultados y condiciones](RESULTADOS-ATLAS.md).

Las secciones siguientes son la fotografía del 5 de octubre, anterior a esta implementación. Sus cifras describen las fuentes históricas y no se reutilizan como benchmarks de la base nueva.

Actualización: 5 de octubre de 2026. Este documento describe lo implementado y separa las propuestas que aún debe decidir el grupo.

## Qué está hecho

- ClickHouse 25.8 en un nodo Docker, volumen persistente y API Python.
- Carga, validación y dashboards de fuentes reales; scripts de Python y SQL.
- Vista materializada y agregado diario de OTTO.
- Reproducción de eventos históricos mientras se consulta el dashboard y clics nuevos de la propia página, en tablas separadas.
- Script de inserción, consulta, actualización y borrado en una tabla de ensayo.
- Documentación de instalación, fundamentos, demo y resultados; diapositivas navegables.

| Fuente | Carga verificada en el equipo de desarrollo | Papel |
|---|---:|---|
| OTTO | 216.716.096 eventos; 194.720.954 clics | Volumen, clics y agregación |
| REES46 | 411.709.736 eventos, siete meses | Tiempo, categorías, marcas, vistas, carritos y compras |
| Ele.me | 2.170.299 muestras; 38.914 etiquetas positivas | Recomendaciones de comida a domicilio en China; primer ZIP D1_0 |
| Glovo FooDI-ML | 2.887.444 productos; 415.137 de España | Catálogo, sin clics ni ventas |
| Estrés derivado de OTTO | 1.083.580.480 filas | Cinco escenarios derivados; no observaciones nuevas |

OTTO y REES46 suman 628.425.832 eventos reales de poblaciones diferentes. Las muestras de Ele.me y los productos de Glovo no se mezclan con ese total. No existen identificadores comunes para atribuir los clics de Ele.me a productos españoles de Glovo.

## Evidencia técnica

- Misma agregación diaria OTTO: 5,8908 s desde el histórico frente a 0,2113 s desde el agregado; respuestas iguales y caché SQL desactivada. Mediana de tres ejecuciones locales.
- Agrupación por escenarios sobre 1.083.580.480 filas derivadas: 1,4357 s, una ejecución local.
- Conteo de etiquetas positivas Ele.me: mediana de 0,0581 s para 2.170.299 filas, tres ejecuciones locales.
- La lectura completa del JSON de Ele.me agotó el límite total de memoria local de 3,50 GiB. No hay comparación de tiempos completada entre JSON y columna tipada.

Estos resultados no comparan ClickHouse con PostgreSQL ni acreditan rendimiento en otro equipo. Los informes originales están en `data/*benchmark.json`; [RESULTADOS.md](RESULTADOS.md) y [ELEME.md](ELEME.md) explican condiciones y límites.

## Qué contiene GitHub

Código, SQL, configuración Docker, paneles, documentación, capturas de resultados y pequeños informes de mediciones. Los ZIP/CSV y el volumen Docker **no se suben**: clonar el repositorio no descarga los millones de filas. Las instrucciones enlazan las fuentes y permiten cargar los datos. Ele.me requiere cuenta Tianchi y revisión de sus condiciones; no se redistribuye el archivo.

Para esta versión usar `compose.yaml` y [INSTALACION.md](INSTALACION.md). Se conservan archivos de la versión anterior del repositorio con Flask/Grafana; sus instrucciones, puertos y métricas no describen esta implementación. Las presentaciones antiguas y paneles de los primeros enfoques son material de trabajo, no el guion definitivo.

## Encaje con el enunciado

Hay datasets reales, dashboard, integración Python, CRUD, modelo columnar y mediciones. Las guías cubren instalación, arquitectura, consistencia, escalado y reflexión crítica. Se ha ejecutado un nodo: la replicación y el reparto entre nodos están explicados, no demostrados. Falta comprobar que ClickHouse encaja con la tecnología asignada en la sección «Personas»: utiliza SQL y debe presentarse como motor analítico columnar.

## Dirección del proyecto y decisiones pendientes

**Delivery Atlas: infraestructura analítica de una plataforma ficticia de comida a domicilio.**

**Nueva dirección indicada por el profesor y añadida por el grupo:** definir una plataforma ficticia de comida a domicilio, con una infraestructura analítica para sus eventos. El recorrido de navegación y una carga masiva pueden ser simulados y deben identificarse como tales. Un contrato de eventos y adaptadores permitirían incorporar datos reales futuros sin cambiar todas las consultas y paneles. Véase [PLATAFORMA-FICTICIA.md](PLATAFORMA-FICTICIA.md).

El [mapa de la base de datos](ESTRUCTURA-BD.md) explica el laboratorio actual y el modelo propuesto. La [presentación de avance y sus notas](AVANCE-PRESENTACION.md) están en inglés, duran 5 minutos y priorizan estructura y estado. La [revisión de la teoría](REVISION-TEORIA.md) identifica como próximos ajustes la idempotencia, las métricas de ingesta y la reproducción completa del entorno.

La plataforma completa y el contrato común todavía no están implementados. La infraestructura y los datasets actuales son la base de trabajo: OTTO demuestra escala e ingesta; Ele.me aporta recomendaciones reales del sector; REES46 amplía las dimensiones temporales; Glovo aporta catálogo español; la tabla derivada sirve como estrés opcional. Sus resultados no acreditan todavía el rendimiento de la futura plataforma ficticia.

Próximas decisiones:

1. Cerrar qué fuentes entran en los 30 minutos y cuáles quedan como material complementario.
2. Alinear diapositivas y documentación con ese alcance; Ele.me está integrado, pero el guion principal sigue centrado en OTTO.
3. Ensayar una demo breve de ingesta, dashboard y comparación de consultas; CRUD en tabla de ensayo.
4. Probar la instalación desde cero en otro equipo, con una ruta de volumen reducido si hace falta.
5. Valorar después dos nodos o una comparación de claves de orden. Ya hay volumen suficiente para la clase; descargar más datos no es un requisito pendiente del proyecto.
6. Definir la plataforma ficticia, su contrato de eventos, la carga simulada y los adaptadores para fuentes futuras. Validar la infraestructura con datos semirreales y con los datasets públicos disponibles, manteniendo su procedencia.

Los datos son históricos. El replay demuestra ingesta actual de eventos antiguos; los botones de la página producen las únicas acciones nuevas de la demo. No hay conexión en vivo con Uber Eats, Glovo ni Ele.me.
