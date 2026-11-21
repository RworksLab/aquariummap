"""座標の一括取得（国土地理院 住所検索API）

座標が空欄で、住所が登録されている施設だけを、1件ずつ順番に検索して書き込む。

使い方（リポジトリの一番上で）:
  python3 tools/geocode_batch.py            # 実行して data/facilities.json に書き込む
  python3 tools/geocode_batch.py --dry-run  # 書き込まずに結果だけ表示

安全のための決まり:
- 同時に複数のリクエストを送らない（1件ごとに2秒待つ）
- 取得済みの座標は再取得しない
- HTTP 403 / 429 などのエラーが出たらその場で止める（自動の再試行はしない）
- アクセスした回数と結果を logs/geocode_YYYY-MM-DD.json に記録する

採用基準: 返ってきた住所表記が番地・号・街区（「番」）まで一致、または
登録住所の全体と一致した場合だけ採用。町名・字まででとどまったものは空欄のまま。
"""
import datetime, json, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

API = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
WAIT_SEC = 2
KANJI = str.maketrans("〇一二三四五六七八九", "0123456789")


def query_address(addr: str, pref: str) -> str:
    """郵便番号・改行・建物名・括弧書きを除き、番地までの住所にする。都道府県が無ければ補う。"""
    a = unicodedata.normalize("NFKC", addr)
    a = re.sub(r"(〒|郵便番号)\s*\d{3}-?\d{4}", " ", a)
    a = re.sub(r"[（(].*?[）)]", " ", a)
    lines = [l.strip() for l in re.split(r"[\n\r]+", a) if l.strip()]
    line = next((l for l in lines if re.search(r"\d", l) and re.search(r"[都道府県市区町村郡]", l)), lines[0] if lines else "")
    # 空白の後ろは建物名とみなす（「山下町144 チャイナスクエア3F」→「山下町144」）
    token = next((t for t in line.split() if re.search(r"[都道府県市区町村郡]", t)), line.split()[0] if line.split() else "")
    m = re.match(r"^(.*\d(?:番地|番|号)?)", token)  # 最後の数字（番地）まで
    q = m.group(1) if m else token
    if pref and not q.startswith(pref):
        q = pref + q
    return q


def kansuji(s: str) -> str:
    def conv(m):
        t = m.group(0).translate(KANJI)
        if "十" in t:
            a, _, b = t.partition("十")
            return str((int(a) if a else 1) * 10 + (int(b) if b else 0))
        return t
    return re.sub(r"[〇一二三四五六七八九十]+(?=丁目)", conv, s)


def flat(s: str) -> str:
    s = kansuji(unicodedata.normalize("NFKC", s))
    s = re.sub(r"丁目|番地|番|号", "-", s).replace("ヶ", "ケ").replace("字", "")
    s = re.sub(r"^(東京都|北海道|京都府|大阪府|.{2,3}県)", "", s)
    s = re.sub(r"^.{1,5}郡", "", s)
    return re.sub(r"[-\s]+", "-", s).strip("-")


def judge(q: str, title: str):
    t = unicodedata.normalize("NFKC", title)
    if re.search(r"\d+番|番地|\d+号", t):
        return True, "番地・号・街区まで一致"
    if flat(title) == flat(q):
        return True, "登録住所の全体と一致"
    return False, "町名・字までしか一致せず空欄"


def main(path="data/facilities.json", dry=False):
    data = json.load(open(path, encoding="utf-8"))
    targets = [f for f in data["facilities"] if f["lat"] is None and f.get("address")]
    today = datetime.date.today().isoformat()
    log = {"date": today, "host": "msearch.gsi.go.jp", "requests": []}
    print(f"対象 {len(targets)} 件（座標が空欄で住所がある施設）")
    got, stop = 0, None
    for f in targets:
        q = query_address(f["address"], f["prefecture"])
        entry = {"id": f["id"], "name": f["name"], "query": q}
        log["requests"].append(entry)
        try:
            with urllib.request.urlopen(API + urllib.parse.quote(q), timeout=20) as r:
                res = json.load(r)
            entry["http"] = 200
        except urllib.error.HTTPError as e:
            entry["http"] = e.code; stop = f"HTTP {e.code}"
        except Exception as e:  # 接続できないときも止める
            entry["http"] = None; stop = f"接続失敗: {e}"
        if stop:
            print(f"  停止: {stop}（{f['name']}）。自動の再試行はしません。")
            break
        if not res:
            ok, note, hit = False, "検索結果なし", None
        else:
            lng, lat = res[0]["geometry"]["coordinates"]; hit = (lat, lng, res[0]["properties"]["title"])
            ok, note = judge(q, hit[2])
        entry.update(result=note, matched=hit[2] if hit else None)
        if ok:
            f["lat"], f["lng"] = round(hit[0], 6), round(hit[1], 6)
            f["coord_source"] = "gsi_geocode"
            f.setdefault("sources", []).append({"ref": "gsi", "fields": ["lat", "lng"]})
            got += 1
        f["coord_note"] = note + (f"（一致表記: {hit[2]}）" if hit else "")
        print(f"  {'○' if ok else '×'} {f['name']}: {f['coord_note']}")
        time.sleep(WAIT_SEC)
    m = data["meta"]
    m["with_coordinates"] = sum(x["lat"] is not None for x in data["facilities"])
    m["without_coordinates"] = len(data["facilities"]) - m["with_coordinates"]
    log["summary"] = {"requests": len(log["requests"]), "success": got, "stopped": stop}
    print(f"アクセス {len(log['requests'])} 回・取得 {got} 件・座標あり 計 {m['with_coordinates']} 件")
    if not dry:
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(log, open(f"logs/geocode_{today}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    args = sys.argv[1:]
    paths = [a for a in args if not a.startswith("--")]
    main(paths[0] if paths else "data/facilities.json", "--dry-run" in args)
