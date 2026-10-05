# Estado del proyecto para el equipo

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

## Propuesta de alcance, pendiente de decisión del equipo

**Clickstream Lab: de millones de eventos a un dashboard con ClickHouse.**

OTTO como demostración principal de escala e ingesta; Ele.me como caso real de recomendaciones de comida a domicilio; REES46 como ampliación temporal; Glovo como contexto de catálogo español; tabla derivada como prueba de estrés opcional.

Próximas decisiones:

1. Cerrar qué fuentes entran en los 30 minutos y cuáles quedan como material complementario.
2. Alinear diapositivas y documentación con ese alcance; Ele.me está integrado, pero el guion principal sigue centrado en OTTO.
3. Ensayar una demo breve de ingesta, dashboard y comparación de consultas; CRUD en tabla de ensayo.
4. Probar la instalación desde cero en otro equipo, con una ruta de volumen reducido si hace falta.
5. Valorar después dos nodos o una comparación de claves de orden. Ya hay volumen suficiente para la clase; descargar más datos no es un requisito pendiente del proyecto.

Los datos son históricos. El replay demuestra ingesta actual de eventos antiguos; los botones de la página producen las únicas acciones nuevas de la demo. No hay conexión en vivo con Uber Eats, Glovo ni Ele.me.
