# note_rewriter.py マニュアル

Note記事のAI臭を除去して、自分の文体にリライトするCLIツール（v3）。
記事の完成度を評価するレポート生成機能つき。
ローカルLLM（Ollama）を使うので、外部APIへのデータ送信なし。

---

## セットアップ

### 必要なもの

- Python 3.10以上
- Ollama（ローカルLLMランタイム）
- 推奨モデル: qwen3.5:9b（汎用）、llama-3.1-swallow-8b（日本語特化）

### インストール

```
pip install -r requirements.txt
```

requirements.txt の中身:

```
requests>=2.28.0
beautifulsoup4>=4.12.0
```

### Ollamaの準備

```
# Ollamaインストール（macOS）
brew install ollama

# モデルをダウンロード
ollama pull qwen3.5:9b

# Ollamaサーバー起動（別ターミナルで）
ollama serve
```

---

## 基本的な使い方

### リライト（メイン機能）

```
python note_rewriter.py <NoteのURL>
```

最もシンプルな実行例:

```
python note_rewriter.py https://note.com/zephel01/n/n1fce90d35555
```

記事を取得 → リライト → Markdownファイルとして保存。
出力ファイル名は記事タイトルから自動生成される（例: `記事タイトル_rewritten.md`）。

### 記事の評価のみ

```
python note_rewriter.py <URL> --evaluate-only
```

リライトせず、記事の完成度を4観点（文章品質/構成・導線/SEO・発見性/Note最適化）で100点満点で採点する。改善提案つきのレポートを `記事タイトル_eval.md` に保存。

### リライト＋比較評価

```
python note_rewriter.py <URL> --evaluate
```

リライトを実行したあと、原文と修正文を比較評価するレポートも生成する。出力はリライト結果（`_rewritten.md`）と評価レポート（`_eval.md`）の2ファイル。

比較評価レポートの内容:

- 原文 vs 修正文のスコア比較（各観点 + 総合）
- 改善された点（具体的に引用して説明）
- まだ改善の余地がある点
- リライトで悪化した点（あれば）
- 次のアクション（優先度順）

---

## オプション一覧

### --model（モデル指定）

使用するOllamaモデルを指定する。デフォルトは `qwen3.5:9b`。

```
python note_rewriter.py <URL> --model qwen3.5:9b
python note_rewriter.py <URL> --model schroneko/llama-3.1-swallow-8b-instruct-v0.1
```

指定したモデルがローカルに無い場合、自動で `ollama pull` を試みる。

### --template（文体テンプレート）

リライト時の文体ルールをMarkdownファイルで指定する。

```
python note_rewriter.py <URL> --template my_style.md
```

テンプレートを指定しない場合、スクリプトと同じディレクトリにある以下のファイルを自動検索する:

- style_template.md
- my_style.md
- template.md

いずれも見つからなければ、内蔵のデフォルトスタイルが使われる。

**デフォルトスタイルの方針:**

- 口語調・カジュアルなですます体
- 「〜してみた」「〜ハマった」「〜できた」を積極的に使う
- 一人称は省略か「自分」
- 短い文を多用（一文60字以内目安）
- 結論を先に、詳細は後に

**テンプレートの書き方例:**

```
## 文体の方針
- である調で統一
- 専門用語は初出時に簡単な説明を添える
- 一文は80字以内

## 除去するAI臭パターン
- 「〜と言えるでしょう」→ 断定に
- 「本記事では」→ 削除
```

### --format（出力形式）

出力ファイルの形式を指定する。デフォルトは `md`。

```
# Markdownで出力（デフォルト）
python note_rewriter.py <URL> --format md

# プレーンテキストで出力
python note_rewriter.py <URL> --format txt

# HTMLで出力
python note_rewriter.py <URL> --format html

# 複数形式を同時に出力（カンマ区切り）
python note_rewriter.py <URL> --format md,txt,html
```

複数指定した場合、同じベース名で拡張子だけ変わったファイルが生成される。

### --output（出力先パス）

出力ファイルのベースパスを指定する。拡張子は `--format` に合わせて自動付与。

```
python note_rewriter.py <URL> --output output/my_article
# → output/my_article.md が生成される

python note_rewriter.py <URL> --output output/my_article --format md,html
# → output/my_article.md と output/my_article.html が生成される
```

### --evaluate（リライト後に評価レポート生成）

リライト後に、原文 vs 修正文の比較評価レポートを追加生成する。

