"""Dependency-free dashboard backend over the ClickHouse HTTP API."""

from __future__ import annotations

import base64
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
CH_URL = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8124/")
CH_USER = os.environ.get("CLICKHOUSE_USER", "demo")
CH_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "demo")
MIN_DATE = date(2021, 3, 1)
MAX_DATE = date(2021, 3, 21)
OTTO_CACHE: tuple[float, dict] = (0, {})
REES46_CACHE: dict[str, tuple[float, dict]] = {}
REES46_MONTHLY_CACHE: tuple[float, list[dict]] = (0, [])
SCALE_CACHE: tuple[float, dict] = (0, {})
ELEME_CACHE: dict[str, tuple[float, dict]] = {}


def query(sql: str) -> list[dict]:
    auth = base64.b64encode(f"{CH_USER}:{CH_PASSWORD}".encode()).decode()
    request = Request(CH_URL, data=(sql + " FORMAT JSON").encode(),
                      headers={"Authorization": f"Basic {auth}", "Content-Type": "text/plain"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)["data"]


def dashboard(start: date, end: date) -> dict:
    where = f"order_date BETWEEN '{start}' AND '{end}'"
    statements = {
        "orders": f"SELECT count() AS orders, uniqExact(user_id) AS users, uniqExact(restaurant_id) AS restaurants FROM delivery.orders WHERE {where}",
        "clicks": f"SELECT count() AS clicks FROM delivery.clicks WHERE {where}",
        "items": f"SELECT count() AS items FROM delivery.order_items WHERE {where}",
        "days": f"SELECT order_date AS day, count() AS orders FROM delivery.orders WHERE {where} GROUP BY day ORDER BY day",
        "click_days": f"SELECT order_date AS day, sum(clicks) AS clicks FROM delivery.daily_clicks WHERE {where} GROUP BY day ORDER BY day",
        "hours": f"SELECT toHour(ordered_at) AS hour, count() AS orders FROM delivery.orders WHERE {where} GROUP BY hour ORDER BY hour",
        "price_bands": f"SELECT price_band, count() AS orders FROM delivery.orders WHERE {where} GROUP BY price_band ORDER BY orders DESC",
        "depth": f"SELECT multiIf(click_count = 1, '1', click_count <= 3, '2–3', click_count <= 6, '4–6', click_count <= 10, '7–10', '11+') AS bucket, count() AS orders FROM delivery.click_summary WHERE {where} GROUP BY bucket",
        "last_click": f"SELECT count() AS sessions, countIf(o.restaurant_id = s.last_clicked_restaurant_id) AS same_restaurant FROM delivery.click_summary AS s INNER JOIN delivery.orders AS o ON s.order_id = o.order_id WHERE s.{where}",
        "top": f"SELECT t.restaurant_id AS restaurant_id, t.orders AS orders, ifNull(c.clicks, 0) AS clicks, r.category AS category, r.score AS score FROM (SELECT restaurant_id, count() AS orders FROM delivery.orders WHERE {where} GROUP BY restaurant_id ORDER BY orders DESC LIMIT 10) AS t ANY LEFT JOIN (SELECT restaurant_id, sum(clicks) AS clicks FROM delivery.daily_clicks WHERE {where} GROUP BY restaurant_id) AS c ON t.restaurant_id = c.restaurant_id ANY LEFT JOIN delivery.restaurants AS r ON t.restaurant_id = r.restaurant_id ORDER BY orders DESC",
    }

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = dict(zip(statements, pool.map(query, statements.values())))
    orders = results["orders"][0]
    clicks = results["clicks"][0]["clicks"]
    items = results["items"][0]["items"]
    daily = {row["day"]: {"day": row["day"], "orders": row["orders"], "clicks": 0}
             for row in results["days"]}
    for row in results["click_days"]:
        daily[row["day"]]["clicks"] = row["clicks"]
    depth = {row["bucket"]: row["orders"] for row in results["depth"]}
    depth["0"] = orders["orders"] - sum(depth.values())
    last = results["last_click"][0]
    return {
        "source": "Meituan TRD · 1–21 marzo 2021 · Pekín · datos anonimizados",
        "metrics": {"orders": orders["orders"], "users": orders["users"],
                    "restaurants": orders["restaurants"], "clicks": clicks,
                    "items": items, "clicks_per_order": round(clicks / orders["orders"], 2) if orders["orders"] else 0,
                    "last_click_match_pct": round(100 * last["same_restaurant"] / last["sessions"], 1) if last["sessions"] else 0},
        "daily": list(daily.values()),
        "hours": results["hours"],
        "price_bands": results["price_bands"],
        "depth": [{"bucket": label, "orders": depth.get(label, 0)} for label in ("0", "1", "2–3", "4–6", "7–10", "11+")],
        "top": results["top"],
    }


def glovo_dashboard(country: str, city: str) -> dict:
    if country != "ALL" and not re.fullmatch(r"[A-Z]{2}", country):
        raise ValueError("Código de país inválido.")
    if city and not re.fullmatch(r"[A-Z0-9_-]{2,10}", city):
        raise ValueError("Código de ciudad inválido.")
    if country == "ALL" and city:
        raise ValueError("Selecciona un país antes de filtrar una ciudad.")
    country_where = "1 = 1" if country == "ALL" else f"country_code = '{country}'"
    where = country_where + (f" AND city_code = '{city}'" if city else "")
    city_label = "concat(country_code, '/', city_code)" if country == "ALL" else "city_code"
    city_option_where = country_where if country != "ALL" else "0"
    statements = {
        "metrics": f"SELECT count() AS products, uniqExact(store_name) AS stores, uniqExact((country_code, city_code)) AS cities, uniqExact(collection_section) AS sections, countIf(has_description = 1) AS described FROM delivery.glovo_products WHERE {where}",
        "cities": f"SELECT {city_label} AS city, count() AS products, uniqExact(store_name) AS stores FROM delivery.glovo_products WHERE {where} GROUP BY city ORDER BY products DESC LIMIT 12",
        "sections": f"SELECT collection_section AS section, count() AS products FROM delivery.glovo_products WHERE {where} AND collection_section != '' GROUP BY section ORDER BY products DESC LIMIT 12",
        "stores": f"SELECT store_name AS store, count() AS products, uniqExact(city_code) AS cities, uniqExact(collection_section) AS sections FROM delivery.glovo_products WHERE {where} AND aux_store = 0 GROUP BY store ORDER BY products DESC LIMIT 12",
        "city_options": f"SELECT city_code AS city, count() AS products FROM delivery.glovo_products WHERE {city_option_where} GROUP BY city ORDER BY products DESC LIMIT 500",
        "countries": "SELECT country_code AS country, count() AS products FROM delivery.glovo_products GROUP BY country ORDER BY products DESC",
    }
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = dict(zip(statements, pool.map(query, statements.values())))
    metrics = results["metrics"][0]
    metrics["description_pct"] = round(100 * metrics["described"] / metrics["products"], 1) if metrics["products"] else 0
    return {
        "source": "Glovo FooDI-ML · catálogo histórico publicado en 2021 · productos con imagen",
        "selection": {"country": country, "city": city},
        "metrics": metrics,
        "cities": results["cities"],
        "sections": results["sections"],
        "stores": results["stores"],
        "city_options": results["city_options"],
        "countries": results["countries"],
    }


def otto_dashboard() -> dict:
    global OTTO_CACHE
    now = time.monotonic()
    if now - OTTO_CACHE[0] > 30:
        archive = query("SELECT count() AS events, countIf(event_type = 'clicks') AS clicks, "
                        "countIf(event_type = 'carts') AS carts, countIf(event_type = 'orders') AS orders, "
                        "uniqCombined64(session_id) AS sessions FROM delivery.otto_archive")[0]
        OTTO_CACHE = (now, archive)
    archive = OTTO_CACHE[1]
    statements = {
        "replay": "SELECT count() AS events, countIf(event_type = 'clicks') AS clicks, "
                  "countIf(event_type = 'carts') AS carts, countIf(event_type = 'orders') AS orders, "
                  "uniqCombined64(session_id) AS sessions FROM delivery.otto_replay "
                  "WHERE ingested_at >= now64(3) - INTERVAL 30 SECOND",
        "total_replayed": "SELECT count() AS events FROM delivery.otto_replay",
        "timeline": "SELECT toStartOfInterval(ingested_at, INTERVAL 2 SECOND) AS second, "
                    "countIf(event_type = 'clicks') AS clicks, countIf(event_type = 'carts') AS carts, "
                    "countIf(event_type = 'orders') AS orders FROM delivery.otto_replay "
                    "WHERE ingested_at >= now64(3) - INTERVAL 30 SECOND GROUP BY second ORDER BY second",
        "top": "SELECT article_id, count() AS events, countIf(event_type = 'clicks') AS clicks, "
               "countIf(event_type = 'orders') AS orders FROM delivery.otto_replay "
               "WHERE ingested_at >= now64(3) - INTERVAL 30 SECOND "
               "GROUP BY article_id ORDER BY events DESC LIMIT 8",
        "live": "SELECT count() AS clicks FROM delivery.live_clicks",
        "recent_live": "SELECT section, action, toString(clicked_at) AS clicked_at FROM delivery.live_clicks "
                       "ORDER BY clicked_at DESC LIMIT 8",
    }
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = dict(zip(statements, pool.map(query, statements.values())))
    return {
        "source": "OTTO · clics históricos reales reproducidos; acciones de esta página en vivo",
        "archive": archive,
        "replay_30s": results["replay"][0],
        "replayed_total": results["total_replayed"][0]["events"],
        "timeline": results["timeline"],
        "top": results["top"],
        "live_clicks": results["live"][0]["clicks"],
        "recent_live": results["recent_live"],
    }


def rees46_dashboard(month: str) -> dict:
    global REES46_MONTHLY_CACHE
    if month != "ALL" and month not in {"201910", "201911", "201912", "202001", "202002", "202003", "202004"}:
        raise ValueError("Mes REES46 inválido.")
    cached = REES46_CACHE.get(month)
    if cached and time.monotonic() - cached[0] < 60:
        return cached[1]
    where = "1 = 1" if month == "ALL" else f"toYYYYMM(event_date) = {month}"
    statements = {
        "metrics": f"SELECT count() AS events, countIf(event_type = 'view') AS views, "
                   f"countIf(event_type = 'cart') AS carts, "
                   f"countIf(event_type = 'remove_from_cart') AS removals, "
                   f"countIf(event_type = 'purchase') AS purchases, "
                   f"uniqCombined64(user_id) AS users_approx "
                   f"FROM delivery.rees46_events WHERE {where}",
        "categories": f"SELECT category_code AS category, countIf(event_type = 'view') AS views, "
                      f"countIf(event_type = 'cart') AS carts, "
                      f"countIf(event_type = 'purchase') AS purchases "
                      f"FROM delivery.rees46_events WHERE {where} AND category_code != '' "
                      f"GROUP BY category ORDER BY views DESC LIMIT 12",
        "brands": f"SELECT brand, count() AS events, countIf(event_type = 'purchase') AS purchases "
                  f"FROM delivery.rees46_events WHERE {where} AND brand != '' "
                  f"GROUP BY brand ORDER BY events DESC LIMIT 10",
    }
    monthly_sql = ("SELECT toYYYYMM(event_date) AS month, event_type, count() AS events "
                   "FROM delivery.rees46_events GROUP BY month, event_type ORDER BY month, event_type")
    if time.monotonic() - REES46_MONTHLY_CACHE[0] >= 600:
        statements["monthly"] = monthly_sql
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(zip(statements, pool.map(query, statements.values())))
    if "monthly" in results:
        REES46_MONTHLY_CACHE = (time.monotonic(), results["monthly"])
    else:
        results["monthly"] = REES46_MONTHLY_CACHE[1]
    output = {"source": "REES46 · marketplace · oct 2019–abr 2020 · eventos reales anonimizados",
              "month": month, "metrics": results["metrics"][0],
              "monthly": results["monthly"], "categories": results["categories"], "brands": results["brands"]}
    REES46_CACHE[month] = (time.monotonic(), output)
    return output


def eleme_dashboard(day: str) -> dict:
    if day not in {"ALL", "1", "2", "3", "4", "5", "6", "7", "8"}:
        raise ValueError("Día relativo Ele.me inválido.")
    cached = ELEME_CACHE.get(day)
    if cached and time.monotonic() - cached[0] < 10:
        return cached[1]
    where = "1=1" if day == "ALL" else f"sample_day = {day}"
    statements = {
        "metrics": f"SELECT count() AS samples, sum(clicked) AS clicks, "
                   f"uniqCombined64(user_id) AS users_approx, uniqCombined64(shop_id) AS shops_approx "
                   f"FROM delivery.eleme_samples WHERE {where}",
        "days": "SELECT sample_day AS day, count() AS samples, sum(clicked) AS clicks "
                "FROM delivery.eleme_samples GROUP BY day ORDER BY day",
        "hours": f"SELECT request_hour AS hour, count() AS samples, sum(clicked) AS clicks "
                 f"FROM delivery.eleme_samples WHERE {where} GROUP BY hour ORDER BY hour",
        "cities": f"SELECT city_id AS city, count() AS samples, sum(clicked) AS clicks "
                  f"FROM delivery.eleme_samples WHERE {where} GROUP BY city ORDER BY samples DESC LIMIT 12",
        "meals": f"SELECT meal_period AS period, count() AS samples, sum(clicked) AS clicks "
                 f"FROM delivery.eleme_samples WHERE {where} GROUP BY period ORDER BY samples DESC",
        "files": "SELECT source_file AS file, sample_day AS day, count() AS samples "
                 "FROM delivery.eleme_samples GROUP BY file, day ORDER BY day, file",
        "staging": "SELECT sum(rows) AS rows FROM system.parts WHERE database='delivery' "
                   "AND table='eleme_staging' AND active",
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(zip(statements, pool.map(query, statements.values())))
    metrics = results["metrics"][0]
    metrics["positive_pct"] = round(100 * int(metrics["clicks"]) / int(metrics["samples"]), 2) if int(metrics["samples"]) else None
    output = {"source": "Ele.me · recomendación de comida a domicilio · China · histórico anonimizado",
              "source_url": "https://tianchi.aliyun.com/dataset/131047", "day": day,
              "declared_samples": 146_000_000, "metrics": metrics,
              "days": results["days"], "hours": results["hours"], "cities": results["cities"],
              "meals": results["meals"],
              "files": results["files"],
              "staging_rows": int(results["staging"][0]["rows"]),
              "loaded_total": sum(int(row["samples"]) for row in results["files"]),
              "empty": not results["files"]}
    ELEME_CACHE[day] = (time.monotonic(), output)
    return output


def scale_dashboard() -> dict:
    global SCALE_CACHE
    if time.monotonic() - SCALE_CACHE[0] < 10:
        return SCALE_CACHE[1]
    parts = query("SELECT table, sum(rows) AS rows, sum(bytes_on_disk) AS bytes_on_disk "
                  "FROM system.parts WHERE database = 'delivery' AND active "
                  "AND table IN ('otto_archive','otto_daily_rollup','rees46_events',"
                  "'otto_scale_benchmark','eleme_samples') GROUP BY table ORDER BY table")
    tables = {row["table"]: row for row in parts}
    report_path = ROOT / "data" / "query-benchmark.json"
    benchmark = json.loads(report_path.read_text()) if report_path.is_file() else None
    output = {"tables": tables, "real_events": sum(int(tables.get(name, {}).get("rows", 0))
                                                    for name in ("otto_archive", "rees46_events")),
              "derived_rows": int(tables.get("otto_scale_benchmark", {}).get("rows", 0)),
              "benchmark": benchmark}
    SCALE_CACHE = (time.monotonic(), output)
    return output


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        # The live OTTO panel polls every two seconds; keep the demo terminal readable.
        if self.path.startswith("/api/otto") and len(args) > 1 and str(args[1]) == "200":
            return
        super().log_message(format, *args)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/live-click":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024:
                raise ValueError("Cuerpo inválido")
            event = json.loads(self.rfile.read(size))
            section = event.get("section")
            action = event.get("action")
            if section not in {"inicio", "productos", "cesta"} or action not in {"abrir", "explorar", "anadir"}:
                raise ValueError("Acción inválida")
            auth = base64.b64encode(f"{CH_USER}:{CH_PASSWORD}".encode()).decode()
            request = Request(CH_URL, data=("INSERT INTO delivery.live_clicks (section, action) FORMAT JSONEachRow\n" +
                                            json.dumps({"section": section, "action": action}) + "\n").encode(),
                              headers={"Authorization": f"Basic {auth}", "Content-Type": "text/plain"})
            with urlopen(request, timeout=10):
                pass
            self.respond(b'{"ok":true}', "application/json")
        except (ValueError, OSError, KeyError) as error:
            self.respond(json.dumps({"error": str(error)}).encode(), "application/json", 400)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/eleme":
            try:
                day = parse_qs(parsed.query).get("day", ["ALL"])[0].upper()
                self.respond(json.dumps(eleme_dashboard(day), ensure_ascii=False).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.respond(json.dumps({"error": str(error)}, ensure_ascii=False).encode(), "application/json", 503)
            return
        if parsed.path == "/api/scale":
            try:
                self.respond(json.dumps(scale_dashboard(), ensure_ascii=False).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.respond(json.dumps({"error": str(error)}, ensure_ascii=False).encode(), "application/json", 503)
            return
        if parsed.path == "/api/rees46":
            try:
                month = parse_qs(parsed.query).get("month", ["ALL"])[0].upper()
                self.respond(json.dumps(rees46_dashboard(month), ensure_ascii=False).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.respond(json.dumps({"error": str(error)}, ensure_ascii=False).encode(), "application/json", 503)
            return
        if parsed.path == "/api/otto":
            try:
                self.respond(json.dumps(otto_dashboard(), ensure_ascii=False).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.respond(json.dumps({"error": str(error)}, ensure_ascii=False).encode(), "application/json", 503)
            return
        if parsed.path == "/api/dashboard":
            try:
                params = parse_qs(parsed.query)
                start = date.fromisoformat(params.get("from", [str(MIN_DATE)])[0])
                end = date.fromisoformat(params.get("to", [str(MAX_DATE)])[0])
                if not (MIN_DATE <= start <= end <= MAX_DATE):
                    raise ValueError("Las fechas deben estar entre el 1 y el 21 de marzo de 2021.")
                self.respond(json.dumps(dashboard(start, end), ensure_ascii=False).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.respond(json.dumps({"error": str(error)}, ensure_ascii=False).encode(), "application/json", 400)
            return
        if parsed.path == "/api/glovo":
            try:
                params = parse_qs(parsed.query)
                country = params.get("country", ["ES"])[0].upper()
                city = params.get("city", [""])[0].upper()
                self.respond(json.dumps(glovo_dashboard(country, city), ensure_ascii=False).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.respond(json.dumps({"error": str(error)}, ensure_ascii=False).encode(), "application/json", 400)
            return
        path = "/index.html" if parsed.path == "/" else parsed.path
        target = (WEB / path.lstrip("/")).resolve()
        if not target.is_relative_to(WEB) or not target.is_file():
            self.send_error(404)
            return
        mime = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}.get(target.suffix, "application/octet-stream")
        self.respond(target.read_bytes(), mime)

    def respond(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Dashboard disponible en http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
