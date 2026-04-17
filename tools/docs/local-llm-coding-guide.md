Claude AIが使えない時の保険！Ollamaで動かすローカルLLMコーディング環境ガイド【メモリ別おすすめモデル付き】

## はじめに

Claude AIやChatGPTなどのクラウドLLMサービスは非常に便利ですが、障害やメンテナンスで使えなくなることがあります。そんな時に「コードが書けない…」と手が止まってしまうのは避けたいですよね。

この記事では、**Ollama**を使ってローカル環境でプログラミング支援LLMを動かす方法を、メモリ容量別のおすすめモデルとあわせて紹介します。

---

## なぜローカルLLMを用意しておくべきか

- **障害時のバックアップ**：クラウドサービスが落ちても作業を継続できる
- **プライバシー**：コードやデータが外部に送信されない
- **コスト削減**：API利用料が不要。ハードウェアさえあれば無料で使い放題
- **オフライン動作**：インターネット接続がなくても使える
- **低レイテンシ**：ローカル実行なのでレスポンスが速い

---

## Ollamaとは？

Ollama（ https://ollama.com/ ）は、ローカルマシンで大規模言語モデル（LLM）を簡単に動かすためのツールです。Mac・Windows・Linuxに対応しており、コマンド1つでモデルのダウンロードと実行ができます。

### インストール方法

macOS / Linuxの場合は、ターミナルで以下を実行します。

```
curl -fsSL https://ollama.com/install.sh | sh
```

Windowsの場合は ollama.com からインストーラーをダウンロードしてください。

### 基本的な使い方

モデルのダウンロードと実行はこれだけです。

```
ollama run qwen2.5-coder:7b
```

その他のよく使うコマンドはこちら。

```
ollama list
ollama pull deepseek-coder-v2:16b
```

---

## プログラミング向けおすすめモデル一覧

### Qwen2.5-Coder（Alibaba）— イチオシ

コード生成に特化したモデルで、オープンソースモデルの中でトップクラスの性能を誇ります。GPT-4oに匹敵するコード修正能力（Aiderベンチマーク73.7）を持ち、**40以上のプログラミング言語**に対応しています。

**サイズ別の一覧：**

- **0.5B** — 容量398MB / メモリ2GB〜 / `ollama run qwen2.5-coder:0.5b`
- **1.5B** — 容量986MB / メモリ4GB〜 / `ollama run qwen2.5-coder:1.5b`
- **3B** — 容量1.9GB / メモリ4GB〜 / `ollama run qwen2.5-coder:3b`
- **7B** — 容量4.7GB / メモリ8GB〜 / `ollama run qwen2.5-coder:7b`
- **14B** — 容量9.0GB / メモリ16GB〜 / `ollama run qwen2.5-coder:14b`
- **32B** — 容量20GB / メモリ32GB〜 / `ollama run qwen2.5-coder:32b`

コンテキスト長：32Kトークン
https://ollama.com/library/qwen2.5-coder

---

### GLM-4.7-Flash（Zhipu AI）

30Bクラス最強を謳うMoE（Mixture of Experts）モデル。30Bのパラメータを持ちながら、一度に活性化されるのは3Bだけなので、メモリ効率に優れています。SWE-benchで59.2を記録しており、コーディングタスクにも強いです。

**バリアント別の一覧：**

- **q4_K_M（デフォルト）** — 容量19GB / メモリ24GB〜 / `ollama run glm-4.7-flash`
- **q8_0** — 容量32GB / メモリ40GB〜 / `ollama run glm-4.7-flash:q8_0`
- **bf16（フル精度）** — 容量60GB / メモリ64GB〜 / `ollama run glm-4.7-flash:bf16`

コンテキスト長：198Kトークン（超長文に対応！）
注意：Ollama 0.14.3以降が必要です（プレリリース版）
https://ollama.com/library/glm-4.7-flash

---

### DeepSeek-Coder-V2

