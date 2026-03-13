# Git branch 整理チートシート

## 方針

- `main` は常用の作業場所にしない
- 新しい作業ブランチは **`origin/main` から直接** 作る
- `advisor` / `ops` のような長寿命 base branch は増やさない
- worker の役割名は **branch 名ではなく worktree 名** で表す
- branch の削除は基本的に **手動で確認しながら行う**

---

## 新しい作業を始める

今どの branch にいても、`origin/main` から直接新しい branch を作れる。

```bash
git fetch origin
git switch -c feat/xxx origin/main
````

例:

```bash
git fetch origin
git switch -c feat/heatmap-bucket-tuning origin/main
```

---

## 状態確認

### ローカル branch の一覧を見る

```bash
git branch -vv
```

### ローカル + リモートを全部見る

```bash
git branch -a
```

### `main` に取り込まれた branch を見る

```bash
git branch --merged main
```

### `main` にまだ取り込まれていない branch を見る

```bash
git branch --no-merged main
```

---

## 「この branch を削除してよいか？」の確認

### 1. branch 固有のコミット数を確認する

```bash
git rev-list --left-right --count main...origin/branch-name
```

見方:

* 左: `main` 側だけのコミット数
* 右: `branch` 側だけのコミット数

判断の目安:

* **右が `0`** → 削除候補
* 右が少数 → 中身を見て判断
* 右が多い → 独自の履歴が残っている可能性が高い

---

### 2. 共通祖先から見た実差分があるか確認する

```bash
git diff --stat $(git merge-base main origin/branch-name)..origin/branch-name
```

判断の目安:

* **これが空** → その branch は実体差分を持っていない
* 古く止まった base branch / role branch の可能性が高い
* `log` に履歴差が出ても、実差分が空なら削除候補になりやすい

---

### 3. branch 側だけの履歴を見る

```bash
git log --oneline --decorate --graph main..origin/branch-name
```

注意:

* merge commit が並んでいても、実差分が空なら削除候補
* `log` は **履歴差**
* `diff` は **実体差**

削除判断では `diff` をより重視する

---

## 削除前の考え方

### 削除してよさそうなケース

* `git diff --stat $(git merge-base main origin/xxx)..origin/xxx` が空
* `git rev-list --left-right --count main...origin/xxx` の右が `0`
* その branch が古い base branch / role branch で、現在の運用では不要
* `main` から最新の branch を作り直す方針に移行している

### すぐ削除しないほうがよいケース

* branch 側に独自コミットがある
* 実差分がある
* その branch を今も worktree や運用上の入口として使っている
* 役割がまだ明確に置き換わっていない

---

## 削除コマンド

### リモート branch を削除する

```bash
git push origin --delete branch-name
```

### ローカル branch を削除する

```bash
git branch -d branch-name
```

### 強制削除する

```bash
git branch -D branch-name
```

### 削除後に追跡情報を掃除する

```bash
git fetch --prune
```

---

## 不安なときの保険

削除前にタグで退避しておく。

```bash
git tag backup/branch-name origin/branch-name
git push origin backup/branch-name
```

その後に branch を削除する。

```bash
git push origin --delete branch-name
```

---

## よく使う確認フロー

```bash
git fetch --prune
git branch -vv
git rev-list --left-right --count main...origin/branch-name
git diff --stat $(git merge-base main origin/branch-name)..origin/branch-name
git log --oneline --decorate --graph main..origin/branch-name
```

判断して削除してよさそうなら:

```bash
git push origin --delete branch-name
git fetch --prune
```

必要ならローカルも削除:

```bash
git branch -d branch-name
```

---

## 運用メモ

### 避けたいこと

* 古い `advisor` / `ops` / `builder` のような base branch を長く延命する
* そこへ `main` を何度も merge して使い続ける
* branch 名で worker の役割を表し続ける

### 採用する方針

* 必要なときに `origin/main` から新しい branch を作る
* worker の役割は worktree 名で表す
* 古い base branch は、差分が空なら順次削除する

---

## 一言まとめ

* `main` を checkout しなくても `origin/main` から branch は作れる
* branch の履歴差と実体差は別物
* 古い土台枝は延命するより、必要時に最新 `main` から作り直すほうがきれい
* 削除は手動確認ベースで進める