```
python note_rewriter.py <URL> --evaluate
```

### --evaluate-only（評価レポートのみ）

リライトせず、記事の現状を評価するレポートだけ生成する。

```
python note_rewriter.py <URL> --evaluate-only
```

### --host（Ollamaホスト）

OllamaのAPIエンドポイントを指定する。デフォルトは `http://localhost:11434`。

```
python note_rewriter.py <URL> --host http://192.168.1.100:11434
```

### --dry-run（原文確認のみ）

LLMを呼ばずに、記事の取得・セクション分割の結果だけ表示して終了する。

```
python note_rewriter.py <URL> --dry-run
```

確認できる内容:

- 取得した記事のタイトルと本文
- 保護されるコードブロックの数
- セクション分割数と各セクションの文字数
- 使用テンプレートの内容

### --no-title（タイトルリライトをスキップ）

タイトルのリライトを行わず、原文のタイトルをそのまま使う。

```
python note_rewriter.py <URL> --no-title
```

### --chunk-size（チャンクサイズ）

1回のLLM呼び出しに渡す最大文字数を指定する。

```
python note_rewriter.py <URL> --chunk-size 3000
```

指定しない場合、モデル名からサイズを推定して自動設定される。
小さいモデル（7B以下）は2000文字、大きいモデルは3000文字程度。

### --log-dir（ログ出力先）

ログファイルの保存先ディレクトリを指定する。デフォルトは `logs`。

```
python note_rewriter.py <URL> --log-dir /tmp/rewriter_logs
```

ログファイルは `YYYYMMDD_HHMMSS.log` 形式で保存される（例: `20260304_153045.log`）。

---

## 評価レポートの読み方

### 評価の4観点（各25点、合計100点）

**文章品質 (25点)**

AI臭の有無、読みやすさ、文体の一貫性、冗長さを評価する。問題箇所を原文から引用して具体的に指摘。

**構成・導線 (25点)**

タイトルの引き、導入の強さ、見出し構成、CTA・まとめの効果を評価する。

**SEO・発見性 (25点)**

タイトル・見出しへのキーワード配置、記事の長さの適切さを評価する。

**Note最適化 (25点)**

Markdown互換性（Noteで崩れないか）、スマホ閲覧時の段落の長さ、画像・コードの配置を評価する。

### 比較評価モード（--evaluate）

リライト前後のスコアを並べて表示し、改善された点・まだ残っている問題・悪化した点をそれぞれ列挙する。

---

## 処理時間サマリー

実行完了時に各ステップの所要時間が表示される。

```
──────────────────────────────────────────────────
⏱  処理時間サマリー
──────────────────────────────────────────────────
  モデル:         qwen3.5:9b
  記事取得:       0.2秒
  タイトル生成:   0.9秒
  セクション1:    10.0秒
  セクション2:    8.5秒
  記事評価:       15.3秒
  MD変換:        0.00秒
  ────────────────────
  合計:           34.9秒
──────────────────────────────────────────────────
```

モデルの比較をしたいときは、同じ記事を複数モデルで実行してサマリーの時間とリライト品質を見比べるとよい。

---

## ログについて

実行ごとにログファイルが `logs/` ディレクトリに自動保存される。

**コンソール出力（INFO以上）:**

- 処理の進行状況
- エラーメッセージ

**ログファイル（DEBUG以上）:**

- Ollama APIリクエストの詳細
- TTFT（最初のトークンまでの時間）
- トークン生成数と経過時間
- ストール検出（120秒間トークンが来ない場合）
- セクション分割の詳細
- プロンプト内容

問題発生時はログファイルを確認すると原因を特定しやすい。

---

## 処理の流れ

**Step 1: 記事取得**

Note非公式API → HTMLスクレイピング の順でフォールバックしながら記事を取得する。取得したHTMLをMarkdownに変換。

**Step 2: コードブロック保護**

記事中のコードブロックをプレースホルダに置換し、LLMが改変しないように保護する。リライト後に元のコードブロックを復元。

**Step 3: セクション分割**

長い記事は `--chunk-size` で指定した文字数ごとに分割される。見出し（##）の位置を優先して自然な区切りで分割。

**Step 4: LLMリライト**

各セクションをOllamaに送信し、ストリーミングでリライト結果を受け取る。反復検出が働き、同じ文が繰り返された場合は自動で中断。

**Step 5: 後処理**