DeepSeekのコーディング特化モデル。MoEアーキテクチャで、16Bモデルでも実際に動くパラメータは2.4Bだけという効率設計。**338のプログラミング言語**に対応し、128Kトークンの長いコンテキストが特徴です。

**サイズ別の一覧：**

- **16B（Lite）** — 容量8.9GB / メモリ12GB〜 / `ollama run deepseek-coder-v2:16b`
- **236B** — 容量大 / メモリ128GB〜 / `ollama run deepseek-coder-v2:236b`

コンテキスト長：128Kトークン
https://ollama.com/library/deepseek-coder-v2

---

### Codestral（Mistral）

Mistralが開発した22Bのコード特化モデル。コード生成の精度が高く、温度パラメータを0.1に設定すると決定的（再現性の高い）なコード出力が得られます。

- **22B（Q4）** — 容量13GB / メモリ16GB〜 / `ollama run codestral`

コンテキスト長：32Kトークン
https://ollama.com/library/codestral

---

### Qwen3-Coder（Alibaba・最新世代）

Qwen2.5-Coderの後継で、エージェント型コーディングに特化。CLINEやCursorなどのAIコーディングツールとの連携を想定して作られています。MoEモデルで、30Bサイズ（活性化3.3B）が個人利用では現実的です。

- **30B-A3B** — 活性化3.3B / メモリ24GB〜 / `ollama run qwen3-coder:30b`

コンテキスト長：最大262Kトークン
https://ollama.com/library/qwen3-coder

---

### StarCoder2（BigCode）

600以上のプログラミング言語に対応した透明性の高いオープンソースモデル。小さいサイズでもIDEの補完機能には十分な性能を発揮します。ファインチューニングのベースモデルとしても人気です。

**サイズ別の一覧：**

- **3B** — 容量1.7GB / メモリ4GB〜 / `ollama run starcoder2:3b`
- **7B** — 容量4.0GB / メモリ8GB〜 / `ollama run starcoder2:7b`
- **15B** — 容量9.1GB / メモリ16GB〜 / `ollama run starcoder2:15b`

コンテキスト長：16Kトークン
https://ollama.com/library/starcoder2

---

## メモリ別おすすめ構成

### 16GBメモリの場合

16GBでは7B〜14Bクラスのモデルが動かせます。「とりあえず動く」レベルではなく、十分実用的な速度で使えます。

**おすすめ構成：**

- **メインモデル**：qwen2.5-coder:7b（4.7GB）— 最もバランスが良い
- **軽量サブ**：starcoder2:3b（1.7GB）— IDE補完やちょっとした質問に
- **チャレンジ**：qwen2.5-coder:14b（9.0GB）— ギリギリ動くが他のアプリと併用は厳しい

まずはこれを入れましょう。

```
ollama pull qwen2.5-coder:7b
ollama pull starcoder2:3b
```

### 32GBメモリの場合

32GBあれば選択肢がぐっと広がります。14B〜22Bクラスのモデルを快適に動かせるので、コード生成の品質が大きく向上します。

**おすすめ構成：**

- **メインモデル**：qwen2.5-coder:32b（20GB）— オープンソース最強クラス、GPT-4o匹敵
- **汎用サブ**：deepseek-coder-v2:16b（8.9GB）— 128K長文コンテキスト
- **高速サブ**：codestral（13GB）— Mistral製の高速コード生成

```
ollama pull qwen2.5-coder:32b
ollama pull deepseek-coder-v2:16b
```

### 64GBメモリの場合

64GBあれば、大型モデルをフル精度に近い形で動かせます。MoEモデルの大きなバリアントも選択肢に入り、クラウドLLMに近い体験が可能です。

**おすすめ構成：**

- **メインモデル**：qwen2.5-coder:32b（20GB）— q8_0量子化でさらに高品質
- **長文特化**：glm-4.7-flash（19GB）— 198Kトークンの超長文対応
- **推論特化**：qwen3-coder:30b — エージェント型コーディングに
- **サブモデル**：deepseek-coder-v2:16b — 多言語対応のバックアップ

