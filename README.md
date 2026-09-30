# Analítica de clics y abandono de pedidos en una plataforma de reparto de comida

Proyecto de Bases de Datos con **ClickHouse**.

**Pregunta:** en una app tipo Uber Eats, ¿en qué paso se pierden los pedidos?
(inicio → búsqueda → filtros → restaurante → menú → carrito → pago)

## Qué hay

```
miniapp (Flask) ──POST /evento──▶ ClickHouse ◀── Grafana (embudo y gráficos)
                                      ▲
                     carga: CSV de MT-LIFT (Meituan) y censo de Madrid
```

| Carpeta | Contenido |
|---|---|
| `docker-compose.yml` | App + ClickHouse + Grafana |
| `app/` | Miniapp Flask: página de prueba y endpoint `/evento` |
| `clickhouse/init/` | Tablas, vista materializada y usuarios (se ejecutan al primer arranque) |
| `grafana/` | Conexión de Grafana con ClickHouse |
| `scripts/` | Simulador de sesiones y consultas de la demo |
| `docs/DATOS.md` | De dónde salen los datos y qué podemos afirmar con cada uno |
| `docs/TEORIA-APLICADA.md` | Cada decisión técnica con su concepto del curso |

## Arrancar

```bash
cp .env.example .env        # y cambiar las contraseñas
docker compose up -d
docker compose ps           # esperar a que clickhouse esté "healthy"
```

- App: http://localhost:8080
- Grafana: http://localhost:3000 (usuario `admin`, contraseña `GRAFANA_PASSWORD` de `.env`)
- ClickHouse: `docker compose exec clickhouse clickhouse client --user admin --password`

Generar volumen de prueba (marcado como simulado):

```bash
pip install clickhouse-connect
set -a; source .env; set +a
python scripts/simular_sesiones.py --sesiones 200000
```

Si se cambian las tablas de `clickhouse/init/`, hay que borrar el volumen para que se vuelvan a
ejecutar: `docker compose down -v && docker compose up -d` (**borra los datos**).

## Reparto de tareas (propuesta)

- [ ] 🐳 Docker + ClickHouse: cargar MT-LIFT y el censo (`docs/DATOS.md`, pendientes)
- [ ] 📱 App: restaurantes reales del censo y recorrido completo
- [ ] 📊 Grafana: panel del embudo, búsquedas y promociones
- [ ] 📝 Memoria y presentación (`docs/TEORIA-APLICADA.md` como guion)

## Demo

1. `SELECT count()` sobre los 5,5 M de registros reales de Meituan.
2. Tasa de clic y de conversión por promoción.
3. Recorrido en directo en la app: buscar «pizza», filtrar, abrir un restaurante, añadir y abandonar.
4. Ver ese clic en ClickHouse y en el panel de Grafana.
5. Embudo por sección: dónde se pierden más sesiones.
6. Insertar, consultar, corregir y borrar un evento (`scripts/consultas_demo.sql`, consulta 6).
7. Vista materializada: el panel consulta agregados, no millones de filas.
