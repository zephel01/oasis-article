# tools/ — ローカル LLM 執筆支援ツール群

[Ollama](https://ollama.ai/) でローカル LLM を動かし、note / Qiita / Zenn どのプラットフォームにも使える形で「AI 臭除去 + リライト」を行うための CLI ツール群です。外部 API へのデータ送信は一切ありません。

## 同梱ツール

| ツール | 用途 |
| --- | --- |
| `article_rewriter.py` | note / Qiita / Zenn 向けにローカル LLM で記事を自分の文体にリライト。AI 臭の検出・除去。 |
| `heic_to_png.py` | iPhone の HEIC 画像を PNG に一括変換（リサイズ対応） |
| `benchmark_slm.py` | 小型 LLM (SLM) のベンチマーク比較。速度 / 精度を横並び測定 |
| `benchmark_per_model.sh` | benchmark_slm.py をモデル別に回すラッパー |

## セットアップ

```bash
# 依存パッケージ
pip install -r requirements.txt

# Ollama 本体とモデル
ollama pull schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest
ollama serve
```

## 推奨モデル（ハードウェア別）

リライト用途では「命令追従の強さ」「日本語の自然さ」「コード改変耐性」がモノを言います。コンテキスト長 16〜32k を使う前提で、**モデル本体で 25 GB 以内**に収まる範囲から選んでいます。

| メモリ | モデル | ollama pull 名 | サイズ目安 |
| --- | --- | --- | --- |
| 8〜16 GB | Swallow 8B (デフォルト) | `schroneko/llama-3.1-swallow-8b-instruct-v0.1` | ~5 GB |
| 8〜16 GB | Qwen2.5 7B | `qwen2.5:7b-instruct-q4_K_M` | ~5 GB |
| 8〜16 GB | Gemma 2 9B | `gemma2:9b-instruct-q4_K_M` | ~6 GB |
| 16〜24 GB | **Qwen2.5 14B** ⭐ | `qwen2.5:14b-instruct-q5_K_M` | ~11 GB |
| 16〜24 GB | Phi-4 14B | `phi4:14b` | ~9 GB |
| 24〜32 GB | **Qwen2.5 32B** ⭐ | `qwen2.5:32b-instruct-q4_K_M` | ~20 GB |
| 24〜32 GB | Gemma 2 27B (Q5) | `gemma2:27b-instruct-q5_K_M` | ~21 GB |

⭐ = その帯でまず試すと良い一手

迷ったら **`qwen2.5:14b-instruct`** から始めるのが安全です。日本語の自然さを最優先するなら Gemma 2 27B、`--deai` モードや厳しめの style_template に追従させたいなら Phi-4 14B が効きます。

### モデルを切り替える

```bash
# 環境変数で毎回指定不要に
export NOTE_REWRITER_MODEL=qwen2.5:14b-instruct

# 単発で変える
python article_rewriter.py draft.md --platform note --model gemma2:27b-instruct-q5_K_M
```

32 GB を超えるモデル（Qwen2.5 72B / Llama 3.3 70B / Swallow 70B など）は現状メモリの壁があるため、環境が整ったら追記予定です。

## article_rewriter.py

note / Qiita / Zenn の記事 (URL またはローカル .md) を、ローカル LLM で自分の文体に書き直します。

```bash
# note 向け（デフォルト）
python article_rewriter.py https://note.com/user/n/nXXXXXXX --platform note

# Qiita 向け
python article_rewriter.py draft.md --platform qiita

# Zenn 向け
python article_rewriter.py draft.md --platform zenn

# AI 臭の検出だけ（LLM 不要）
python article_rewriter.py draft.md --deai

# 品質評価レポートを生成
python article_rewriter.py draft.md --evaluate

# 自作テンプレートを使う
python article_rewriter.py draft.md --template my_style.md
```

### プラットフォーム別テンプレート

`--platform` を指定すると、`templates/<platform>.md` が自動で読み込まれます。

```
tools/templates/
├── note.md      # note 向け文体 + note の記法ルール
├── qiita.md     # Qiita 向け文体 + Qiita 記法 (> **Note**, <details>, ```lang:file)
├── zenn.md      # Zenn 向け文体 + Zenn 記法 (:::message, :::details, @[card])
├── common.md    # どのプラットフォームでも使う共通スタイルガイド
└── ai-remove.md # AI 臭除去に特化したスタイルガイド
```

`--template` を明示すると `--platform` の自動選択より優先されます。

### 主なオプション

| オプション | 説明 |
| --- | --- |
| `--platform` | `note` / `qiita` / `zenn`（デフォルト: `note`） |
| `--template` | 文体テンプレのパス（--platform より優先） |
| `--model` | Ollama モデル名（環境変数 `NOTE_REWRITER_MODEL`） |
| `--output` | 出力先ベースパス |
| `--format` | `md,txt,html` をカンマ区切り |
| `--host` | Ollama ホスト URL |
| `--dry-run` | LLM を呼ばず原文と計画だけ表示 |
| `--no-title` | タイトルはリライトしない |
| `--evaluate` | 品質評価レポートも生成 |
| `--evaluate-only` | リライトせず評価のみ |
| `--chunk-size` | 1 回の LLM 呼び出しに渡す最大文字数 |
| `--deai` | AI 臭検出のみ（LLM 不要、パターンマッチ） |

## heic_to_png.py

iPhone から書き出した HEIC を PNG に一括変換。`--width` でリサイズ可能。

```bash
python heic_to_png.py ~/Pictures -o output/ --width 1920
```

## benchmark_slm.py

小型 LLM (SLM) の比較ベンチマーク。使い方は `docs/` 配下の関連ドキュメントを参照。

## docs/

設計メモ、AI 臭除去のアルゴリズム解説、著者変更手順、その他開発時のドキュメントを収録。

## natural-japanese-writing/

「自然な日本語を生成する」ための Skill 定義 (`SKILL.md`) と eval (`evals/`)。

## ライセンス

- コード: MIT
- ドキュメント: CC-BY-4.0

詳細はリポジトリルートの [LICENSE](../LICENSE) を参照。
