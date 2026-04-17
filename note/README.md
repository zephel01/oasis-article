# note

[note.com](https://note.com/) 向けの記事ワークスペース。下書きやリライト前後の記事を `articles/` に置き、リライト・AI 臭除去は共通ツール `../tools/article_rewriter.py` を使います。

## ディレクトリ

```
note/
├── README.md
├── articles/    # 下書き・リライト後の記事 (*.md)
└── templates/   # note 向けの構成テンプレート
```

## 執筆フロー

```bash
# 1. テンプレートをコピーして下書きを作る
cp templates/essay.md articles/$(date +%Y%m%d)-slug.md

# 2. 書く
$EDITOR articles/$(date +%Y%m%d)-slug.md

# 3. AI 臭チェック（LLM 不要）
python ../tools/article_rewriter.py articles/$(date +%Y%m%d)-slug.md --deai

# 4. ローカル LLM で文体リライト
python ../tools/article_rewriter.py articles/$(date +%Y%m%d)-slug.md \
  --platform note \
  --output articles/$(date +%Y%m%d)-slug-rewritten

# 5. できあがった Markdown を note.com の編集画面にコピペ
```

## note.com 投稿時のポイント

- 本文は Markdown で書いておき、note.com の編集画面では **リッチテキスト** に貼り付けると多くの装飾が維持されます
- 見出しは H2 / H3 まで。note は H4 以降を細かく区別しません
- `:::message` や `<details>` など Zenn / Qiita の独自記法は note では効かないので使わない
- 画像はキャプションを前提に並べる（「↑ 実測結果の一枚」など）

## テンプレート

| ファイル | 想定用途 |
| --- | --- |
| `templates/essay.md` | 所感・日記・長めのエッセイ |
| `templates/tech-note.md` | 技術ネタの note 化（Qiita/Zenn ほど硬くしない） |
| `templates/review.md` | 製品 / ツールのレビュー |

## 関連

- 共通ツール: [../tools/README.md](../tools/README.md)
- note 向け文体テンプレ: [../tools/templates/note.md](../tools/templates/note.md)
