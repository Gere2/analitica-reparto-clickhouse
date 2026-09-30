"""Genera sesiones SIMULADAS (origen = 'simulado') para probar ClickHouse a escala.

Nunca se mezclan con los clics reales: todas las consultas pueden filtrar por origen.

Uso (con docker compose levantado y las variables de .env exportadas):
    pip install clickhouse-connect
    set -a; source .env; set +a
    python scripts/simular_sesiones.py --sesiones 200000
"""
import argparse
import os
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import clickhouse_connect

COLUMNAS = [
    "event_id", "ts", "session_id", "user_id", "origen", "seccion", "accion",
    "restaurante_id", "plato_id", "promo_id", "busqueda", "filtros", "importe",
    "dispositivo", "distrito",
]
# Probabilidad de pasar al paso siguiente. Son SUPUESTOS del simulador, no datos
# reales: sirven para que el embudo tenga forma, no para sacar conclusiones.
PASOS = [
    ("inicio", 1.00), ("busqueda", 0.70), ("filtros", 0.45), ("restaurante", 0.80),
    ("menu", 0.85), ("carrito", 0.40), ("pago", 0.60), ("pedido", 0.90),
]
BUSQUEDAS = ["pizza", "sushi", "hamburguesa", "kebab", "ensalada", "tacos", "poke"]
DISTRITOS = ["Centro", "Salamanca", "Chamberí", "Retiro", "Tetuán", "Latina", "Moncloa-Aravaca"]
MADRID = ZoneInfo("Europe/Madrid")


def sesion(inicio: datetime) -> list:
    sid, uid = uuid.uuid4(), random.randint(1, 50_000)
    dispositivo = random.choices(["movil", "escritorio", "tablet"], [0.75, 0.2, 0.05])[0]
    distrito = random.choice(DISTRITOS)
    busqueda = random.choice(BUSQUEDAS)
    restaurante = random.randint(1, 500)
    importe = Decimal(random.randint(800, 4000)) / 100
    ts, filas = inicio, []
    for seccion, p in PASOS:
        if random.random() > p:
            break
        ts += timedelta(seconds=random.randint(3, 90))
        filas.append([
            uuid.uuid4(), ts, sid, uid, "simulado", seccion,
            {"carrito": "anadir", "pago": "pagar"}.get(seccion, "ver"),
            restaurante if seccion not in ("inicio", "busqueda", "filtros") else 0,
            random.randint(1, 30) if seccion == "carrito" else 0,
            0,
            busqueda if seccion == "busqueda" else "",
            ["envio_gratis"] if seccion == "filtros" else [],
            importe if seccion in ("carrito", "pago", "pedido") else Decimal(0),
            dispositivo, distrito,
        ])
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sesiones", type=int, default=100_000)
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--lote", type=int, default=50_000)
    args = ap.parse_args()

    ch = clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
        username=os.environ["CLICKHOUSE_ADMIN_USER"],
        password=os.environ["CLICKHOUSE_ADMIN_PASSWORD"],
        database=os.environ.get("CLICKHOUSE_DB", "reparto"),
    )
    ahora = datetime.now(MADRID)
    lote, total = [], 0
    for _ in range(args.sesiones):
        inicio = ahora - timedelta(days=random.uniform(0, args.dias))
        lote.extend(sesion(inicio))
        if len(lote) >= args.lote:          # lotes grandes: ClickHouse rinde mal con INSERT pequeños
            ch.insert("eventos_app", lote, column_names=COLUMNAS)
            total += len(lote)
            lote = []
    if lote:
        ch.insert("eventos_app", lote, column_names=COLUMNAS)
        total += len(lote)
    print(f"{args.sesiones} sesiones simuladas, {total} eventos insertados")


if __name__ == "__main__":
    main()
