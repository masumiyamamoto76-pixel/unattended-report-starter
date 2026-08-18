# -*- coding: utf-8 -*-
"""
watchdog.py — レポートが「今日も正しく作られたか」を外から検査する見張り役

本体（daily_report.py）とは別プロセス・別時刻で動かすのが最大のポイント。
本体がどんな死に方をしても（例外・ハング・タスク自体の消滅）、
見張りは無関係に起動して「成果物そのもの」を検査できる。

検査項目:
    1. レポートファイルが存在するか
    2. 更新時刻が24時間以内か（= 今朝ちゃんと生成されたか）
    3. ファイルサイズが下限以上か（= 中身が空っぽの殻ではないか）
    4. 必須セクションの文字列が含まれているか（= 途中で欠けていないか）

通知ポリシー:
    異常時のみWindowsトースト通知を出す。毎日の成功通知は3日で読まれなくなり、
    「通知が来ないこと」と「見張りが死んでいること」の区別がつかなくなるため。

終了コード: 0 = 全項目OK / 1 = 異常あり（通知済み）
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TARGET = BASE_DIR / "output" / "daily_report.html"
LOG_PATH = BASE_DIR / "logs" / "watchdog_log.txt"

MAX_AGE_HOURS = 24          # これより古いレポートは「今朝作られていない」とみなす
MIN_SIZE_BYTES = 2000       # 正常時の実測（約2.9KB）の3分の2を下限に設定
REQUIRED_SECTIONS = ["日別推移", "カテゴリ別集計", "検算"]


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    if sys.stdout is not None:  # pythonw.exe では None になる
        print(line)


def notify(title: str, body: str) -> None:
    """Windowsトースト通知（追加インストール不要・PowerShell標準機能のみ）。"""
    ps = f"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@'
<toast><visual><binding template="ToastGeneric"><text>{title}</text><text>{body}</text></binding></visual></toast>
'@)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$appid = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appid).Show($toast)
"""
    # 日本語を確実に通すため、UTF-8 BOM付きの一時.ps1に書いてから実行する
    with tempfile.NamedTemporaryFile(
        "w", suffix=".ps1", encoding="utf-8-sig", delete=False
    ) as f:
        f.write(ps)
        ps1_path = f.name
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
            capture_output=True, timeout=30,
        )
    finally:
        Path(ps1_path).unlink(missing_ok=True)


def main() -> None:
    log("---- watchdog 開始 ----")
    problems: list[str] = []

    if not TARGET.exists():
        problems.append(f"レポートが存在しません: {TARGET.name}")
    else:
        stat = TARGET.stat()

        age_h = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds() / 3600
        if age_h > MAX_AGE_HOURS:
            problems.append(f"レポートが古すぎます: 最終更新から {age_h:.1f} 時間（許容 {MAX_AGE_HOURS}h）")
        else:
            log(f"鮮度OK: 最終更新から {age_h:.1f} 時間")

        if stat.st_size < MIN_SIZE_BYTES:
            problems.append(f"ファイルサイズが小さすぎます: {stat.st_size} bytes（下限 {MIN_SIZE_BYTES}）")
        else:
            log(f"サイズOK: {stat.st_size:,} bytes")

        text = TARGET.read_text(encoding="utf-8", errors="replace")
        lacking = [s for s in REQUIRED_SECTIONS if s not in text]
        if lacking:
            problems.append(f"必須セクションが欠落: {lacking}")
        else:
            log(f"セクションOK: {REQUIRED_SECTIONS} すべて存在")

    if problems:
        for p in problems:
            log(f"異常: {p}")
        notify("日次レポート異常", f"{len(problems)}件の異常: " + " / ".join(problems)[:150])
        log(f"NG: 異常 {len(problems)} 件 → トースト通知を送信して終了(exit=1)")
        sys.exit(1)

    log("OK: 全項目正常（通知なし）")
    log("---- watchdog 正常終了 ----")


if __name__ == "__main__":
    main()
