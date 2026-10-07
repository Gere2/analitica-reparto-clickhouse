"""Transform the public TRD TSV files into typed ClickHouse TSVs.

All facts use the 2021-03-01..2021-03-21 training period. The published
click-session file also has a test week whose order details are withheld.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
END_DATE = "20210321"


def rows(name: str):
    with (RAW / name).open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream, delimiter="\t")


def clean_int(value: str) -> str:
    return value if value.isdigit() else "0"


def clean_float(value: str) -> str:
    try:
        return str(float(value))
    except (ValueError, TypeError):
        return r"\N"


def date(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()

    with (OUT / "restaurants.tsv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        for row in rows("pois.txt"):
            writer.writerow((row["wm_poi_id"], row["primary_first_tag_name"],
                             clean_int(row["aor_id"]), clean_float(row["poi_score"])))
            counts["restaurants"] += 1

    with (OUT / "foods.tsv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        for row in rows("spus.txt"):
            writer.writerow((row["wm_food_spu_id"], clean_float(row["price"]), row["category"]))
            counts["foods"] += 1

    with (OUT / "orders.tsv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        for row in rows("orders_train.txt"):
            writer.writerow((row["wm_order_id"], row["user_id"], row["wm_poi_id"],
                             clean_int(row["aor_id"]), row["order_price_interval"],
                             row["order_timestamp"], row["ord_period_name"], date(row["dt"])))
            counts["orders"] += 1

    with (OUT / "order_items.tsv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        for row in rows("orders_spu_train.txt"):
            writer.writerow((date(row["dt"]), row["wm_order_id"], row["wm_food_spu_id"]))
            counts["order_items"] += 1

    with (OUT / "clicks.tsv").open("w", encoding="utf-8", newline="") as click_file, \
         (OUT / "click_summary.tsv").open("w", encoding="utf-8", newline="") as summary_file:
        click_writer = csv.writer(click_file, delimiter="\t", lineterminator="\n")
        summary_writer = csv.writer(summary_file, delimiter="\t", lineterminator="\n")
        for row in rows("orders_poi_session.txt"):
            if row["dt"] > END_DATE:
                continue
            counts["click_sessions"] += 1
            raw_clicks = row["clicks"]
            if raw_clicks in ("", "NULL"):
                counts["sessions_without_recorded_clicks"] += 1
                continue
            restaurant_ids = raw_clicks.split("#")
            for position, restaurant_id in enumerate(restaurant_ids, start=1):
                click_writer.writerow((date(row["dt"]), row["wm_order_id"], position, restaurant_id))
                counts["clicks"] += 1
            summary_writer.writerow((date(row["dt"]), row["wm_order_id"], len(restaurant_ids),
                                     len(set(restaurant_ids)), restaurant_ids[-1]))
            counts["click_summaries"] += 1

    (OUT / "manifest.json").write_text(
        json.dumps({"source": "https://zenodo.org/records/8025855",
                    "period": "2021-03-01 to 2021-03-21",
                    "counts": dict(counts)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(dict(counts), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
