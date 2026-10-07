# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Jere, Anuar y Echenique preparan un proyecto BD2; el profesor y otros estudiantes deben entenderlo y reproducir la demo. La implementación la continúa Rayo con Jere hasta que el equipo se incorpore.

## Product Purpose

Delivery Atlas demuestra infraestructura analítica de una plataforma ficticia de comida a domicilio. Debe representar eventos masivos, explicar el esquema y enseñar ingesta y seguimiento durante la demo.

## Operating Context

Demo local en navegador y Docker Compose, integración Python/ClickHouse. El usuario confirmó Madrid y repartidores simulados con posiciones cada dos segundos el 7/10/2026. Conservamos los datasets públicos y los paneles históricos.

## Capabilities and Constraints

Un nodo ClickHouse 25.8, API Python de biblioteca estándar y cola SQLite persistente de transporte. El histórico y los eventos propios conservan procedencia. No hay GPS observado ni datos operativos en vivo de Uber Eats/Glovo. Las posiciones y pedidos son simulaciones; las rutas no siguen una red viaria real. No hay pagos ni reparto real.

## Brand Commitments

Nombre Delivery Atlas. Explicaciones en español; exposición de clase en inglés cuando se solicite. Respetar la apariencia existente de los paneles del laboratorio al extender la web.

## Evidence on Hand

docs/auditoria-esquemas.json contiene tablas y columnas inspeccionadas. docs/RESULTADOS-ATLAS.md recoge un millón de eventos simulados y pruebas de reintentos/recuperación. Las mediciones de OTTO no se atribuyen a Atlas. Glovo aporta catálogo; Ele.me muestras; Meituan pedidos y secuencias históricas. Ninguna de esas fuentes contiene nuestra flota GPS.

## Product Principles

- Separar histórico, simulación y acciones manuales.
- Leer del almacén real: no mover repartidores en el navegador sin ingesta.
- Mostrar retraso, errores y antigüedad de posición.
- Hacer reproducible la ruta pequeña sin descargar los datasets masivos.
