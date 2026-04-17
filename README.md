<div align="center">

# 🌴 oasis-article

### *Your single source of truth for writing on note / Qiita / Zenn*

AI 臭を落とし、自分の文体で、3つのプラットフォームに届ける。

<br>

[![License: MIT (code)](https://img.shields.io/badge/code-MIT-blue.svg)](./LICENSE)
[![License: CC BY 4.0 (docs)](https://img.shields.io/badge/docs-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node 20+](https://img.shields.io/badge/node-20%2B-5FA04E?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Ollama](https://img.shields.io/badge/Ollama-local-000?logo=ollama&logoColor=white)](https://ollama.ai/)
[![note](https://img.shields.io/badge/note.com-41C9B4?logo=note&logoColor=white)](https://note.com/)
[![Qiita](https://img.shields.io/badge/Qiita-55C500?logo=qiita&logoColor=white)](https://qiita.com/)
[![Zenn](https://img.shields.io/badge/Zenn-3EA8FF?logo=zenn&logoColor=white)](https://zenn.dev/)

<br>

```

   ╭─────────────╮      ╭─────────────╮      ╭─────────────╮      ╭─────────────╮
   │   💡 idea   │  ──▶ │  ✍️ draft   │  ──▶ │ 🧽 rewrite │  ──▶ │  🚀 publish │
   ╰─────────────╯      ╰─────────────╯      ╰─────────────╯      ╰─────────────╯
                                                    │
                                           ╭────────┴────────╮
                                    🦙 local LLM         ✂️  AI臭 40+ patterns
                                       (Ollama)

```

</div>

## ✨ これは何か

**oasis-article** は、note / Qiita / Zenn の3プラットフォームで書き続けるためのモノレポです。

- 🦙 **ローカル LLM でリライト** — Ollama で完結、外部 API にデータを出さない
- 🧽 **AI 臭の検出と除去** — ChatGPT / Claude / Gemini / Grok が出しがちな 40+パターン
- 🎭 **1 本の記事を 3 媒体に最適化** — `--platform note|qiita|zenn` で文体と記法を切替
- 🗂️ **各媒体の CLI ワークスペース付属** — zenn-cli / qiita-cli のひな型まで揃う
- 📊 **品質評価レポート** — 文章品質・構成・SEO・媒体適合度をスコアリング
- 🛡️ **コードブロック保護** — LLM にコードや図表を改変させない差分検証付き

## 🗺️ 構成

```
oasis-article/
├── 🛠️  tools/    ← ローカル LLM ツール（3媒体共通）
├── 📝  note/     ← note.com 記事ワークスペース
├── 📚  qiita/    ← Qiita CLI ワークスペース
└── ⚡  zenn/     ← Zenn CLI ワークスペース
```

| ディレクトリ | 役割 | 主なツール / ファイル |
| --- | --- | --- |
| 🛠️ [`tools/`](./tools) | 共通 CLI ツール群 | `article_rewriter.py`, `heic_to_png.py`, `benchmark_slm.py` |
| 📝 [`note/`](./note) | note 記事ワークスペース | `articles/`, `templates/essay.md` ほか |
| 📚 [`qiita/`](./qiita) | Qiita CLI 用 | `@qiita/qiita-cli`, `templates/tech-article.md` ほか |
| ⚡ [`zenn/`](./zenn) | Zenn CLI 用 | `zenn-cli`, `articles/`, `templates/`, `scripts/new-from-draft.js` |

## 🚀 クイックスタート

### 前提

```bash
# Python 3.12+, Node 20+, Ollama
brew install ollama
ollama pull schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest
ollama serve
```

> 🦙 **使う Ollama モデルの選び方**（16 / 24 / 32 GB 別の推奨表）は [tools/README.md#推奨モデルハードウェア別](./tools/README.md#推奨モデルハードウェア別) を参照。迷ったら `qwen2.5:14b-instruct` から。

### 依存インストール

```bash
# 共通ツール
cd tools && pip install -r requirements.txt && cd ..

# Qiita / Zenn (必要な方だけ)
cd qiita && npm install && cd ..
cd zenn  && npm install && cd ..
```

### 1 本の下書きを 3 媒体に分ける

```bash
# 共通の下書き
echo "# 〇〇を触ってみた話" > draft.md

# 媒体別にリライト
python tools/article_rewriter.py draft.md --platform note  --output note/articles/draft
python tools/article_rewriter.py draft.md --platform qiita --output qiita/public/draft
python tools/article_rewriter.py draft.md --platform zenn  --output zenn/articles/draft
```

`--platform` で文体テンプレと媒体固有の記法指示 (`:::message` / `> **Note**:` / note の装飾ルール) が自動で切り替わります。

### AI 臭だけ検出する

```bash
python tools/article_rewriter.py draft.md --deai
```

LLM を呼ばず、パターンマッチで「いかがでしたか？」「〜と言えるでしょう」などを指摘します。

## 🎯 使い分けの目安

| 目的 | おすすめの公開先 |
| --- | --- |
| 個人の学び・所感・長めのエッセイ | 📝 **note** |
| 技術情報で検索から読まれたい | 📚 **Qiita** |
| コード中心で Markdown 記法をフル活用したい | ⚡ **Zenn** |
| 書籍形式でまとめたい | ⚡ **Zenn**（books） |

## 🧰 article_rewriter の主なオプション

| フラグ | 役割 |
| --- | --- |
| `--platform note\|qiita\|zenn` | 出力先媒体（デフォルト: `note`） |
| `--template PATH` | 自作スタイルテンプレ（`--platform` より優先） |
| `--model NAME` | Ollama モデル（`NOTE_REWRITER_MODEL` 環境変数でも可） |
| `--format md,txt,html` | 出力形式を複数同時に |
| `--deai` | LLM を呼ばず AI 臭のパターン検出のみ |
| `--evaluate` | 品質評価レポートも生成 |
| `--dry-run` | 取得だけして LLM は呼ばない |

詳細は [tools/README.md](./tools/README.md) を参照。

## 📜 ライセンス

- コード（`*.py`, `*.js`, `*.sh`, `*.json`, `*.toml`）: **MIT**
- 記事本文・テンプレート・ドキュメント（`*.md`, `*.txt`）: **CC BY 4.0**

詳細は [LICENSE](./LICENSE) を参照。

## 👤 著者

**くーるぜろ** — [@zephel01](https://github.com/zephel01)

<div align="center">
<sub>🌴 Happy writing.</sub>
</div>
