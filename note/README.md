# Notemake

Note.com 記事のリライト・AI 臭除去・品質評価を行う CLI ツールキットです。すべての LLM 処理はローカルの [Ollama](https://ollama.ai/) で完結し、外部 API への送信は一切ありません。

## 特徴

- **AI 臭の検出と除去** — ChatGPT / Claude / Gemini / Grok が生成しがちな 40 以上の表現パターンを検出し、自分の文体にリライト
- **Note.com 記事の直接取得** — URL を渡すだけで記事本文を自動取得（API → HTML フォールバック）
- **ローカル LLM で完結** — Ollama を使い、データが外部に出ない安心設計
- **文体テンプレート** — 自分の書き癖を定義したテンプレートでリライトの方向性を制御
- **4 軸の品質評価** — 文章品質・構成・SEO・Note 最適化をスコアリング
- **コードブロック保護** — ソースコードや図表を LLM の改変から自動で保護
- **HEIC → PNG 一括変換** — iPhone 写真などの HEIC 画像をリサイズ付きで PNG に変換

## クイックスタート

### 必要環境

- Python 3.12+
- [Ollama](https://ollama.ai/)

### セットアップ

```bash
# 依存パッケージ
pip install -r requirements.txt

# Ollama モデルの取得と起動
ollama pull schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest
ollama serve
```

### 使い方

```bash
# Note.com 記事をリライト
python note_rewriter.py https://note.com/user/n/nXXXXXXX

# ローカルファイルをリライト
python note_rewriter.py article_draft.md

# AI 臭検出のみ（LLM 不要）
python note_rewriter.py article_draft.md --deai

# 品質評価レポートを生成
python note_rewriter.py article_draft.md --evaluate

# HEIC 画像を PNG に変換
python heic_to_png.py ~/Pictures -o output/ --width 1920
```

## ツール一覧

| ツール | 概要 |
|---|---|
| `note_rewriter.py` | 記事リライト・AI 臭除去・品質評価 |
| `heic_to_png.py` | HEIC/HEIF → PNG 一括変換 |

## ドキュメント

- **[利用ガイド（USAGE.md）](USAGE.md)** — 全コマンド・オプション・環境変数の詳細リファレンス
- **[詳細マニュアル](docs/note_rewriter_manual.md)** — note_rewriter の設計と使い方
- **[文体テンプレート例](docs/style_template.md)** — カスタムテンプレートの書き方

## プロジェクト構成

```
notemake/
├── note_rewriter.py        # 記事リライトツール
├── heic_to_png.py          # 画像変換ツール
├── requirements.txt        # 依存パッケージ
├── docs/                   # ドキュメント
├── note/                   # リライト済み記事
├── logs/                   # 実行ログ
└── png/                    # 変換済み画像
```

## 注意事項

- Note.com 記事の取得には非公式 API を使用しています。利用規約をご確認ください。
- Ollama のモデルは用途に合わせて変更可能です（`--model` オプション）。
