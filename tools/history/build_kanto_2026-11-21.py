# 記録用：2026-11-21 の関東試作データ作成に使ったスクリプト。現在のデータを上書きするため再実行しないこと。
"""関東試作データの生成と検証。
施設データ（facilities.json）と保留リスト（pending.json）を作り、
重複・必須項目・件数をチェックする。
"""
import json, re, unicodedata, math
from collections import Counter

TODAY = "2026-11-21"

SRC = {
    "jaza": {"name": "日本動物園水族館協会 正会員名簿【水族館】（令和8年7月13日現在）",
             "url": "https://www.jaza.jp/about-jaza/structure/list-aquarium", "accessed": TODAY},
    "wikipedia": {"name": "Wikipedia「日本の水族館一覧」（候補抽出のみに使用）",
                  "url": "https://ja.wikipedia.org/wiki/日本の水族館一覧", "accessed": TODAY},
    "gsi": {"name": "国土地理院 住所検索API（座標取得）",
            "url": "https://msearch.gsi.go.jp/address-search/AddressSearch", "accessed": TODAY},
}

PREF = {"茨城県": "08", "栃木県": "09", "群馬県": "10", "埼玉県": "11",
        "千葉県": "12", "東京都": "13", "神奈川県": "14"}

CATEGORY_LABEL = {
    "general_aquarium": "一般的な水族館",
    "small_aquarium": "小規模水族館",
    "freshwater_aquarium": "淡水魚水族館",
    "in_facility": "動物園・施設内の水族館",
    "marine_exhibit": "海洋生物展示施設",
    "learning_exhibit": "水生生物の学習展示施設",
}
STATUS_LABEL = {"operating": "営業中", "temporarily_closed": "休館中",
                "closed": "閉館", "unknown": "不明"}

