<!--
note 向け：note.com の編集画面では Markdown をそのまま貼り付けられる
タイトル、見出し画像、有料エリアの区切りは note 側で入れる
note では :::message や <details>、言語+ファイル名付きコードブロックは効かない
-->

# OpenRouter の無料モデルで、いろんな LLM を API で試してみる

<!-- 上の H1 はタイトル用の仮置き。note の編集画面では H1 は書かず、
     タイトル欄にこの文字列を入れる。本文は下の導入から始める。 -->

---

「Claude だけ、ChatGPT だけで満足しているけど、他のモデルってどうなんだろう」と思う瞬間がある。Qwen、Gemma、Llama、GLM、Nemotron ── 名前はよく聞くけど、一つひとつ API 契約してまで試すのは面倒くさい。手元の Ollama で動かすにはメモリが足りないやつもある。

そこで便利なのが **OpenRouter** というサービスで、1 つの API キーで 100 以上のモデルを呼べる。おまけに、その中に **無料で使えるモデル (`:free` が付いているもの)** が 20 個以上あって、課金をしなくても試せる。私はこれを「気になるモデルの試食コーナー」として使っている。

この記事では、OpenRouter の無料モデルで色々試してみる方法と、2026 年 4 月時点で「これは触っておいていいよ」と言えるモデルを紹介する。

https://openrouter.ai/models?q=free

## OpenRouter って何

ざっくり言うと、OpenAI 互換 API で 100 種類以上のモデルに横断アクセスできるサービス。

- Anthropic (Claude)、OpenAI (GPT)、Google (Gemini)、Meta (Llama)、Qwen、DeepSeek、Mistral、xAI (Grok) など、有名どころはほぼ揃っている
- エンドポイントは `https://openrouter.ai/api/v1`、API は OpenAI 互換なので `openai` SDK がそのまま使える
- 課金はクレジット制 (前払い or 従量)
- 一部のモデルはプロバイダが「無料枠」として開放していて、`モデル名:free` という ID で呼べる

公式サイトはこちら。

https://openrouter.ai/

## 無料モデルの使い方

### 1. アカウントを作って API キーを取る

OpenRouter のサイトでアカウントを作り、ダッシュボードの Keys から API キーを発行する。キーは `sk-or-v1-...` みたいな形式になる。無料モデルだけ使う場合もキーは必要。

### 2. curl で叩いてみる

いちばん簡単に試す方法。`openai/gpt-oss-20b:free` を呼んでみる例。

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b:free",
    "messages": [
      {"role": "user", "content": "日本の秋の食べ物を3つ挙げて、それぞれ1行で説明して"}
    ]
  }'
```

`model` の値を差し替えるだけで、別のモデルに切り替えられる。ここが OpenRouter のいちばん気持ちいいところ。

### 3. Python から使う

既存の `openai` SDK がそのまま使えるので、ほとんどゼロ学習コストで入れ替えられる。

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-xxxxxxxxxxxx",
)

res = client.chat.completions.create(
    model="qwen/qwen3-next-80b-a3b-instruct:free",
    messages=[
        {"role": "user", "content": "Pythonの非同期処理を3行で説明して"}
    ],
)

print(res.choices[0].message.content)
```

`base_url` と `api_key` を差し替えるだけ。ChatGPT 用に書いたスクリプトを流用して、ついでに別モデルとの比較もできる。

### 4. 無料枠の制限について

細かい数字は運営方針でちょくちょく変わるので公式の「Limits」ページを見るのが正解だけど、大枠はこうなっている。

- 無料モデルでもレート制限 (1 分あたりのリクエスト数) がある
- 1 日あたりの合計リクエスト数にも上限があり、アカウントに一定額のクレジットを入れると上限が上がる仕組み
- 無料枠は「プロバイダが期間限定で開放している」ものもあり、急に `:free` が外れるモデルもある

要するに、本番運用には向かない。「試す」「比較する」「プロトタイプを作る」くらいの用途向き。

https://openrouter.ai/docs/api-reference/limits

## 2026 年 4 月時点のおすすめ無料モデル

OpenRouter で `:free` が付いているモデルから、個人的に「これは触っておくと見聞が広がる」と思うものを挙げる。全部 API 経由で呼べて、全部 0 円。

### 手堅く日本語で試したい：Llama 3.3 70B

`meta-llama/llama-3.3-70b-instruct:free`

Meta の 70B モデル。日本語の受け答えがわりと素直で、長文の要約やリライトに使える。Llama 系は今なお「現役のベースライン」として強い。まず 1 本試すならここから。

### 最新の大本命：Qwen3-Next 80B

`qwen/qwen3-next-80b-a3b-instruct:free`

Qwen3 系の次世代モデル。262K トークンのコンテキスト長が無料で使えるのはちょっとびっくりする。日本語の命令追従が素直で、長い資料を突っ込んで要約させるような用途が得意。

### コーディング特化：Qwen3-Coder

`qwen/qwen3-coder:free`

