---
title: "【ハンズオン】〇〇を△△でやってみる"
tags:
  - Python
  - Tutorial
  - Beginner
private: false
updated_at: ""
id: null
organization_url_name: null
slide: false
ignorePublish: true
---

<!--
============================================================
 Qiita ハンズオン / チュートリアル テンプレート
------------------------------------------------------------
 使い方:
   手順を "1 章 = 1 動作確認" の粒度で区切ると読者が離脱しにくい
============================================================
-->

この記事を最後まで進めると、**〇〇を自分の手で動かせる状態**になります。読了 + 手を動かす目安は **約N分** です。

> **対象読者**
> - △△ を触ったことがある
> - 〇〇 という言葉を聞いたことがある

## 完成イメージ

<!-- スクリーンショットや最終成果物のコードをここに -->

## 前提環境

| 項目 | バージョン |
| --- | --- |
| OS | macOS 14 / Ubuntu 22.04 |
| Python | 3.12 |
| その他 | 〇〇 |

## STEP 1. 環境を用意する

```bash
mkdir my-app && cd my-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

動作確認:

```bash
python -c "import sys; print(sys.version)"
# → 3.12.x が出れば OK
```

## STEP 2. 〇〇を書く

```python:main.py
def main():
    print("Hello, tutorial!")

if __name__ == "__main__":
    main()
```

実行:

```bash
python main.py
# → Hello, tutorial!
```

## STEP 3. △△ を足す

<!-- 差分を diff で見せると読者が追体験しやすい -->

```diff:main.py
- def main():
-     print("Hello, tutorial!")
+ def main(name: str = "world"):
+     print(f"Hello, {name}!")
```

## STEP 4. 動かして確認する

```bash
python main.py
python main.py Qiita   # 引数パースを追加したらこうなる
```

期待する出力:

```
Hello, world!
Hello, Qiita!
```

## よくあるエラー

<details><summary>ModuleNotFoundError: No module named '〇〇'</summary>

`.venv` を有効化し忘れている可能性。`which python` で venv のパスが出るか確認。

</details>

<details><summary>Permission denied</summary>

`chmod +x main.py` で実行権限を付与。

</details>

## 次のステップ

- 〇〇 のドキュメントを読む → <https://example.com>
- 関連記事: [△△ の使い方](https://qiita.com/username/items/xxxxxxxx)
- GitHub に完成形を置いた → <https://github.com/username/repo>

## まとめ

- STEP 1〜4 で〇〇の基本を一通り体験
- 次は △△ を試すと発展的
