# 練馬区 施設予約システムの空き監視・通知バッチ

Playwright + Python で「多機能操作」から体育館（屋内スポーツ施設/目的:バレーボール）を検索し、
○（空き）を抽出して新規分だけメール通知します。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env  # SMTP設定を編集
```

## 実行

```bash
python main.py --show --slowmo 50
# あるいは
python main.py
```

### オプション
- `--show` : ブラウザを表示（デバッグ）
- `--slowmo MS` : 人間速度に近づける（ミリ秒）
- `--dry-run` : 送信/prev更新なし

## スケジュール（例：3時間おき）

```
0 */3 * * * /path/to/.venv/bin/python /path/to/main.py >> /path/to/log 2>&1
```

## 生成物

```
data/
  prev.json
  run-YYYYMMDD-HHMM/
    gin_menu.html
    multifunc-ready.html
    availability-form.html
    result-page-001.html
    ...
    log.txt
    log.jsonl
```
