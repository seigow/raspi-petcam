# 🐾 petcam — Raspberry Pi Pet Camera

Raspberry Pi 4/5 + Pi Camera Module で動かすペットカメラ。Tailscale 経由でブラウザからライブ映像を視聴し、動きを検知するとクリップを自動録画します。

## 構成

- **ライブ映像**: MJPEG over HTTP（`<img>` タグで再生、低遅延）
- **動体検知**: OpenCV のフレーム差分
- **録画**: picamera2 の H.264 エンコーダ + ffmpeg で MP4 出力
- **保存管理**: 容量/日数上限を超えたクリップを自動削除
- **アクセス**: Tailscale VPN 経由（認証はそちらに委譲）

## 開発（WSL / Linux ホスト）

```bash
uv sync
uv run pytest -v
PETCAM_MOCK=1 uv run python -m petcam.main
# ブラウザで http://localhost:8000/ を開く（MockCamera の合成映像が流れる）
```

## Raspberry Pi デプロイ

```bash
# 1. picamera2 と ffmpeg は apt 経由で
sudo apt install -y python3-picamera2 ffmpeg

# 2. リポジトリを取得
git clone <this-repo> ~/raspi-petcam && cd ~/raspi-petcam

# 3. 設定ファイル
cp config.example.yaml config.yaml

# 4. 依存解決（picamera2 を参照するため system-site-packages を有効化）
uv sync --python-preference only-system
# もしくは .venv/pyvenv.cfg の include-system-site-packages を true に

# 5. 動作確認
uv run python -m petcam.main
# ブラウザで http://<tailscale-name>:8000/
```

## systemd で自動起動

```bash
sudo cp petcam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now petcam
journalctl -u petcam -f
```

## 設定（config.yaml）

| セクション | キー | デフォルト | 説明 |
|---|---|---|---|
| camera | width / height | 1280 / 720 | 解像度 |
| camera | framerate | 15 | fps |
| motion | threshold | 25 | 差分感度（小さいほど敏感） |
| motion | min_area | 5000 | 検知する最小輪郭面積（px²） |
| motion | cooldown_sec | 10 | 検知後の抑制時間 |
| recording | segment_sec | 60 | 1クリップの長さ |
| storage | max_total_gb | 10 | 保存領域の上限 |
| storage | retain_days | 7 | 保持日数 |
| server | host / port | 0.0.0.0 / 8000 | HTTP サーバ |

## ディレクトリ構成

```
.
├── src/petcam/          # アプリ本体
│   ├── app.py           # FastAPI アプリファクトリ
│   ├── camera.py        # CameraProtocol + MockCamera
│   ├── picam_camera.py  # picamera2 実装（Pi 専用）
│   ├── config.py        # YAML 設定ロード
│   ├── main.py          # エントリポイント
│   ├── motion.py        # フレーム差分による動体検知
│   ├── recorder.py      # 録画セッション状態機械
│   ├── storage.py       # クリップ一覧 + retention
│   └── streaming.py     # MJPEG multipart ジェネレータ
├── tests/               # pytest スイート
├── web/index.html       # SPA（ライブ映像 + 録画一覧）
├── config.example.yaml
├── petcam.service       # systemd unit
└── pyproject.toml
```