```
ollama pull qwen2.5-coder:32b
ollama pull glm-4.7-flash
ollama pull qwen3-coder:30b
ollama pull deepseek-coder-v2:16b
```

---

## 量子化（Quantization）について

モデルのダウンロード時に「Q4_K_M」「Q8_0」「bf16」などの表記を見かけると思います。これは**量子化**と呼ばれる技術で、モデルの精度を少し落とす代わりにメモリ使用量を大幅に削減します。

- **Q4_K_M** — 約75%削減 / 品質は実用十分 / コスパ最高でおすすめ
- **Q5_K_M** — 約70%削減 / かなり良い品質 / バランス型
- **Q8_0** — 約50%削減 / ほぼ劣化なし / メモリに余裕があれば
- **bf16/fp16** — 削減なし / オリジナル品質 / 64GB以上推奨

Ollamaのデフォルトは多くの場合Q4_K_Mなので、特に指定しなくても効率の良い量子化が適用されます。

---

## 各ツールからOllamaに接続する方法

ローカルLLMはターミナルで対話するだけでなく、普段使いのツールやエディタと連携させることで真価を発揮します。ここでは主要なツールごとの接続方法を解説します。

---

### Claude Code × Ollama

Claude Codeは、Ollama v0.14.0以降でAnthropic Messages API互換のエンドポイントが提供されるようになったため、環境変数を3つ設定するだけでローカルモデルに切り替えられます。

**セットアップ手順**

まずOllama v0.14.0以上をインストールし、モデルをダウンロードします。

```
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:32b
```

次に、環境変数を設定してClaude Codeを起動します。

```
export ANTHROPIC_BASE_URL="http://localhost:11434"
export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
claude
```

**ポイント**

- Claude Codeはツールコール（Function Calling）機能を多用するため、**ツールコール対応モデル**を選ぶのが重要です
- おすすめモデル：qwen2.5-coder:32b、glm-4.7-flash、qwen3-coder:30b
- ローカル実行はクラウド版と比べてかなり遅くなります（体感で数十倍）。品質は近いものの、速度面は覚悟が必要です
- .bashrc や .zshrc に環境変数を書いておけば、障害時にすぐ切り替えられます

普段はコメントアウトしておき、必要な時だけ有効にする方法がおすすめです。

```
# === Ollama ローカルモード ===
# export ANTHROPIC_BASE_URL="http://localhost:11434"
# export ANTHROPIC_AUTH_TOKEN="ollama"
# export ANTHROPIC_API_KEY=""
```

---

### CLINE（VS Code拡張）× Ollama

CLINE（旧Claude Dev）はVS Code上で動くエージェント型コーディングアシスタントです。Ollamaとの連携で完全ローカルなAIコーディング環境を構築できます。

**セットアップ手順**

**Step 1：** VS Codeの拡張機能マーケットプレイスで「Cline」を検索してインストールします。

**Step 2：** Ollamaでモデルを起動します。

```
ollama run qwen2.5-coder:7b
```

**Step 3：** CLINEの設定画面を開き、以下を設定します。

- **API Provider**：OpenAI Compatible（または Ollama）
- **Base URL**：http://localhost:11434/v1
- **Model**：qwen2.5-coder:7b（ダウンロード済みのモデル名）

**ポイント**

- CLINEはファイル作成・編集・コマンド実行などの「エージェント操作」を行うため、モデルの能力が低いと指示に従えないことがあります
- 最低でも7B以上、できれば14B〜32Bクラスのモデルを推奨します
- 小さなモデルではツール呼び出しに失敗しやすいので、シンプルなタスクから試しましょう

---

### Continue（VS Code拡張）× Ollama

Continueは、VS CodeとJetBrains IDEに対応したオープンソースのAIコーディングアシスタントです。**コード補完**と**チャット**の両方をローカルモデルで動かせるのが魅力です。

**セットアップ手順**

**Step 1：** VS Codeの拡張機能マーケットプレイスで「Continue」を検索してインストールします。

**Step 2：** Cmd + Shift + P（Mac）/ Ctrl + Shift + P（Win/Linux）で「Continue: Open config.json」を選択し、以下のように設定します。

