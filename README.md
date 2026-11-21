# 水族館訪問マップ

日本全国の水族館を巡り、自分だけの訪問記録やコレクションを作るためのウェブアプリです。
スマートフォンでの利用を前提にした1ページのアプリで、サーバーは不要です（GitHub Pages でそのまま公開できます）。

- マップ：全国の水族館の位置。訪問済みの施設はスタンプ、未訪問は白いピンで表示
- 一覧：検索、都道府県・訪問状況・お気に入りで絞り込み、地図の位置へ移動
- 記録：訪問日・評価・感想・写真のアルバム
- マイページ：達成率、都道府県別の訪問数、お気に入り数、記録のファイル保存・読み込み

## 公開のしかた（GitHub Pages）

1. このフォルダの中身をそのまま GitHub のリポジトリに置く（`index.html` が一番上に来るように）
2. リポジトリの **Settings → Pages** を開く
3. **Build and deployment** の Source を「Deploy from a branch」、Branch を `main`、フォルダを `/ (root)` にして Save
4. 数分後に表示される URL（`https://<ユーザー名>.github.io/<リポジトリ名>/`）を開く

`.nojekyll` は GitHub Pages に余計な変換をさせないためのファイルです。消さないでください。

## 訪問記録の保存先について

- GitHub Pages などで公開した場合、訪問記録・お気に入り・写真は **それぞれの利用者のブラウザ（端末）の中** に保存されます。サーバーには送られません。
- ブラウザのデータを消すと記録も消えるため、マイページの「記録をファイルに保存」でときどき保存してください。「ファイルから読み込む」は記録を **追加するだけ** で、今ある記録を上書き・削除しません。
- claude.ai のアーティファクトとして開いた場合は、claude.ai のクラウドに保存されます（公開版とは記録が別になります）。

## 施設データの更新

施設データはすべて `data/facilities.json` にあります。アプリはこのファイルを読み込むだけなので、**このファイルを更新して push すれば公開中のアプリにも反映されます**。

| ファイル | 内容 |
|---|---|
| `data/facilities.json` | 施設データ本体（`meta` に件数・出典・ルール、`facilities` に施設の配列） |
| `data/pending.json` | 収録を保留している候補、未開業、閉館で除外したもの |
| `data/japan-prefectures.topo.json` | 地図の都道府県境界 |
| `icons/`, `manifest.webmanifest` | アプリアイコン（ホーム画面に追加したときのアイコンなど） |
| `tools/validate.py` | データの検証（ID・施設名の重複、必須項目、座標の範囲など） |
| `tools/geocode_batch.py` | 座標が空欄で住所のある施設だけ、国土地理院の住所検索で座標を一括取得 |
| `tools/history/` | 初期データを作ったときのスクリプト（記録用。再実行しない） |
| `sources/`, `logs/` | 取得したデータの控えと、アクセスの記録 |

### 守ってほしいルール

- **施設 ID（`aq-都道府県番号-番号`）は変えない・使い回さない。** 訪問記録は ID で施設と結び付いています。
- **閉館した施設は削除しない。** `status` を `closed` にして `closed_date` を入れる。地図と一覧には残り、過去の記録も見られ、新しい訪問だけ記録できなくなります。
- 確認できない項目は `null`（空欄）にする。推測で埋めない。
- 新しい施設を追加するときは、同じ都道府県の最後の番号の次を使う（例：`aq-13-0011`）。

### 更新の手順

```bash
# 1. data/facilities.json を編集する（または Claude に依頼する）
# 2. 検証
python3 tools/validate.py
# 3. 住所を追加した施設の座標を取る（必要なときだけ）
python3 tools/geocode_batch.py --dry-run   # 試しに実行（書き込まない）
python3 tools/geocode_batch.py
# 4. 反映
git add data logs && git commit -m "施設データを更新" && git push
```

push すると GitHub Actions（`.github/workflows/validate.yml`）が自動で検証し、問題があれば赤い ✕ が付きます。

`meta.version` と `meta.generated_at` も更新しておくと、いつのデータか分かりやすくなります。

## データの出典とライセンス

- 施設の座標・公式サイト・住所の一部：[Wikidata](https://www.wikidata.org/)（CC0）
- 座標の一部：国土地理院 住所検索
- 地図の境界：地球地図日本（国土地理院）を加工して作成（[dataofjapan/land](https://github.com/dataofjapan/land) 経由）
- 収録候補の確認：水族館マップ（aquarium-map.com）、マンボウなんでも博物館「日本の水族館マップ」。いずれも施設名と都道府県の確認だけに使い、地図データや説明文は複製していません。
- 関東の25施設は、各施設の公式サイト・自治体・日本動物園水族館協会などで個別に確認しています。それ以外は「施設一覧に掲載」段階で、`verification` が `listed` になっています。

OpenStreetMap のデータを取り込む場合は、アプリ内に「© OpenStreetMap contributors」を表示し、ODbL の条件に従ってください。

施設の情報は変わることがあります。お出かけ前には各施設の公式情報を確認してください。

## 使っている外部ライブラリ

- [D3.js](https://d3js.org/) 7.8.5、[TopoJSON Client](https://github.com/topojson/topojson-client) 3.0.2（cdnjs から読み込み）
- フォント：Zen Kaku Gothic New、Zen Maru Gothic（Google Fonts）