プロンプトエコーの除去、プレースホルダの復元、コードブロックの検証、反復ブロックの除去を行う。

**Step 6: 評価（--evaluate時のみ）**

原文と修正文を比較し、4観点でスコアリング。改善点・残課題・悪化点をレポートにまとめる。

**Step 7: 保存**

指定したフォーマット（md/txt/html）で保存。評価レポートは `_eval.md` として別途保存。

---

## よくあるトラブル

### Ollamaに接続できない

```
[ERROR] Ollamaに接続できません。
```

→ `ollama serve` が起動しているか確認。別ターミナルで実行する。

### タイトルリライトで止まる

大きいモデル（30B以上）や思考型モデルは、タイトル生成に時間がかかることがある。120秒のストール検出が働くまで待つか、`--no-title` オプションで回避。

### 出力が途中で切れる

`--chunk-size` を小さくしてセクション分割を細かくすると改善する場合がある。

```
python note_rewriter.py <URL> --chunk-size 1500
```

### モデルが見つからない

指定したモデルがローカルに無い場合、自動で `ollama pull` が実行される。手動でダウンロードする場合:

```
ollama pull qwen3.5:9b
```

### 評価レポートが途中で切れる

記事が長すぎる場合、評価プロンプトに渡せる文字数に上限がある（原文6000文字、比較評価では各4000文字）。記事が長い場合は評価の精度がやや落ちる可能性がある。

---

## 推奨モデル

### 汎用（バランス重視）

- **qwen3.5:9b** — デフォルト。速度と品質のバランスが良い
- **qwen2.5-coder:14b** — コード多めの技術記事に向く（32GB推奨）
- **qwen3-coder:30b** — コード品質最高だがメモリ消費大（64GB推奨）

### 日本語特化

日本語の記事リライトには、日本語特化モデルの方が敬語の使い分けや文末表現の自然さで有利。

- **schroneko/llama-3.1-swallow-8b-instruct-v0.1** — 東京科学大学の日本語強化モデル。学術品質が高く、文章リライトに最適。16GBで動作
- **lucas2024/llama-3-elyza-jp-8b:q5_k_m** — ELYZA社のビジネス日本語モデル。自然な敬語表現に定評あり。16GBで動作
- **schroneko/calm3-22b-chat:q4_k_m** — サイバーエージェントのスクラッチ学習22Bモデル。日本語品質は最高レベル。32GB以上推奨
- **okamototk/gemma-2-llama-swallow:9b** — Google Gemma 2ベースに東工大Swallow日本語学習を適用。バランス型

### モデルのインストール

```
# 汎用（デフォルト）
ollama pull qwen3.5:9b

# 日本語特化（おすすめ順）
ollama pull schroneko/llama-3.1-swallow-8b-instruct-v0.1
ollama pull lucas2024/llama-3-elyza-jp-8b:q5_k_m
ollama pull schroneko/calm3-22b-chat:q4_k_m
```

### メモリ目安

- 16GB: 7B〜9Bモデル（Q4_K_M量子化）
- 32GB: 14B〜22Bモデル（Q4_K_M量子化）
- 64GB: 30B以上のモデル

### モデルの比較方法

同じ記事を複数モデルで実行して品質を比較するのが確実:

```
python note_rewriter.py <URL> --model qwen3.5:9b --output compare_qwen35
python note_rewriter.py <URL> --model schroneko/llama-3.1-swallow-8b-instruct-v0.1 --output compare_swallow
python note_rewriter.py <URL> --model lucas2024/llama-3-elyza-jp-8b:q5_k_m --output compare_elyza
```

比較ポイント: 敬語・文末表現の自然さ、AI臭の除去具合、情報の欠落がないか、処理速度。

---

## 各AIが生成する文章の癖

AI生成文を人間らしい文章にリライトするには、各AIの特徴を知っておくと効果的。
同梱の `style_template_ai_remove.md` テンプレートで以下すべてを除去対象にできる。

```
python note_rewriter.py <URL> --template style_template_ai_remove.md
```

### 全AI共通の癖

どのAIでも出やすいパターン:

- 「〜と言えるでしょう」「〜が求められます」「〜を実現しました」— 回りくどい表現
- 「本記事では〜ご紹介します」「はじめに」「まとめ」— 教科書的な構成
- 「いかがでしたか？」「それでは〜見ていきましょう」— テンプレ的な接続
- 「徹底解説」「完全ガイド」「〜のすべて」— 煽りタイトル
- 「〜することが可能です」「〜を活用することで」— 冗長な言い換え