```
{
  "models": [
    {
      "title": "Qwen2.5 Coder 7B",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b",
      "apiBase": "http://localhost:11434/"
    }
  ],
  "tabAutocompleteModel": {
    "title": "StarCoder2 3B",
    "provider": "ollama",
    "model": "starcoder2:3b",
    "apiBase": "http://localhost:11434/"
  }
}
```

**ポイント**

- **チャット用**と**コード補完用**で別々のモデルを設定できるのが強みです
- チャット用には賢い大きめのモデル（qwen2.5-coder:7b以上）、補完用には軽くて速いモデル（starcoder2:3b）がおすすめ
- GitHub Copilotの代替として使えます

---

### Cursor × Ollama

CursorはAI機能が組み込まれたコードエディタですが、ローカルモデルも利用可能です。ただし、直接接続ではなくngrok経由でのセットアップが必要になります。

**セットアップ手順**

**Step 1：** ngrokをインストールします。

```
brew install ngrok
```

https://ngrok.com/ からもダウンロードできます。

**Step 2：** OllamaのCORS設定を変更します。

```
export OLLAMA_ORIGINS="*"
```

**Step 3：** ngrokでトンネルを作成します。

```
ngrok http 11434 --host-header="localhost:11434"
```

表示されるURLをコピーしてください（例：https://xxxx-xxx.ngrok-free.app ）。

**Step 4：** Cursorの設定画面で以下を入力します。

- Settings → Models を開く
- OpenAI API Keyの欄にダミー値（ollamaなど）を入力
- Base URLにngrokのURLを入力
- モデル名を追加（例：qwen2.5-coder:7b）
- ローカルモデルだけを選択し、Verifyをクリック

**ポイント**

- Cursorのローカルモデル対応はやや回り道が必要ですが、一度設定すれば快適に使えます
- ngrokの無料プランにはセッション時間の制限があるため、長時間利用にはngrokの有料プランか別のトンネリングツールを検討してください

---

### Open WebUI × Ollama

ブラウザベースのChatGPT風インターフェースでOllamaモデルを使えるツールです。ターミナルが苦手な方や、チャット形式でコードの相談をしたい場合におすすめです。

**セットアップ手順**

Dockerで以下のコマンドを実行するだけです。

```
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

起動後、http://localhost:3000 にアクセスすればすぐに使えます。Ollamaが起動していれば、モデルが自動的に認識されます。

---

### ツール比較まとめ

- **Claude Code** — ターミナルベースのエージェント / セットアップ簡単（環境変数3つ）/ CLIでのコーディング全般に
- **CLINE** — VS Codeエージェント型 / セットアップ簡単 / ファイル作成・編集の自動化に
- **Continue** — VS Code補完＋チャット / セットアップ簡単 / Copilotの代替、日常のコーディングに
- **Cursor** — AI統合エディタ / セットアップやや複雑（ngrok必要）/ Cursor愛用者のローカル切替に
- **Open WebUI** — ブラウザチャットUI / セットアップ簡単（Docker）/ チャット形式でのコード相談に

---

## まとめ

- **16GB** → qwen2.5-coder:7b がおすすめ。まずは試してみたい方、日常の軽いコーディング補助に。
- **32GB** → qwen2.5-coder:32b がおすすめ。本格的にローカルLLMを使いたい方、品質重視。
- **64GB** → qwen2.5-coder:32b + glm-4.7-flash がおすすめ。クラウド並みの体験、複数モデルの使い分けも。

クラウドAIサービスが使えない時でも、ローカルLLMを準備しておけば作業を止める必要はありません。特にQwen2.5-Coderシリーズはコストパフォーマンスに優れており、GPT-4oクラスのコード支援をローカルで受けられるのは大きな魅力です。

まずは `ollama run qwen2.5-coder:7b` から試してみてください！

---

*この記事の情報は2026年3月時点のものです。モデルのバージョンや性能は日々更新されていますので、最新情報は各モデルの公式ページをご確認ください。*
