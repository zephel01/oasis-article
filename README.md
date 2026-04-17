# oasis-article

**note / Qiita / Zenn** の3プラットフォーム向け記事執筆を支援するツール群と、それぞれの記事管理ワークスペースを1つにまとめたリポジトリです。

## 構成

```
oasis-article/
├── note/       # note.com 向け：ローカル LLM によるリライト・AI 臭除去ツール
├── qiita/      # Qiita 向け：qiita-cli ベースの記事管理 + テンプレート
└── zenn/       # Zenn 向け：zenn-cli ベースの記事管理 + テンプレート
```

3プラットフォームそれぞれに異なるワークフローがあるので、各ディレクトリは独立して動かせるようにしています。ルートにまとめた理由は「ネタが決まったら、どこに出すかを選ぶ」ためのハブとして使えるようにするためです。

## note/ — リライト・AI 臭除去ツール

詳細は [note/README.md](./note/README.md) を参照。

- `note_rewriter.py` — note.com 記事やローカル Markdown を **ローカル LLM (Ollama)** で自分の文体にリライト。ChatGPT / Claude / Gemini / Grok が出しがちな「AI 臭」40+パターンを検出・除去
- `heic_to_png.py` — iPhone の HEIC 画像を PNG に一括変換（リサイズ対応）
- `benchmark_slm.py` — Small Language Model のベンチマーク比較ツール
- `natural-japanese-writing/` — 自然な日本語を生成するための Skill 定義 + eval

```bash
cd note
pip install -r requirements.txt
python note_rewriter.py https://note.com/user/n/nXXXXXXX
```

## qiita/ — Qiita CLI ワークスペース

詳細は [qiita/README.md](./qiita/README.md) を参照。

- `public/` — 公開済み / 下書きの記事
- `templates/` — tech-article / tutorial / troubleshooting / benchmark の4種
- `package.json` — `@qiita/qiita-cli` を依存に定義

```bash
cd qiita
npm install
npx qiita login
cp templates/tech-article.md public/$(date +%Y%m%d)-slug.md
npm run preview
```

## zenn/ — Zenn CLI ワークスペース

詳細は [zenn/docs/getting-started.md](./zenn/docs/getting-started.md) を参照。

- `articles/` — Zenn 記事
- `books/` — Zenn 本
- `templates/` — tech-article / tutorial / idea-essay / multipart-series の4種
- `scripts/new-from-draft.js` — 下書きから Zenn 形式の記事に自動変換

```bash
cd zenn
npm install
npm run preview
npm run new:article
```

## 執筆プラットフォームの使い分け（目安）

| 目的 | 向いている先 |
| --- | --- |
| 個人の学び・所感・長めのエッセイ | **note** |
| 技術情報で検索から読まれたい | **Qiita** |
| コード中心で Markdown 記法をフル活用したい | **Zenn** |
| 書籍形式でまとめたい | **Zenn**（books） |

## ライセンス

- 各ツール（Python / JS コード）: MIT
- 記事本文 / テンプレート: CC-BY-4.0

詳細は [LICENSE](./LICENSE) を参照。

## 著者

くーるぜろ ([@zephel01](https://github.com/zephel01))