名前の通りコード向け。コメントの書き方や差分提案の粒度がちょうどよく、Cursor / Cline 系のエディタに繋いで「サブ LLM」として使うのもあり。

### 話題の OSS：GPT-OSS 120B / 20B

- `openai/gpt-oss-120b:free`
- `openai/gpt-oss-20b:free`

OpenAI が久々に出したオープンウェイトモデル。閉じた API と違って中身を触れるので、「OpenAI 系の挙動を自分の手元で分解したい」人には最適。120B は推論が重いけど無料なので気軽に比較できる。

### マシン 1 台で再現したい派に：Gemma 3 27B

`google/gemma-3-27b-it:free`

Google の Gemma 3 系。ローカルで Ollama を回しているなら、OpenRouter の `:free` で同じモデルの反応を見て、「自分の環境と同じ出力が出るか」の基準値として使える。日本語もだいぶ自然。

### 巨艦砲：Hermes 3 Llama 3.1 405B

`nousresearch/hermes-3-llama-3.1-405b:free`

Nous Research がファインチューンした 405B モデル。個人ではまず触れないサイズを API 経由で呼べるのは、無料枠ならではの体験。長文の執筆支援や難しめの推論で個性が出る。

### エージェント用途が気になる：GLM-4.5 Air

`z-ai/glm-4.5-air:free`

Zhipu の GLM-4.5 Air。ツール呼び出し (function calling) まわりの挙動が他モデルと違って面白い。エージェント的なことを試すならウォッチしておいて損はない。

### 軽量で速い系：Nemotron Nano 9B

`nvidia/nemotron-nano-9b-v2:free`

NVIDIA の小型モデル。9B の軽さと速さで、「雑に大量にリクエストを投げたい」系の用途に使える。チャットボットのプロトタイプとか、Jupyter で遊ぶときの作業用モデルに悪くない。

### 超大型をタダで触る：Nemotron 3 Super 120B / Minimax M2.5

- `nvidia/nemotron-3-super-120b-a12b:free`
- `minimax/minimax-m2.5:free`

いずれも 120B 級 / MoE 系の大型モデル。「触ったことはあまりないけど名前は知っている」枠を埋めるのにちょうどいい。コンテキスト長も 196K〜262K と潤沢。

## ちょっとしたコツ

### `x-ai`, `mistralai`, `openrouter/auto` もチェックする

無料枠以外でも、OpenRouter の `openrouter/auto` というルーター機能は面白い。投げたプロンプトをコストと性能で自動的に振り分けてくれる。本番ではこれ、試作では `:free` でモデル固定、という運用が回しやすい。

### `HTTP-Referer` と `X-Title` ヘッダを付けておく

OpenRouter は、リクエスト時に自分のプロジェクト URL とタイトルをヘッダに載せておくと、公式の「アプリ一覧」に表示される (任意)。API 単体で使うだけなら不要だけど、何か作って公開するなら付けておいたほうが気分がいい。

```python
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com/your/repo",
        "X-Title": "my-side-project",
    },
)
```

### ストリーミング応答もそのまま

OpenAI SDK で `stream=True` にすれば、OpenRouter 経由でもトークンが順次流れてくる。レスポンスの体感速度はモデルごとにだいぶ違うので、「この大きさでもこれだけ速いのか」みたいな比較がしやすい。

### モデルごとに「向き不向き」がある

たとえば、

- 長文要約 → Qwen3-Next 80B、Gemma 3 27B、Llama 3.3 70B
- コード生成 → Qwen3-Coder、GPT-OSS 120B
- エージェント / ツール呼び出し → GLM-4.5 Air、Hermes 3 405B
- 軽く速く → Nemotron Nano 9B、GPT-OSS 20B、Gemma 3 12B

「同じプロンプトを 3 つのモデルに投げて、結果を並べて目視で比較する」のを 30 分くらいやると、自分の用途に刺さるモデルの輪郭が見えてくる。

## OpenRouter に繋げるエージェントツール

API を直接叩くだけだと、「結局 ChatGPT のほうが便利じゃん」となりがち。そこで OpenRouter の真価が出るのは、**エディタやエージェントツールに `base_url` 差し替えで突っ込む**使い方。ここでは「対応しているよ」という紹介だけ。細かい設定や比較は別の記事にする予定。

コーディング系で、OpenRouter をそのまま設定項目として持っているツール。

- **Cline** (VSCode 拡張) … エージェントっぽく動く VSCode 拡張。設定画面に OpenRouter のプリセットがあり、`:free` モデルをそのまま指定できる
- **Roo Code** (Cline 派生) … Cline からフォークされた派生。機能追加が早く、OpenRouter 経由で最新モデルを試すときに重宝する
- **Continue** (VSCode / JetBrains) … 老舗の AI コーディング支援。`config.json` に OpenRouter 用の設定を書くだけで使える
- **Aider** (ターミナル) … ターミナル駐在型のコーディング相棒。`--openai-api-base https://openrouter.ai/api/v1` で即対応
- **Zed** (エディタ) … Rust 製のエディタ。アシスタント機能のプロバイダに OpenRouter を選べる

