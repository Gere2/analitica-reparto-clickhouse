"""Miniapp de reparto: sirve la página y recibe los clics para guardarlos en ClickHouse.

Deliberadamente un monolito (una sola app Flask): separar un servicio de eventos
solo añadiría latencia de red en un proyecto de este tamaño.
"""
import os
import random
import time
import uuid
from collections import deque
from datetime import datetime
from decimal import Decimal

import clickhouse_connect
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

COLUMNAS = [
    "event_id", "ts", "session_id", "user_id", "origen", "seccion", "accion",
    "restaurante_id", "plato_id", "promo_id", "busqueda", "filtros", "importe",
    "dispositivo", "distrito",
]
SECCIONES = {"inicio", "busqueda", "filtros", "restaurante", "menu", "carrito", "pago", "pedido"}

# Si ClickHouse no responde, los eventos esperan aquí y la navegación no se rompe.
pendientes: deque = deque(maxlen=10_000)
_cliente = None


def cliente():
    global _cliente
    if _cliente is None:
        _cliente = clickhouse_connect.get_client(
            host=os.environ["CLICKHOUSE_HOST"],
            port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
            username=os.environ["CLICKHOUSE_USER"],
            password=os.environ["CLICKHOUSE_PASSWORD"],
            database=os.environ.get("CLICKHOUSE_DB", "reparto"),
            connect_timeout=2,        # timeout: una dependencia lenta no bloquea la app
            send_receive_timeout=5,
            # ClickHouse agrupa las inserciones pequeñas (un clic = una fila)
            settings={"async_insert": 1, "wait_for_async_insert": 1},
        )
    return _cliente


def insertar(filas, intentos=3):
    """Reintenta con backoff exponencial y jitter. Es seguro reintentar porque
    event_id y ts vienen del cliente: un duplicado lo elimina ReplacingMergeTree."""
    for intento in range(intentos):
        try:
            cliente().insert("eventos_app", filas, column_names=COLUMNAS)
            return True
        except Exception as error:  # noqa: BLE001 (cualquier fallo de red o del servidor)
            app.logger.warning("insert fallido (intento %s): %s", intento + 1, error)
            time.sleep((2 ** intento) * 0.2 + random.uniform(0, 0.2))
    return False


def a_fila(e: dict) -> list:
    return [
        uuid.UUID(e["event_id"]),
        datetime.fromisoformat(e["ts"].replace("Z", "+00:00")),
        uuid.UUID(e["session_id"]),
        int(e.get("user_id", 0)),
        e.get("origen", "app_real"),
        e["seccion"],
        e.get("accion", "ver"),
        int(e.get("restaurante_id", 0)),
        int(e.get("plato_id", 0)),
        int(e.get("promo_id", 0)),
        e.get("busqueda", ""),
        list(e.get("filtros", [])),
        Decimal(str(e.get("importe", 0))),
        e.get("dispositivo", "desconocido"),
        e.get("distrito", ""),
    ]


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/health")
def health():
    return {"ok": True, "pendientes": len(pendientes)}


@app.post("/evento")
def evento():
    e = request.get_json(silent=True) or {}
    if e.get("seccion") not in SECCIONES or "event_id" not in e or "session_id" not in e:
        return jsonify(error="faltan event_id, session_id o una seccion válida"), 400
    try:
        fila = a_fila(e)
    except (KeyError, ValueError) as error:
        return jsonify(error=str(error)), 400

    lote = list(pendientes) + [fila]
    if insertar(lote):
        pendientes.clear()
        return jsonify(ok=True), 201
    pendientes.append(fila)
    return jsonify(ok=False, encolado=True), 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
