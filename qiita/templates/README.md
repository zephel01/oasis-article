# Qiita 記事テンプレート

`public/` にコピーして使ってください。先頭の Front Matter (`---`〜`---`) は **残したまま** title と tags を書き換えて編集します。

| ファイル | 用途 |
| --- | --- |
| `tech-article.md` | 技術解説（導入・背景・実装・検証・まとめ） |
| `tutorial.md` | ハンズオン / 手順書（STEP形式） |
| `troubleshooting.md` | エラー対処（症状 → 原因 → 解決） |
| `benchmark.md` | 比較・ベンチマーク記事 |

## 使い方

```bash
# 例: 新しいチュートリアル記事を作る
cp templates/tutorial.md public/$(date +%Y%m%d)-my-new-article.md

# 編集
$EDITOR public/$(date +%Y%m%d)-my-new-article.md

# ローカルプレビュー
npm run preview

# 公開（ignorePublish: false にしてから）
npx qiita publish <basename>
```

## Front Matter の注意点

- `ignorePublish: true` にしておくと `qiita publish` で対象外になります。下書き中はこれを推奨。
- `private: true` は限定共有（URL を知っている人だけが読める）。
- `id`, `updated_at`, `organization_url_name` は公開後に qiita-cli が自動で埋めます。
