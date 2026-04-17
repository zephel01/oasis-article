# Notemake 利用ガイド

Note.com 記事のリライトと AI 臭除去、および画像変換のための CLI ツールキットです。

## 目次

- [セットアップ](#セットアップ)
- [note\_rewriter.py — 記事リライトツール](#note_rewriterpy--記事リライトツール)
- [heic\_to\_png.py — 画像変換ツール](#heic_to_pngpy--画像変換ツール)
- [プロジェクト構成](#プロジェクト構成)

---

## セットアップ

### 必要環境

- Python 3.12 以上
- [Ollama](https://ollama.ai/)（ローカル LLM ランタイム）

### インストール

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# HEIC 変換を使う場合（任意）
pip install pillow pillow-heif
```

### Ollama の準備

```bash
# macOS
brew install ollama

# モデルの取得
ollama pull schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest

# サーバー起動
ollama serve
```

---

## note\_rewriter.py — 記事リライトツール

Note.com 記事や Markdown ファイルを、ローカル LLM で自分の文体にリライトするツールです。AI 臭（ChatGPT・Claude・Gemini・Grok の癖）を検出・除去できます。

### 基本構文

```bash
python note_rewriter.py <source> [options]
```

`<source>` には **Note.com の URL** または **ローカルファイルパス**（.md / .txt）を指定します。

### コマンド例

```bash
# Note.com 記事をリライト
python note_rewriter.py https://note.com/user/n/nXXXXXXX

# ローカル Markdown をリライト
python note_rewriter.py article_draft.md

# AI 臭検出のみ（LLM 不要、パターンマッチ）
python note_rewriter.py article_draft.md --deai

# カスタムテンプレートでリライト
python note_rewriter.py https://note.com/user/n/nXXX --template my_style.md

# 品質評価レポートを生成
python note_rewriter.py https://note.com/user/n/nXXX --evaluate

# 評価のみ（リライトなし）
python note_rewriter.py article_draft.md --evaluate-only

# 複数形式で出力
python note_rewriter.py article_draft.md --format md,txt,html

# プレビュー（LLM 呼び出しなし）
python note_rewriter.py article_draft.md --dry-run
```

### オプション一覧

| オプション | 説明 | デフォルト |
|---|---|---|
| `--template` | 文体テンプレートファイル | 自動検出 |
| `--model` | Ollama モデル名 | `schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest` |
| `--output` | 出力ファイルのベースパス | タイトルから自動生成 |
| `--format` | 出力形式（`md` / `txt` / `html`、カンマ区切りで複数可） | `md` |
| `--host` | Ollama サーバー URL | `http://localhost:11434` |
| `--log-dir` | ログ保存先ディレクトリ | `logs` |
| `--chunk-size` | LLM 1 回あたりの最大文字数 | モデルから自動推定 |
| `--dry-run` | 原文を表示するのみ（LLM 呼び出しなし） | — |
| `--no-title` | タイトルのリライトをスキップ | — |
| `--evaluate` | リライト後に品質評価レポートを生成 | — |
| `--evaluate-only` | リライトせず評価のみ実行 | — |
| `--deai` | AI 臭パターン検出モード（LLM 不要） | — |

### 環境変数

設定を環境変数で固定できます。

| 変数名 | 対応オプション |
|---|---|
| `NOTE_REWRITER_MODEL` | `--model` |
| `NOTE_REWRITER_HOST` | `--host` |
| `NOTE_REWRITER_LOG_DIR` | `--log-dir` |
| `NOTE_REWRITER_FORMAT` | `--format` |
| `NOTE_REWRITER_TEMPERATURE` | LLM の温度パラメータ（デフォルト: 0.2） |

### 文体テンプレート

`--template` を省略した場合、カレントディレクトリから以下の順で自動検出します。

1. `style_template.md`
2. `my_style.md`
3. `template.md`

テンプレートの書き方は `docs/style_template.md` を参照してください。

### 品質評価（`--evaluate`）

4 軸でスコアリングした評価レポートが生成されます。

- **文章品質** — 表現の自然さ・読みやすさ
- **構成・フロー** — 論理展開と段落構成
- **SEO・発見性** — 検索への最適化度
- **Note 最適化** — Note.com プラットフォームへの適合度

### AI 臭検出（`--deai`）

LLM を使わず、40 以上のパターンで AI 生成らしい表現を検出します。検出対象の例は以下の通りです。

- ChatGPT 系: 「素晴らしい質問ですね」「以下にまとめました」
- Claude 系: 「ですね」の多用、過度な婉曲表現
- Gemini 系: 箇条書きの多用、過度な太字
- Grok 系: 「ぶっちゃけ」「まぁ」などの口語フィラー

---

## heic\_to\_png.py — 画像変換ツール

HEIC / HEIF 画像を PNG に一括変換するユーティリティです。

### 基本構文

```bash
python heic_to_png.py [paths] [options]
```

### コマンド例

```bash
# カレントディレクトリの HEIC を変換
python heic_to_png.py

# 指定ディレクトリから変換
python heic_to_png.py ~/Pictures

# 出力先とリサイズを指定
python heic_to_png.py ~/Pictures -o output/ --width 1920

# 50% に縮小
python heic_to_png.py ~/Pictures --scale 50

# ファイルサイズ上限を指定（KB）
python heic_to_png.py ~/Pictures --max-filesize 500

# サブディレクトリも再帰的に検索
python heic_to_png.py -r ~/Pictures

# プレビュー（変換なし）
python heic_to_png.py ~/Pictures --dry-run
```

### オプション一覧

| オプション | 説明 |
|---|---|
| `-o OUTPUT_DIR` | 出力先ディレクトリ |
| `--width N` | 長辺を N px にリサイズ（アスペクト比維持） |
| `--scale N` | 元サイズの N% に縮小 |
| `--max-filesize KB` | ファイルサイズ上限（超過時は自動縮小） |
| `-r` / `--recursive` | サブディレクトリを再帰検索 |
| `--dry-run` | 変換せずプレビューのみ |

---

## プロジェクト構成

```
notemake/
├── note_rewriter.py        # 記事リライトツール（メイン）
├── heic_to_png.py          # HEIC→PNG 変換ツール
├── main.py                 # エントリポイント
├── requirements.txt        # Python 依存パッケージ
├── pyproject.toml          # プロジェクト設定
│
├── docs/                   # ドキュメント
│   ├── note_rewriter_manual.md   # 詳細マニュアル
│   ├── style_template.md         # 文体テンプレートのサンプル
│   ├── note-template-tech.md     # 技術記事テンプレート
│   └── note-template-general.md  # 一般記事テンプレート
│
├── note/                   # リライト済み記事の出力先
├── logs/                   # 実行ログ
├── png/                    # 変換済み PNG 画像
└── output/                 # その他の出力ファイル
```

---

## ライセンス・注意事項

- すべての LLM 処理はローカルの Ollama で実行されます。外部 API への送信はありません。
- Note.com 記事の取得には非公式 API を使用しています。利用規約を確認のうえご利用ください。
