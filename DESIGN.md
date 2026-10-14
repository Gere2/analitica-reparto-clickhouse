# Delivery Atlas: diseño del panel operativo

Se extiende la familia visual existente del laboratorio: fondo gris claro, superficies blancas, acento verde y azul para datos. Se conserva el laboratorio anterior. Panel nuevo: `web/atlas-dashboard.html`.

## Escena y prioridad

Modo Operate: durante una clase, en un portátil o proyector con luz ambiente, Jere inicia la simulación, selecciona un repartidor y demuestra que su posición publicada cambia. Fondo claro y contraste legible; los estados no dependen solo del color.

## Estructura

La estructura combina operación e inventario: cabecera con control de simulación; contadores compactos; plano de coordenadas y detalle seleccionado; pedidos actuales; navegación; inventario y catálogo. Los datos históricos aparecen separados debajo, sin competir con el seguimiento. Rutas y posiciones están etiquetadas como sintéticas. Plano SVG geométrico, sin red viaria inventada ni dependencia de mapas externos.

Se consideraron siete estructuras (mapa completo, lista con mapa, carriles de estado, línea temporal, comparación histórica, operación con inventario, sesión individual). La selección de estructura indicó operación con inventario. El servicio de alternativas visuales no estaba disponible; se heredó el sistema existente. No se delegó el trabajo: el usuario pidió que Rayo trabajara solo.

## Sistema

- Tipografía de sistema para controles y datos, evitando descargas en una demo local.
- Verde oscuro `#24553d` para acción principal y selección; azul `#244e77` para GPS; rojo `#9f3131` para error; naranja oscuro para demoras.
- Texto principal `#18242d`, secundario `#52645b`, fondo `#f6f7f3`, líneas `#dfe4df`.
- Separar secciones con espacio y líneas; no anidar tarjetas. Botones y controles con foco visible, estados de carga y errores explícitos.
- Dos columnas para seguimiento en escritorio; una en móvil, con tabla horizontal desplazable y plano visible.
- Sin animación decorativa. El marcador cambia solo al recibir posiciones del servidor. Menos movimiento conserva el mismo comportamiento.
