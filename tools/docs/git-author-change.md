# Git Author 変更手順

Git コミットの Author 情報を後から変更する方法のまとめ。

## Author の仕組み

コミット時の Author は以下の優先順位で決まる。

1. **ローカル設定**（`.git/config`）— そのリポジトリのみ
2. **グローバル設定**（`~/.gitconfig`）— 全リポジトリ共通
3. **システム設定**（`/etc/gitconfig`）— マシン全体

## グローバル設定の確認・変更

```bash
# 現在の設定を確認
git config --global user.name
git config --global user.email

# 変更
git config --global user.name "zephel01"
git config --global user.email "zephel01@gmail.com"
```

特定のリポジトリだけ別の Author にしたい場合は、そのリポジトリ内で `--global` なしで実行する。

## 過去コミットの Author 変更

### 直前の 1 件だけ

```bash
git commit --amend --author="zephel01 <zephel01@gmail.com>" --no-edit
```

### 特定のコミットを変更

```bash
# 対象の 1 つ前のコミットハッシュを指定
git rebase -i <コミットハッシュ>
# エディタで対象行の pick → edit に変更して保存

git commit --amend --author="zephel01 <zephel01@gmail.com>" --no-edit
git rebase --continue
```

### 全コミットを一括変更（git filter-repo）

```bash
pip install git-filter-repo

git filter-repo --name-callback 'return b"zephel01"' \
                --email-callback 'return b"zephel01@gmail.com"'
```

## filter-repo でエラーが出た場合

```
Aborting: Refusing to destructively overwrite repo history since
this does not look like a fresh clone.
```

### 対処法 A: ゴミ掃除して --force

```bash
git gc --prune=now
git filter-repo --name-callback 'return b"zephel01"' \
                --email-callback 'return b"zephel01@gmail.com"' \
                --force
```

### 対処法 B: fresh clone してから実行

```bash
cd ..
git clone <元のリポジトリ> <リポジトリ名>-clean
cd <リポジトリ名>-clean
git filter-repo --name-callback 'return b"zephel01"' \
                --email-callback 'return b"zephel01@gmail.com"'
```

## リモートへの反映

Author 変更はコミットハッシュが全て変わるため force push が必要。

```bash
# filter-repo は remote を削除するので再設定
git remote add origin <リポジトリURL>

# force push（他人の変更があれば拒否してくれる安全版）
git push --force-with-lease
```

## 注意事項

- コミットハッシュが変わるため、PR やイシューのコミット参照リンクが壊れる可能性がある
- 他の人が clone 済みの場合、履歴が衝突する
- 個人リポジトリや共有前であれば問題なし
