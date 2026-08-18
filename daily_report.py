# -*- coding: utf-8 -*-
"""
daily_report.py — 受注CSVを集計してHTMLレポートを生成する（検算付き）

処理の流れ:
    1. data/orders.csv を読み込む
    2. 入力検証（必須列がそろっているか／カテゴリに未知の値がないか）
    3. 集計（日別・カテゴリ別）
    4. 検算（内訳の合計 = 全体の合計 が一致するか）
    5. 検算を通過した場合のみ output/daily_report.html を生成

設計方針:
    - 検算に失敗したらレポートを「作らない」で非0終了する。
      間違ったレポートが定時に届き続けるのが最悪の事故だから。
    - タスクスケジューラの pythonw.exe から動かす前提。
      pythonw では標準出力が存在しない（sys.stdout が None）ため、
      記録はすべて logs/report_log.txt に書く。

終了コード:
    0 = 正常 / 2 = 入力ファイルなし・列不足 / 3 = 未知カテゴリ / 4 = 検算不一致
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "orders.csv"
OUT_PATH = BASE_DIR / "output" / "daily_report.html"
LOG_PATH = BASE_DIR / "logs" / "report_log.txt"

# ---- 集計の定義（ここが唯一の正。変更は必ずレビューを通す） ----
REQUIRED_COLUMNS = ["注文日", "注文ID", "カテゴリ", "数量", "金額"]
KNOWN_CATEGORIES = ["文具", "日用品", "飲料", "菓子", "衣料"]


def log(msg: str) -> None:
    """ログファイルに追記する。コンソールがあれば画面にも出す。"""
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    if sys.stdout is not None:  # pythonw.exe では None になる
        print(line)


def fail(code: int, msg: str) -> None:
    log(f"NG(exit={code}): {msg}")
    sys.exit(code)


def main() -> None:
    log("---- daily_report 開始 ----")

    # 1. 読み込み
    if not CSV_PATH.exists():
        fail(2, f"入力ファイルがありません: {CSV_PATH}")
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail(2, "入力CSVが空です")

    # 2-1. 必須列の検証 —— 列名の変更はここで止める
    missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
    if missing:
        fail(2, f"必須列が見つかりません: {missing} / 実際の列: {list(rows[0].keys())}")

    # 2-2. カテゴリの全数監査 —— 未知の値を黙って「その他」に流さない
    unknown = sorted({r["カテゴリ"] for r in rows} - set(KNOWN_CATEGORIES))
    if unknown:
        fail(3, f"未知のカテゴリがあります: {unknown}（分類表に追加するかデータを確認）")

    # 3. 集計
    daily_amount: dict[str, int] = defaultdict(int)
    daily_count: dict[str, int] = defaultdict(int)
    cat_amount: dict[str, int] = defaultdict(int)
    cat_count: dict[str, int] = defaultdict(int)
    total_amount = 0
    for r in rows:
        amount = int(r["金額"])
        daily_amount[r["注文日"]] += amount
        daily_count[r["注文日"]] += 1
        cat_amount[r["カテゴリ"]] += amount
        cat_count[r["カテゴリ"]] += 1
        total_amount += amount

    # 4. 検算 —— 内訳を全部足すと全体に一致するか（合わないなら集計ロジックが壊れている）
    checks = [
        ("カテゴリ別件数の合計 = 総行数", sum(cat_count.values()), len(rows)),
        ("カテゴリ別金額の合計 = 総金額", sum(cat_amount.values()), total_amount),
        ("日別金額の合計 = 総金額", sum(daily_amount.values()), total_amount),
    ]
    for name, left, right in checks:
        if left != right:
            fail(4, f"検算不一致: {name} → {left:,} != {right:,}")
        log(f"検算OK: {name} → {left:,}")

    # 5. HTML生成（検算をすべて通過した場合のみ）
    days = sorted(daily_amount)
    daily_tr = "\n".join(
        f"<tr><td>{escape(d)}</td><td>{daily_count[d]}</td>"
        f"<td>{daily_amount[d]:,} 円</td></tr>"
        for d in days
    )
    cat_tr = "\n".join(
        f"<tr><td>{escape(c)}</td><td>{cat_count[c]}</td>"
        f"<td>{cat_amount[c]:,} 円</td></tr>"
        for c in KNOWN_CATEGORIES
    )
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>日次レポート {days[-1]}</title>
<style>
 body {{ font-family: "Yu Gothic UI", sans-serif; margin: 2rem; }}
 table {{ border-collapse: collapse; margin-bottom: 2rem; }}
 th, td {{ border: 1px solid #999; padding: 4px 12px; text-align: right; }}
 th {{ background: #eee; }}
</style>
</head>
<body>
<h1>日次レポート（{days[0]} 〜 {days[-1]}）</h1>
<p>生成時刻: {datetime.now():%Y-%m-%d %H:%M:%S} ／
   対象 {len(rows):,} 件 ／ 総額 {total_amount:,} 円</p>

<h2>日別推移</h2>
<table><tr><th>日付</th><th>件数</th><th>金額</th></tr>
{daily_tr}
</table>

<h2>カテゴリ別集計</h2>
<table><tr><th>カテゴリ</th><th>件数</th><th>金額</th></tr>
{cat_tr}
</table>

<h2>検算</h2>
<p>内訳合計と全体の突合 3 項目をすべて通過しています。</p>
</body>
</html>
"""
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    log(f"OK: {OUT_PATH} を生成（{len(rows):,}件 / 総額 {total_amount:,}円）")
    log("---- daily_report 正常終了 ----")


if __name__ == "__main__":
    main()