チャット / 汎用 UI 系。

- **Open WebUI** … Ollama 前提で有名だけど、OpenAI 互換エンドポイントとして OpenRouter も設定できる。ローカル LLM と無料クラウドモデルを同じ UI で並べられて便利
- **LibreChat** … 複数プロバイダ対応のチャット UI。`librechat.yaml` に OpenRouter エンドポイントを書けば使える
- **ChatBox / BoltAI** 等のデスクトップクライアント … 多くが OpenAI 互換エンドポイントの追加に対応していて、OpenRouter を指定すればそのまま動く

エージェント / 自律実行系。

- **OpenHands** (旧 OpenDevin) … 自律エージェント系の OSS。LLM プロバイダに OpenRouter を選べる
- **LangChain / LlamaIndex** … フレームワーク側で OpenAI 互換クライアントを使う構成なら、`base_url` の差し替えだけで移行できる

要するに **「OpenAI 互換 API を受け付けるツールなら、だいたい OpenRouter に差し替えられる」** と覚えておけばいい。`:free` モデルを刺して遊ぶ最速ルートになる。

## いつも使っているコーディング CLI に `export` で流し込む

もう一歩踏み込むと、**普段使いの OpenAI 互換 CLI は、環境変数を差し替えるだけで OpenRouter に向けられる** ことが多い。これが体感的にいちばん楽。

多くの CLI は `OPENAI_API_KEY` と `OPENAI_BASE_URL` (または `OPENAI_API_BASE`) を読む実装になっているので、シェルでこう書いておく。

```bash
export OPENAI_API_KEY="sk-or-v1-xxxxxxxxxxxx"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_MODEL="qwen/qwen3-coder:free"   # ツールが読む場合のみ
```

これだけで、

- OpenAI の **Codex CLI** 系
- **Aider** (`OPENAI_API_BASE` のほうを使う派。どちらの名前でも動くことが多い)
- **自作スクリプト** (`openai` / `httpx` / `curl` で叩いているもの)
- **LangChain / LlamaIndex** のデフォルトクライアントを使うスクリプト

あたりは、**ソースを一行も書き換えずに** OpenRouter の無料モデルに切り替えられる。個人プロジェクトなら `direnv` で `.envrc` に書いておけば、リポジトリごとに「今はこの無料モデルで試す」という切り替えができて便利。

### できない / 一筋縄でいかないケース

ただし、**全部の CLI が `export` で切り替わるわけではない**ので注意。

- **Claude Code** や **Anthropic SDK ベースのツール** … Anthropic 独自のエンドポイント (`/v1/messages`) を前提にしているので、OpenAI 互換の `base_url` を差し替えただけでは動かない。LiteLLM などの中継プロキシを間に立てる必要がある
- **Gemini CLI / Google AI Studio SDK** … Google の独自 API なので同様に直接は差し替え不可
- **一部のベンダー純正 CLI** (例：xAI Grok、Cohere など) … 自社エンドポイント固定で、環境変数で外向きにできない作りのものがある
- 環境変数を読まずに **設定ファイル (`config.yaml` など) しか見ない** ツールも一部ある。その場合は素直に設定ファイル側を編集する

見分け方としては、そのツールのドキュメントで「`OPENAI_API_KEY` と `OPENAI_BASE_URL` (または `OPENAI_API_BASE`) をサポートしているか」を確認するのが早い。対応していれば 99% の確率で OpenRouter にも向けられる。

## 注意点

最後にひとつだけ。**無料モデルは、本番で使わない前提で触る**のが無難。

- 上で書いた通り、`:free` は急に消えることがある
- 一部のプロバイダは無料枠で渡したプロンプトを学習に使うオプションがあり、オプトイン/アウトの設定が必要なことがある (機密情報は絶対に入れない方針が安全)
- レート制限は公式ドキュメントが正

あくまで「試食コーナー」として、色んなモデルを横断比較する場として使うのがちょうどいい塩梅だと思う。

## まとめ

- OpenRouter は、1 つの API キーで 100 以上のモデルを横断して呼べるサービス
- `:free` が付いているモデルは課金なしで試せる (2026 年 4 月時点で 25 個前後)
- OpenAI SDK 互換なので、既存のコードの `base_url` と `api_key` を差し替えるだけ
- 試すならまずは Llama 3.3 70B、Qwen3-Next 80B、Qwen3-Coder、GPT-OSS 120B あたり
- Cline / Continue / Aider / Open WebUI など、OpenAI 互換を受けるエージェントツールはだいたい対応している
- 本番運用よりは「モデル比較」「プロトタイプ」「見聞を広げる」用途に向く

「Claude / ChatGPT 以外も気になっていたけど、なんとなく触っていなかった」人の、最初の一歩として使ってみてほしい。

↓ モデル一覧はこちら

https://openrouter.ai/models?q=free
