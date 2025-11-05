# ドラクエ風Web RPG (MVP)

レトロ配色・テキスト主体で構築した FastAPI + Vanilla JS の簡易RPGです。
街とフィールドを往復し、洞窟を抜けてボスを倒す流れを 30 分程度で遊べる規模にまとめています。

## ディレクトリ構成

```
app/
  backend/
    main.py              # FastAPI アプリ本体
    models/
      domain.py          # バトル計算ロジック
      game.py            # データ読み込みと生成処理
      schemas.py         # Pydantic スキーマ
    routes/
      battles.py         # 戦闘API
      players.py         # 新規ゲーム
      shops.py           # ショップ・宿
      world.py           # ロケーション・エンカウント
    data/                # モンスター/アイテム/マップ定義(JSON)
  frontend/
    index.html           # UIレイアウト
    styles.css           # レトロ風スタイル
    main.js              # ゲーム進行ロジック
    assets/              # 画像/音声(空のプレースホルダー)
```

## 起動手順

Python 3.11 以上を想定しています。Node.js は不要です。

```bash
cd app/backend
python -m venv .venv
source .venv/bin/activate  # Windows の場合は .venv\Scripts\activate
pip install fastapi uvicorn pydantic[dotenv] python-multipart
uvicorn main:app --reload
```

別ターミナルでフロントエンドを配信します。

```bash
cd app/frontend
python -m http.server 8000
```

ブラウザで <http://localhost:8000> を開くとゲームが始まります。

## ゲームの流れ

1. 最初の起動でプレイヤー名を入力 (未入力なら「ゆうしゃ」)。
2. はじまりの町 → 草むらでの戦闘をこなしつつ次の街へ。
3. 洞窟で戦力を整え、最奥のボスを撃破するとエンディングが表示されます。

- 戦闘は「たたかう / まほう / アイテム / にげる」の 4 コマンド制。
- まほうはヒール(回復)とファイア(攻撃)を実装。
- アイテムは薬草などを所持 (各9個まで)。
- 宿屋で HP/MP を全快可能。ゴールドが足りないと泊まれません。
- オートセーブ：街・戦闘終了時・マップ遷移時。手動セーブ/ロードボタンも利用できます。

## バトル仕様メモ

- 物理ダメージ: `max(1, (ATK - floor(DEF/2)) + rand(-1..+2))` をベースにクリティカルで追加上乗せ。
- クリティカル: 基礎5% (+/- AGI差 2%、2〜15%にクランプ)。DEF軽減を無視。
- 逃走: 雑魚戦のみ確率成功。ボスは常に失敗。
- レベルアップ: HP/MP/各能力がランダムで上昇。Lv99が上限。

## 将来拡張フック

- `index.html` 内の TODO コメントに BGM/SE および画像差し替えポイントを記載。
- `main.js` の末尾コメントに React/TypeScript 移行時の方針ヒントを残しています。

## テスト

`tests/test_battle.py` に最小限のユニットテストを用意しています。`pytest` で実行してください。

```bash
cd app/backend
pytest
```

