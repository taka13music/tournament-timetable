# トーナメント タイムテーブル

Google スプレッドシートからトーナメントのブレイク時間を読み込み、重複をひと目で比較できるタイムテーブルです。

| 用途 | 公開先 | URL |
|------|-------------|-----|
| **管理画面**（編集） | Surge | `https://tournament-timetable.surge.sh/` |
| **閲覧用** | Netlify | `https://tournament-timetable.netlify.app/`（または自分の Netlify サイト） |

## 使い方（大会ごと）

1. 管理画面で **大会を追加**（大会名・スラッグ・シートURL・タブ範囲）
2. 大会を選んで「更新」→ その大会のシートだけ読み込み / 差分更新
3. 「生成」で閲覧用 Zip をダウンロード（`published/{スラッグ}.json` と `events.json` を含む）
4. Netlify にデプロイ
5. 閲覧は `?event=スラッグ`（例: `/?event=jopt-2025`）

大会設定はブラウザに保存され、生成 Zip の `events.json` 経由で GitHub / Netlify にも載せられます。

## スプレッドシートの形式

シートは次のような構成を想定しています。

|  | A | B | C | ... |
|--|----|----|----|-----|
| 1行目など | 日付など | | | |
| トーナメント名 | #02 Warm-up | ... | | |
| メタ情報 | fee: ¥12,000 | | | |
| メタ情報 | starting chip: 30,000 | | | |
| レベル1 | 100-200 | 15:00 | 15:20 | |
| レベル2 | 200-300 | 15:20 | 15:40 | |
| ブレイク | break | 15:40 | 16:00 | |

- **トーナメント**: シートのタブごとに 1 トーナメント
- **メタ情報**: fee / chips / レイトレジスト など
- **時間**: `15:00` 形式。営業日は 9:00 開始〜翌朝 8:00 前後まで

## 仕様メモ

- ブレイクの重なりはハイライト表示でき、移動人数も確認できる
- 営業日は 9:00 始まり（0:00〜8:59 は前日の営業日）
- 大会ごとにシート設定と公開 JSON を分けて管理できる

## デプロイ

### 管理画面 → Surge

```bash
cd ~/Projects/tournament-timetable
./setup-and-deploy-surge.sh
```

再デプロイ:

```bash
./deploy-surge.sh
```

### 閲覧用 → Netlify

1. 公開用 JSON を `published/` に置く（または管理画面で「生成」）
2. `events.json` に大会一覧を置く
3. 初回:

```bash
./setup-and-deploy-viewer.sh
```

再デプロイ:

```bash
./deploy-viewer.sh
```

ローカルで Zip を作る場合:

```bash
./build-viewer-zip.sh published/timetable.json my-tournament.zip
```

Netlify の Deploy manually にこの Zip をドラッグ＆ドロップしてください。`index.html` 単体やフォルダごと Zip は使わないでください。

### GitHub Actions（自動デプロイ）

リポジトリの Secrets に次を登録します。

- **Surge（管理画面）**: `SURGE_LOGIN` / `SURGE_TOKEN`（`./get-surge-token.sh` 参照）
- **Netlify（閲覧用）**: `NETLIFY_AUTH_TOKEN` / `NETLIFY_SITE_ID`（`./get-netlify-token.sh` 参照）

`main` へ push すると、変更内容に応じて Surge / Netlify へ自動デプロイされます（`published/**` と `events.json` 含む）。
