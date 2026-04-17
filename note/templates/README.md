# note 向けテンプレート

`articles/` にコピーして使ってください。

| ファイル | 用途 |
| --- | --- |
| `essay.md` | 所感・日記・長めのエッセイ |
| `tech-note.md` | 技術ネタの note 化（Qiita/Zenn ほど硬くしない） |
| `review.md` | 製品 / ソフト / サービスのレビュー |

```bash
cp essay.md ../articles/$(date +%Y%m%d)-slug.md
```

## 文体ガイド

文体テンプレートは `../../tools/templates/note.md` に集約しています。リライト時は自動的にこれが使われます。