# 座標精度: 番地/号/街区まで一致、または公式住所全体と一致したものだけ採用
# lat/lng=None は「取得できず」または「未取得」
F = [
 # pref, name, address, cat, url, (lng,lat) or None, coord_note, sources[(url, fields)], extra
 ("茨城県","アクアワールド茨城県大洗水族館","茨城県東茨城郡大洗町磯浜町8252-3","general_aquarium",
  "https://www.aquaworld-oarai.com/",(140.588028,36.3241),"番地一致",
  [("https://www.aquaworld-oarai.com/information/about/",["name","address"])],{}),
 ("茨城県","かすみがうら市水族館","茨城県かすみがうら市坂910-1","freshwater_aquarium",
  None,None,"町名までしか一致せず空欄",
  [("https://www.pref.ibaraki.jp/soshiki/seikatsukankyo/kasumigauraesc/05_gakushu/kojyouschool/documents/2021_10kasumigaurasshisuizokukan.pdf",["name","address"])],
  {"notes":"歩崎公園内"}),
 ("栃木県","栃木県なかがわ水遊園","栃木県大田原市佐良土2686","freshwater_aquarium",
  "https://tnap.jp/",None,"町名までしか一致せず空欄",
  [("https://tnap.jp/park/access.php",["name","address"]),("jaza",["name","address"])],{}),
 ("栃木県","さかなと森の観察園","栃木県日光市中宮祠2482-3","learning_exhibit",
  None,(139.493256,36.728291),"番地一致",
  [("https://www.gltjp.com/ja/directory/item/15052/",["name","address","status"])],
  {"notes":"水産研究・教育機構の広報施設。冬期休園（営業期間3/20〜11/30）"}),
 ("群馬県","水産学習館（道の駅みなかみ水紀行館）","群馬県利根郡みなかみ町湯原1681-1","freshwater_aquarium",
  None,(138.969696,36.765873),"番地一致",
  [("https://rurubu.jp/andmore/spot/80008328",["name","address"])],
  {"parent_facility":"道の駅みなかみ水紀行館",
   "notes":"道の駅内だが、トンネル水槽などを備えた独立した淡水魚の展示館のため収録（要確認）"}),
 ("群馬県","桐生が岡動物園 水族館","群馬県桐生市宮本町3-8-13","in_facility",
  None,(139.33992,36.419548),"号まで一致",
  [("https://www.city.kiryu.lg.jp/_res/projects/default_project/_page_/001/005/753/no.37.pdf",["name","address"])],
  {"parent_facility":"桐生が岡動物園","notes":"座標は動物園の代表住所"}),
 ("埼玉県","さいたま水族館","埼玉県羽生市三田ヶ谷751-1","freshwater_aquarium",
  "https://www.parks.or.jp/suizokukan/",(139.598053,36.173141),"番地一致",
  [("https://www.parks.or.jp/suizokukan/",["name","address"]),("jaza",["name","address"])],
  {"notes":"羽生水郷公園内"}),
 ("千葉県","鴨川シーワールド","千葉県鴨川市東町1464-18","general_aquarium",
  "https://www.kamogawa-seaworld.jp/",(140.122452,35.117218),"番地一致",
  [("https://www.kamogawa-seaworld.jp/access/",["name","address"]),("jaza",["name","address"])],{}),
 ("千葉県","かつうら海中公園 海中展望塔","千葉県勝浦市吉尾174","marine_exhibit",
  None,(140.286545,35.136028),"番地一致",
  [("https://rurubu.jp/andmore/spot/80009740",["name","address"])],
  {"notes":"海中の自然の魚を観察する展望塔"}),
 ("千葉県","世界一ちっちゃな水族館","千葉県銚子市潮見町15-9","small_aquarium",
  None,None,"町名までしか一致せず空欄",
  [("https://maruchiba.jp/spot/detail_11255.html",["name","address"])],
  {"parent_facility":"銚子海洋研究所"}),
 ("東京都","サンシャイン水族館","東京都豊島区東池袋3-1-3 サンシャインシティ ワールドインポートマートビル屋上","general_aquarium",
  "https://sunshinecity.jp/aquarium/",(139.719986,35.727844),"号まで一致",
  [("https://sunshinecity.jp/aquarium/access/",["name","address"]),("https://sunshinecity.jp/aquarium/legal.html",["address"])],{}),
 ("東京都","東京都葛西臨海水族園","東京都江戸川区臨海町6-2-3","general_aquarium",
  "https://www.tokyo-zoo.net/zoo/kasai/",(139.855331,35.640774),"街区まで一致",
  [("https://www.tokyo-zoo.net/zoo/kasai/directions.html",["name","address"]),("jaza",["name","address"])],
  {"aliases":["葛西臨海水族園"],"notes":"葛西臨海公園内。園内で新水族園を建設中"}),
 ("東京都","しながわ水族館","東京都品川区勝島3-2-1","general_aquarium",
  "https://www.aquarium.gr.jp/",(139.736954,35.588001),"号まで一致",
  [("https://www.aquarium.gr.jp/outline",["name","address"])],{"notes":"しながわ区民公園内"}),
 ("東京都","マクセル アクアパーク品川","東京都港区高輪4-10-30（品川プリンスホテル内）","general_aquarium",
  "https://www.aqua-park.jp/",(139.736984,35.628574),"街区まで一致",
  [("https://www.aqua-park.jp/aqua/access/index.html",["name","address"])],
  {"aliases":["アクアパーク品川"]}),
 ("東京都","すみだ水族館","東京都墨田区押上1-1-2 東京スカイツリータウン・ソラマチ5F・6F","general_aquarium",
  "https://www.sumida-aquarium.com/",(139.808609,35.710083),"号まで一致",
  [("https://www.sumida-aquarium.com/about/access/",["name","address"])],{}),
 ("東京都","井の頭自然文化園 水生物館","東京都武蔵野市御殿山1-17-6","in_facility",
  "https://www.tokyo-zoo.net/inokashira/",(139.573074,35.700573),"号まで一致",
  [("https://www.tokyo-zoo.net/inokashira/exhibits/aquatic-life-house/index.html",["name","address"])],
  {"parent_facility":"井の頭自然文化園",
   "notes":"淡水生物の水族館。水生物館は分園にあり、座標は園の代表住所（本園）"}),
 ("東京都","足立区生物園","東京都足立区保木間2-17-1","in_facility",
  "https://seibutuen.jp/",(139.806992,35.793121),"街区まで一致",
  [("https://seibutuen.jp/guidance/information.html",["name","address"])],
  {"notes":"昆虫・魚類などを展示する生物園。元渕江公園内"}),
 ("東京都","板橋区立熱帯環境植物館 ミニ水族館","東京都板橋区高島平8-29-2","in_facility",
  "https://www.seibu-la.co.jp/nettaikan/",(139.664566,35.791729),"号まで一致",
  [("https://www.seibu-la.co.jp/nettaikan/facility.html",["name","address"]),
   ("https://www.city.itabashi.tokyo.jp/kusei/chosha/1043016/1042967/1043209.html",["address"])],
  {"parent_facility":"板橋区立熱帯環境植物館","notes":"地下1階のミニ水族館（約150種）"}),
 ("東京都","小笠原海洋センター","東京都小笠原村父島字屏風谷","marine_exhibit",
  "https://bonin-ocean.net/",None,"村・島名までしか一致せず空欄",
  [("https://bonin-ocean.net/archives/18161",["status"]),("https://bonin-ocean.net/recruitment-guide-of-volunteer",["address"])],
  {"status":"temporarily_closed","status_note":"改修工事のため2026年8月〜2027年3月末まで休館（公式発表）",
   "notes":"ウミガメの展示・保全施設"}),
 ("神奈川県","横浜・八景島シーパラダイス","神奈川県横浜市金沢区八景島","general_aquarium",
  "https://www.seaparadise.co.jp/",(139.644135,35.336521),"公式住所全体と一致（番地なし）",
  [("https://www.seaparadise.co.jp/contact/index.html",["name","address"]),("jaza",["name","address"])],{}),
 ("神奈川県","新江ノ島水族館","神奈川県藤沢市片瀬海岸2-19-1","general_aquarium",
  "https://www.enosui.com/",(139.479889,35.310005),"号まで一致",
  [("https://www.enosui.com/contact.php",["name","address"])],{}),
 ("神奈川県","カワスイ 川崎水族館","神奈川県川崎市川崎区日進町1-11 川崎ルフロン9・10階","general_aquarium",
  "https://kawa-sui.com/",None,"未取得（アクセス削減のため次回一括取得）",
  [("https://kawa-sui.com/",["name","address"]),("jaza",["name","address"])],{}),
 ("神奈川県","相模川ふれあい科学館 アクアリウムさがみはら","神奈川県相模原市中央区水郷田名1-5-1","freshwater_aquarium",
  "https://sagamigawa-fureai.com/",None,"未取得（アクセス削減のため次回一括取得）",
  [("https://www.pref.kanagawa.jp/docs/bs5/cnt/f4898/p14371.html",["name","address","official_url"])],{}),
 ("神奈川県","箱根園水族館","神奈川県足柄下郡箱根町元箱根139","general_aquarium",
  None,None,"未取得（アクセス削減のため次回一括取得）",
  [("https://kanagawa-kankou.or.jp/spot/311",["name","address"])],{"parent_facility":"箱根園"}),
 ("神奈川県","横浜開運水族館 フォーチュンアクアリウム","神奈川県横浜市中区山下町144 チャイナスクエア3F","small_aquarium",
  None,None,"未取得（アクセス削減のため次回一括取得）",
  [("https://kanagawa-kankou.or.jp/spot/7382",["name","address"])],{"notes":"横浜中華街内"}),
]