### ChatGPT (OpenAI)

最も「AI臭い」文章を生成しやすい。特徴は過剰な肯定と教科書的構成:

- 「素晴らしい質問ですね！」的な前置き（英語だと "Certainly!" "Absolutely!"）
- 「〜が重要です」の多用
- 「以下にまとめました」「具体的には以下の通りです」— リスト導入の定型文
- 「ステップバイステップで」「お役に立てれば幸いです」— 丁寧すぎる締め
- 過度なナンバリング（1. 2. 3.）で何でもリスト化

### Claude (Anthropic)

比較的自然だが、丁寧すぎ・留保しすぎの癖がある:

- 「〜ですね」「〜かもしれません」の多用 — 断定を避ける
- 「ただし」「一方で」の過剰な留保 — バランスを取りすぎ
- 「〜と考えられます」「いくつかの点を指摘できます」— 客観風にぼかす
- 「重要な点として」「〜という点は注目に値します」— 格調高すぎ
- 英語だと "I'd be happy to help" が定番

### Gemini (Google)

構造化が好きで、聞いてないことまで答える:

- 「ポイントは3つあります」的なナンバリング予告
- 太字（**）の多用
- テーブル・表を何にでも使おうとする
- 「網羅的に」「包括的に」「〜の観点から」— 網羅志向
- 聞いていない補足情報を「ご参考までに」と追加

### Grok (xAI)

他と比べてカジュアルだが、砕けすぎ・断定しすぎの癖がある:

- 「ぶっちゃけ」「正直なところ」「まぁ」— 砕けすぎ
- 皮肉やブラックユーモアの混入
- 根拠なく断定的な物言い
- Twitter/Xネタの混入

### テンプレートの選び方

- ChatGPTで書いた記事 → `style_template_ai_remove.md` が最も効果的
- Claudeで書いた記事 → デフォルトテンプレートでも十分、留保表現を重点除去したければ `style_template_ai_remove.md`
- Geminiで書いた記事 → `style_template_ai_remove.md` + 表・リストの整理を手動で
- Grokで書いた記事 → `style_template_ai_remove.md` + 文体トーンの調整

---

## カスタムテンプレートの例

### ビジネス寄りのスタイル

```
## 文体の方針
- です・ます調で統一
- 読者を「あなた」と呼ぶ
- 導入は課題提起から始める
- 具体的な数値やデータを重視
- 一文は80字以内

## 除去するAI臭パターン
- 「〜と言えるでしょう」→ 「〜です」に断定
- 「本記事では」→ 削除
- 「〜が求められます」→ 「〜が必要です」に
```

### 技術ブログ風のスタイル

```
## 文体の方針
- である調で統一
- コード例は必ず残す
- 手順は番号付きで書く
- エラーメッセージは原文ママ
- 冗長な前置きは削除

## 除去するAI臭パターン
- 「〜と言えるでしょう」→ 削除
- 「それでは〜見ていきましょう」→ 削除
- 「いかがでしたか？」→ 削除
```

---

## 実行例まとめ

```
# 基本のリライト
python note_rewriter.py https://note.com/zephel01/n/nXXX

# 日本語特化モデルでリライト
python note_rewriter.py <URL> --model schroneko/llama-3.1-swallow-8b-instruct-v0.1

# リライト＋比較評価レポート
python note_rewriter.py <URL> --evaluate

# 評価レポートのみ（リライトしない）
python note_rewriter.py <URL> --evaluate-only

# 自分のテンプレートでリライト → txt + html で保存
python note_rewriter.py <URL> --template my_style.md --format md,txt,html

# 原文の確認だけ（LLMを呼ばない）
python note_rewriter.py <URL> --dry-run

# リモートOllamaで大型モデルを使う
python note_rewriter.py <URL> --model schroneko/calm3-22b-chat:q4_k_m --host http://192.168.1.100:11434
```

---

## ファイル構成

```
note_rewriter.py               # メインスクリプト
requirements.txt               # 依存パッケージ
style_template_ai_remove.md   # AI臭除去テンプレート（各AI対応版）
style_template.md              # 文体テンプレート（カスタム用、任意）
logs/                          # ログ出力先
  20260304_153045.log          # 実行ログ
*_rewritten.md                 # リライト結果
*_eval.md                      # 評価レポート
```
