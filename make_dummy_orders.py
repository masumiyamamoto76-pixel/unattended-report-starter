# -*- coding: utf-8 -*-
"""
make_dummy_orders.py — 練習用のダミー受注CSVを生成する

実在のデータは一切使わず、乱数で架空の受注データを作る。
実行するたびに「今日から過去30日分」を生成するので、
daily_report.py / watchdog.py の鮮度チェックの練習にそのまま使える。

使い方:
    python make_dummy_orders.py
出力:
    data/orders.csv （約500行・UTF-8 BOM付き。Excelでそのまま開ける）
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "data" / "orders.csv"

# 乱数シードを固定 → 誰が実行しても同じ行数・同じ内訳になる（再現性）
random.seed(42)

DAYS = 30  # 今日を含む過去30日分

# すべて架空のマスタ（実在の商品・取引先とは無関係）
CATEGORIES = {
    "文具": (300, 1500),  # (単価の下限, 上限)
    "日用品": (200, 2500),
    "飲料": (100, 800),
    "菓子": (150, 1200),
    "衣料": (1000, 6000),
}
CHANNELS = ["店頭", "電話", "Web"]


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    today = date.today()
    rows = []
    order_no = 1
    for i in range(DAYS - 1, -1, -1):  # 古い日付から順に
        d = today - timedelta(days=i)
        # 1日あたり10〜25件（乱数）
        for _ in range(random.randint(10, 25)):
            cat = random.choice(list(CATEGORIES))
            lo, hi = CATEGORIES[cat]
            unit = random.randrange(lo, hi + 1, 10)  # 10円刻み
            qty = random.randint(1, 5)
            rows.append(
                {
                    "注文日": d.isoformat(),
                    "注文ID": f"ORD-{d:%y%m%d}-{order_no:04d}",
                    "経路": random.choice(CHANNELS),
                    "カテゴリ": cat,
                    "数量": qty,
                    "単価": unit,
                    "金額": unit * qty,
                }
            )
            order_no += 1

    # utf-8-sig（BOM付き）: 日本語CSVをExcelで文字化けさせないための定番
    with OUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK: {OUT_PATH} に {len(rows)} 行を書き出しました（{rows[0]['注文日']}〜{rows[-1]['注文日']}）")


if __name__ == "__main__":
    main()
