---
title: "記事タイトル（30〜60文字目安）"
tags:
  - Python
  - LLM
  - Ollama
private: false
updated_at: ""
id: null
organization_url_name: null
slide: false
ignorePublish: true
---

<!--
============================================================
 Qiita tech記事テンプレート（汎用）
------------------------------------------------------------
 使い方:
   1. このファイルを public/ にコピーしてリネーム
   2. Front Matter の title / tags を埋める
   3. 本文の <!-- 指示 --> に沿って書き換え
   4. 公開時は ignorePublish を false に
============================================================
-->

<!-- ▼ リード文：1〜3段落で「何を・誰に・どう役立つか」を明示 -->
この記事では〇〇について、××の観点から整理します。
対象読者は △△ を使ったことがある人、想定する読了時間は 約N分 です。

> **この記事で学べること**
> - 〇〇の仕組み
> - よくある落とし穴 3つ
> - 実務で使える △△ の書き方

---

## 背景 / なぜこれを書くのか

<!-- 自分が詰まった経緯・既存情報の不足・読者がいま読むべき理由 -->

## 前提条件

- Python 3.12 以上 / Node.js 20 以上 など
- △△ の基本的な知識
- 動作確認環境: macOS 〇〇 / Python 〇〇

## 結論（忙しい人向け）

<!-- 3〜5行で結論だけ先に。詳細は後続セクションで。 -->

- ポイント1
- ポイント2
- ポイント3

## 問題

<!-- 具体例・エラーメッセージ・再現手順 -->

```
Error: xxx is not defined
    at Object.<anonymous> (/path/to/file.js:10:1)
```

## 解決方法

### 案A: 〇〇を使う

```python
# TODO: 実装例
def hello(name: str) -> str:
    return f"Hello, {name}!"
```

### 案B: ××で代替する

```python
# TODO
```

> **注意**
> この方法は △△ のケースでは動かないことがある。

## 動作確認

1. 依存関係をインストール
   ```bash
   pip install -r requirements.txt
   ```
2. 実行
   ```bash
   python main.py
   ```
3. 期待される出力
   ```
   Hello, world!
   ```

## ハマりどころ

<details><summary>〇〇エラーが出た時</summary>

原因は △△ なので、以下のように設定を直す。

```diff
- foo = 1
+ foo: int = 1
```

</details>

<details><summary>×× が反応しない時</summary>

ポートが別プロセスで使われている可能性。`lsof -i :3000` で確認。

</details>

## まとめ

- 〇〇は △△ のときに便利
- ただし ×× には注意
- 次は 〇〇 と合わせて読むとより理解が深まる

## 参考

- [公式ドキュメント](https://example.com)
- [関連記事](https://qiita.com/username/items/xxxxxxxx)

<!--
============================================================
 ▼ Qiita 記法チート（不要な行は削除）
============================================================

■ 注意ボックス
> **Note**: 情報
> **Warning**: 警告

■ 折りたたみ
<details><summary>タイトル</summary>
本文
</details>

■ コードブロック（言語・ファイル名）
```python:sample.py
print("filename付き")
```
```diff
- old
+ new
```

■ 画像
![alt](/images/foo.png)

■ 数式（KaTeX）
インライン: $E=mc^2$
ブロック:
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$

■ 目次
[[toc]]

■ 引用ツイート（そのままURLを貼る）
https://twitter.com/xxx/status/1234567890

============================================================
-->