PENDING = [
 ("東京都","よみうりランド アシカ館","所在地が資料間で食い違う（JAZA名簿は神奈川県川崎市多摩区、遊園地の住所は東京都稲城市）ため、確認できるまで保留"),
 ("東京都","アートアクアリウム美術館 GINZA","金魚を使ったアート展示の美術館。水族館として扱うか要判断"),
 ("神奈川県","北里アクアリウムラボ","北里大学キャンパス内のミニ水族館。一般公開の条件を未確認"),
 ("神奈川県","タッチうおっち水族館","ソレイユの丘内のふれあい施設（12種）。小規模な水槽展示に当たるか要判断"),
 ("神奈川県","観音崎自然博物館","博物館。水槽展示の規模が除外対象に当たるか要判断"),
 ("神奈川県","まかどシーマリンパーク（横浜市立間門小学校附属水族館）","小学校附属。一般公開の条件を未確認"),
 ("埼玉県","ハートフル桶西水族館（埼玉県立桶川西高等学校）","高校内。一般公開の条件を未確認"),
 ("埼玉県","埼玉県立川の博物館","博物館の水槽展示。除外対象に当たるか要判断"),
 ("千葉県","千葉大学 海洋バイオシステム研究センター水族館","大学施設。一般公開の条件を未確認"),
 ("千葉県","“渚の駅”たてやま 海辺の広場","渚の駅（道の駅に類する施設）内の展示。除外対象に当たるか要判断"),
 ("茨城県","ミュージアムパーク茨城県自然博物館","博物館の水槽展示。除外対象に当たるか要判断"),
 ("東京都","小笠原水産センター","水産施設の展示室。規模を未確認"),
]
UPCOMING = [("東京都","東京よみうり水族館","2027年夏開業予定と報道。未開業のため未登録")]

def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"[\s・　（）()]", "", s)

