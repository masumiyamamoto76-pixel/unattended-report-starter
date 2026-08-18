# unattended-report-starter

**毎朝、無人でレポートが届く**——Windowsタスクスケジューラ＋Pythonで作る「壊れたら気づく」自動化の最小構成です。

- 依存ライブラリなし（**Python 3.10+ の標準ライブラリのみ。pip install 不要**）
- サーバー・クラウド不要。**手元のWindows PC 1台で完結**
- レポート本体と「見張り役」を分離し、壊れたらWindowsトースト通知で気づける
- データはすべて乱数生成のダミー。実在の企業・取引とは無関係

解説記事: https://zenn.dev/masumiyamamoto76-pixel/articles/unattended-daily-report-windows

## 構成（3ファイル）

| ファイル | 役割 |
|---|---|
| `make_dummy_orders.py` | 練習用のダミー受注CSVを生成（30日分・約500行・シード固定で再現可能） |
| `daily_report.py` | CSV読込 → 入力検証 → 集計 → **検算（内訳合計＝全体の突合）** → HTMLレポート生成。検算に失敗したらレポートを作らず非0終了 |
| `watchdog.py` | レポートの鮮度（24h以内）・サイズ下限・必須セクションを検査。**異常時のみ**トースト通知 |

## クイックスタート

```bat
python make_dummy_orders.py
python daily_report.py
python watchdog.py
```

3本目まで通れば `output\daily_report.html` が生成され、見張りが「全項目正常（通知なし）」と判定します。ログは `logs\` に残ります。

## タスクスケジューラへの登録（例）

`pythonw.exe` を直接指定するのがポイントです（黒いコンソール窓が出ない）。パスは `where pythonw` で確認してください。

```bat
schtasks /Create /TN "DailyReport" /TR "\"C:\Python312\pythonw.exe\" \"C:\tools\report\daily_report.py\"" /SC DAILY /ST 07:00
schtasks /Create /TN "ReportWatchdog" /TR "\"C:\Python312\pythonw.exe\" \"C:\tools\report\watchdog.py\"" /SC DAILY /ST 08:00
```

登録後は**成果物（HTML）の更新時刻**で動作を確認してください。タスクスケジューラの「前回の結果 0x0」は成功の証拠になりません（詳細は解説記事の「落とし穴」参照）。

## 終了コード

| コード | daily_report.py | watchdog.py |
|---|---|---|
| 0 | 正常 | 全項目OK |
| 1 | — | 異常あり（通知済み） |
| 2 | 入力ファイルなし・必須列の欠落 | — |
| 3 | 未知のカテゴリを検出 | — |
| 4 | 検算不一致 | — |

## ライセンス

MIT（`LICENSE` 参照）
