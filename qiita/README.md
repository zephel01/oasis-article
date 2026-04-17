# qiita

Qiita 向けの記事を [qiita-cli](https://github.com/increments/qiita-cli) で管理するリポジトリです。Markdown で書いて GitHub にコミット、`qiita publish` でそのまま公開できます。

## セットアップ

```bash
# 依存インストール
npm install

# 初期化（.qiita/ と public/ を作成）
npx qiita init

# Qiita アカウントの認証（ブラウザが開きます）
npx qiita login
```

認証トークンは `~/.config/qiita-cli/credentials.json`（または macOS のキーチェーン）に保存されます。リポジトリ内には保存されません。

## 執筆フロー

```bash
# 新規記事のひな型を作成 → public/YYYYMMDD-slug.md が生成される
npx qiita new <slug>

# ローカルプレビュー（http://localhost:8888）
npm run preview

# テキストリントを実行
npm run lint

# Qiita へ公開 / 更新
npx qiita publish <article-basename>
```

## ディレクトリ構成

```
qiita/
├── public/          # 公開済み・下書きの記事 (Front Matter 付き Markdown)
├── templates/       # 自作テンプレート（コピーして public/ で使う）
├── images/          # 記事内で使う画像（任意）
├── package.json
├── .gitignore
└── README.md
```

## Front Matter の例

```yaml
---
title: "記事タイトル"
tags:
  - Python
  - LLM
  - Ollama
private: false          # true で限定共有、false で一般公開
updated_at: ""
id: null                # 公開後に自動付与される
organization_url_name: null
slide: false
ignorePublish: false    # true で publish 対象から除外（下書き用）
---
```

## テンプレート

`templates/` に以下のひな型を用意しています。コピーして `public/` に配置し、編集してください。

- `tech-article.md` — 技術解説（導入・背景・実装・検証・まとめ）
- `tutorial.md` — ハンズオン / 手順書
- `troubleshooting.md` — トラブルシューティング（症状・原因・解決）
- `benchmark.md` — 比較・ベンチマーク記事

## 参考

- Qiita CLI ドキュメント: <https://github.com/increments/qiita-cli>
- Qiita Markdown 記法: <https://qiita.com/Qiita/items/c686397e4a0f4f11683d>