def build():
    counters = Counter()
    facilities = []
    for pref, name, addr, cat, url, coord, cnote, srcs, extra in F:
        code = PREF[pref]
        counters[code] += 1
        fid = f"aq-{code}-{counters[code]:04d}"
        sources = []
        for u, fields in srcs:
            if u in SRC:
                sources.append({"ref": u, "fields": fields})
            else:
                sources.append({"url": u, "accessed": TODAY, "fields": fields})
        rec = {
            "id": fid, "name": name, "aliases": extra.get("aliases", []),
            "prefecture": pref, "prefecture_code": code, "address": addr,
            "lat": coord[1] if coord else None, "lng": coord[0] if coord else None,
            "coord_source": "gsi_geocode" if coord else None, "coord_note": cnote,
            "category": cat, "official_url": url,
            "status": extra.get("status", "operating"), "status_note": extra.get("status_note"),
            "closed_date": None, "parent_facility": extra.get("parent_facility"),
            "notes": extra.get("notes"), "sources": sources,
            "registered_at": TODAY, "verified_at": TODAY,
        }
        facilities.append(rec)
    return facilities

def validate(facs):
    errs = []
    ids = [f["id"] for f in facs]
    if len(ids) != len(set(ids)): errs.append("ID重複")
    keys = Counter(norm(f["name"]) for f in facs)
    errs += [f"名称重複: {k}" for k, v in keys.items() if v > 1]
    addr = Counter(norm(f["address"]) for f in facs)
    errs += [f"住所重複: {k}" for k, v in addr.items() if v > 1]
    for f in facs:
        for k in ("name", "prefecture", "address", "category", "status"):
            if not f[k]: errs.append(f"{f['id']} {k} 空")
        if f["category"] not in CATEGORY_LABEL: errs.append(f"{f['id']} 分類不正")
        if f["status"] not in STATUS_LABEL: errs.append(f"{f['id']} 営業状況不正")
        if not f["address"].startswith(f["prefecture"]): errs.append(f"{f['id']} 都道府県と住所不一致")
        if (f["lat"] is None) != (f["lng"] is None): errs.append(f"{f['id']} 座標片側のみ")
        if f["lat"] is not None and not (24 < f["lat"] < 46 and 122 < f["lng"] < 154):
            errs.append(f"{f['id']} 座標範囲外")
    # 200m以内の近接チェック（警告）
    warns = []
    pts = [f for f in facs if f["lat"] is not None]
    for i, a in enumerate(pts):
        for b in pts[i+1:]:
            d = 6371000 * math.hypot(math.radians(b["lat"]-a["lat"]),
                 math.radians(b["lng"]-a["lng"]) * math.cos(math.radians(a["lat"])))
            if d < 200: warns.append(f"近接 {a['name']} / {b['name']} {d:.0f}m")
    return errs, warns

if __name__ == "__main__":
    facs = build()
    errs, warns = validate(facs)
    assert not errs, errs
    by_status = Counter(f["status"] for f in facs)
    by_pref = Counter(f["prefecture"] for f in facs)
    by_cat = Counter(f["category"] for f in facs)
    meta = {
        "dataset": "水族館訪問マップ 施設データ（関東試作版）",
        "version": "0.1.0", "generated_at": TODAY, "region": "関東（1都6県）",
        "total": len(facs),
        "count_by_status": {STATUS_LABEL[k]: v for k, v in by_status.items()},
        "count_by_prefecture": dict(by_pref),
        "count_by_category": {CATEGORY_LABEL[k]: v for k, v in by_cat.items()},
        "with_coordinates": sum(f["lat"] is not None for f in facs),
        "without_coordinates": sum(f["lat"] is None for f in facs),
        "sources": SRC,
        "rules": {
            "included": "実在が公式サイト・公的機関・都県観光公式サイト等で確認できた施設のみ",
            "empty_fields": "確認できない項目は null（空欄）",
            "coordinates": "確認済み住所を国土地理院住所検索で変換。番地・号・街区まで一致、または公式住所全体と一致した場合のみ採用。それ以外は null",
            "closed_policy": "登録後に閉館した施設は削除せず status=closed に変更し、closed_date を記録する",
            "category_labels": CATEGORY_LABEL, "status_labels": STATUS_LABEL,
        },
        "warnings": warns,
    }
    json.dump({"meta": meta, "facilities": facs},
              open("data/facilities.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    pend = {"generated_at": TODAY,
            "pending": [{"prefecture": p, "name": n, "reason": r} for p, n, r in PENDING],
            "upcoming": [{"prefecture": p, "name": n, "reason": r} for p, n, r in UPCOMING]}
    json.dump(pend, open("data/pending.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: meta[k] for k in ("total","count_by_status","count_by_prefecture","with_coordinates","without_coordinates","warnings")}, ensure_ascii=False, indent=1))
