"""施設データ（data/facilities.json）の検証。

使い方（リポジトリの一番上で）:  python3 tools/validate.py
GitHub に push すると自動でも実行される（.github/workflows/validate.yml）。
問題があれば一覧を出して終了コード 1 で終わる。
"""
import json, math, re, sys, unicodedata
from collections import Counter

PREFS = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
REQUIRED = ["id", "name", "prefecture", "category", "status"]


def norm(s):
    return re.sub(r"[\s・　（）()「」]", "", unicodedata.normalize("NFKC", s or ""))


def main(path="data/facilities.json"):
    d = json.load(open(path, encoding="utf-8"))
    meta, facs = d["meta"], d["facilities"]
    cats = set(meta["rules"]["category_labels"]); stats = set(meta["rules"]["status_labels"])
    errs, warns = [], []
    for k, v in Counter(f["id"] for f in facs).items():
        if v > 1: errs.append(f"ID が重複: {k}")
    for k, v in Counter(norm(f["name"]) for f in facs).items():
        if v > 1: errs.append(f"施設名が重複: {k}")
    for f in facs:
        fid = f.get("id", "?")
        for k in REQUIRED:
            if not f.get(k): errs.append(f"{fid}: {k} が空")
        if not re.fullmatch(r"aq-\d{2}-[0-9a-z]+", fid): errs.append(f"{fid}: ID の形式が違う")
        if f.get("prefecture") not in PREFS: errs.append(f"{fid}: 都道府県名が不正")
        elif fid[3:5] != f"{PREFS.index(f['prefecture'])+1:02d}": warns.append(f"{fid}: ID の県番号と都道府県が違う")
        if f.get("category") not in cats: errs.append(f"{fid}: 分類が不正 ({f.get('category')})")
        if f.get("status") not in stats: errs.append(f"{fid}: 営業状況が不正 ({f.get('status')})")
        if f.get("status") != "closed" and f.get("closed_date"): warns.append(f"{fid}: 営業中なのに閉館日がある")
        lat, lng = f.get("lat"), f.get("lng")
        if (lat is None) != (lng is None): errs.append(f"{fid}: 緯度・経度の片方だけ")
        elif lat is not None and not (20 < lat < 46 and 122 < lng < 154): errs.append(f"{fid}: 座標が日本の範囲外")
        addr = f.get("address") or ""
        other = [p for p in PREFS if p in addr and p != f.get("prefecture")]
        if other and f.get("prefecture") not in addr:
            warns.append(f"{fid}: 住所に別の都道府県名（{other[0]}）がある")
    pts = [f for f in facs if f.get("lat") is not None]
    for i, a in enumerate(pts):
        for b in pts[i+1:]:
            dist = 6371000 * math.hypot(math.radians(b["lat"]-a["lat"]), math.radians(b["lng"]-a["lng"]) * math.cos(math.radians(a["lat"])))
            if dist < 200: warns.append(f"200m 以内に別の施設: {a['name']} / {b['name']}（{dist:.0f}m）")
    if meta.get("total") != len(facs): warns.append(f"meta.total ({meta.get('total')}) と件数 ({len(facs)}) が違う")
    json.load(open("data/pending.json", encoding="utf-8"))
    print(f"施設 {len(facs)} 件・座標あり {len(pts)} 件・エラー {len(errs)} 件・警告 {len(warns)} 件")
    for m in errs: print("エラー:", m)
    for m in warns: print("警告:", m)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
