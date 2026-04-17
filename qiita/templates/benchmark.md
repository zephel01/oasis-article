---
title: "〇〇 vs △△ vs ××：実測ベンチマーク比較"
tags:
  - Benchmark
  - LLM
  - Performance
private: false
updated_at: ""
id: null
organization_url_name: null
slide: false
ignorePublish: true
---

<!--
============================================================
 Qiita ベンチマーク / 比較記事 テンプレート
------------------------------------------------------------
 必須要素: 測定条件の明示・生データの提示・再現手順
 公平性のために「自分の測定」と「公式値の引用」を分けて書く
============================================================
-->

## TL;DR

- **〇〇** は速度重視なら1位（△△ ms）
- **××** は精度重視なら1位（F1: 0.92）
- 実運用では 〇〇 × △△ の組み合わせが現実解

## 測定対象

| モデル / ツール | バージョン | ライセンス |
| --- | --- | --- |
| 〇〇 | 1.2.3 | MIT |
| △△ | 0.9.0 | Apache-2.0 |
| ×× | 2.0.1 | BSD |

## 測定環境

| 項目 | 値 |
| --- | --- |
| CPU | Apple M3 Max |
| メモリ | 64 GB |
| OS | macOS 14.5 |
| Python | 3.12.3 |
| 測定日 | YYYY-MM-DD |

## 測定方法

- 各ツールで **同一入力** を N=10 回実行、中央値を採用
- ウォームアップ1回は計測から除外
- 計測スクリプトは GitHub に公開（末尾リンク）

```python:bench.py
import time, statistics
def bench(fn, inputs, n=10):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn(inputs)
        times.append(time.perf_counter() - t0)
    return statistics.median(times)
```

## 結果

### 速度（ms, 小さい方が良い）

| モデル | 中央値 | p95 | 備考 |
| --- | ---: | ---: | --- |
| 〇〇 | **120** | 145 | 最速 |
| △△ | 180 | 210 | 安定 |
| ×× | 250 | 300 | 精度重視 |

### 精度（F1スコア, 大きい方が良い）

| モデル | F1 |
| --- | ---: |
| 〇〇 | 0.85 |
| △△ | 0.88 |
| ×× | **0.92** |

## 考察

<!-- 数字の裏にある理由を書く。実装上の違い・アーキテクチャ差など -->

〇〇 が速いのは △△ だから。一方 ×× が精度で勝つのは ... 

## 再現手順

```bash
git clone https://github.com/username/bench-repo
cd bench-repo
pip install -r requirements.txt
python bench.py --model all --n 10
```

## まとめ

- 用途別おすすめ:
  - **速度重視** → 〇〇
  - **精度重視** → ××
  - **バランス** → △△

## 参考

- 〇〇 公式ドキュメント: <https://example.com/foo>
- △△ 論文: <https://arxiv.org/abs/xxxx.xxxxx>
- 測定コード（GitHub）: <https://github.com/username/bench-repo>
