---
title: "【解決】〇〇で△△エラーが出たときの対処"
tags:
  - Troubleshooting
  - Python
  - Error
private: false
updated_at: ""
id: null
organization_url_name: null
slide: false
ignorePublish: true
---

<!--
============================================================
 Qiita トラブルシューティング テンプレート
------------------------------------------------------------
 基本構成: 症状 → 環境 → 原因 → 解決 → 再発防止
 SEO 的に検索される「エラーメッセージそのもの」を title/本文に入れる
============================================================
-->

## TL;DR

- **症状**: 〇〇したら `△△ エラー` が出る
- **原因**: ××（一言で）
- **解決**: `foo` を `bar` に変える

## 症状

エラーメッセージ全文を貼る（検索ヒットに重要）。

```
Traceback (most recent call last):
  File "main.py", line 10, in <module>
    ...
RuntimeError: something went wrong
```

## 発生環境

| 項目 | 値 |
| --- | --- |
| OS | macOS 14.5 |
| Python | 3.12.3 |
| 〇〇 | 1.2.3 |

## 原因

<!-- なぜこのエラーが出るかを1〜2段落で説明。図やコードで -->

根本原因は △△ である。〇〇は内部で ×× を呼び出しており、その際 ...

## 解決方法

### 方法A: 〇〇を直す（推奨）

```diff
- import foo
+ import foo.bar
```

再実行して確認:

```bash
python main.py
```

### 方法B: 一時しのぎ

```python
try:
    import foo
except ImportError:
    foo = None
```

> **Warning**
> 根本原因を解決していないので、本番環境では推奨しない。

## 再発防止

- 依存関係を `requirements.txt` でピン留めしておく
- CI でインポートチェックを入れる
- 〇〇 の破壊的変更は CHANGELOG を確認

## 参考

- [公式 Issue #123](https://github.com/xxx/yyy/issues/123)
- [関連記事](https://qiita.com/username/items/xxxxxxxx)
