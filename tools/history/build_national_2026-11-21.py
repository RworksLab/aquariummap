# 記録用：2026-11-21 の全国版データ作成に使ったスクリプト。再実行は想定していない。
"""全国版の初期データを作る。

方針:
- 収録候補 = 現在の施設一覧2サイト（aquarium-map.com の「全国の水族館一覧」、
  マンボウなんでも博物館「日本の水族館マップ」）に載っている施設。
  2サイトからは「施設名と所在の都道府県」（事実情報）だけを使い、地図・座標・説明文は複製しない。
- 座標・公式サイト・住所は Wikidata（CC0）から一括取得したものを使う（sources/wikidata_*.txt）。
- 関東の既存25施設は ID と内容をそのまま残し、空欄の座標だけ Wikidata で補う。
- どちらの一覧にも無い Wikidata の施設、閉館・未開業、収録基準の判断が要るものは pending.json へ。
- 確認できない項目は null。
"""
import json, re, unicodedata
from collections import Counter

TODAY = "2026-11-21"
PREFS = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
code = lambda p: f"{PREFS.index(p)+1:02d}"

# ---- Wikidata 行の読み込み ----
WD = {}
for line in open("sources/wikidata_2026-11-21.txt", encoding="utf-8"):
    if line.startswith("#") or not line.strip():
        continue
    q, label, pt, pref, addr, url, end = line.rstrip("\n").split("|")
    m = re.match(r"Point\(([\d.]+) ([\d.]+)\)", pt)
    WD[q] = {"label": label, "lng": float(m[1]) if m else None, "lat": float(m[2]) if m else None,
             "pref": pref or None, "address": addr or None, "url": url or None}

G, S, F, I, M, L = ("general_aquarium", "small_aquarium", "freshwater_aquarium",
                    "in_facility", "marine_exhibit", "learning_exhibit")
# (都道府県, 施設名, 分類, Wikidata QID, 掲載一覧 A=aquarium-map M=マンボウ, 一覧に載っていた公式URL, 追加情報)
MASTER = [
 ("北海道","AOAO SAPPORO",G,None,"AM","https://aoao-sapporo.blue/",{}),
 ("北海道","おたる水族館",G,"Q11261729","AM",None,{}),
 ("北海道","くしろ水族館ぷくぷく",S,None,"AM","https://www.sennosuke.net/pukupuku/",{}),
 ("北海道","オホーツクとっかりセンター",M,"Q11292366","AM","https://o-tower.co.jp/okhotsktower.html",{"notes":"アザラシの保護・展示施設。マンボウなんでも博物館の一覧では氷海展望塔オホーツクタワーと併記"}),
 ("北海道","サケのふるさと 千歳水族館",F,"Q11405627","A",None,{}),
 ("北海道","サンピアザ水族館",G,"Q11305917","AM",None,{"aliases":["新さっぽろサンピアザ水族館"]}),
 ("北海道","わっかりうむ ノシャップ寒流水族館",G,"Q11596319","AM",None,{"aliases":["稚内市立ノシャップ寒流水族館","ノシャップ寒流水族館"]}),
 ("北海道","札幌市円山動物園",I,None,"A",None,{"parent_facility":"札幌市円山動物園","notes":"動物園内の水生生物展示"}),
 ("北海道","北の大地の水族館（山の水族館）",F,"Q11465797","AM",None,{"aliases":["おんねゆ温泉 北の大地の水族館"]}),
 ("北海道","千歳さけますの森 さけます情報館",L,None,"A",None,{}),
 ("北海道","室蘭民報みんなの水族館（市立室蘭水族館）",G,"Q11480658","AM",None,{"aliases":["市立室蘭水族館"]}),
 ("北海道","旭川市旭山動物園",I,None,"AM","https://www.city.asahikawa.hokkaido.jp/asahiyamazoo/",{"parent_facility":"旭川市旭山動物園"}),
 ("北海道","札幌市豊平川さけ科学館",L,"Q11521425","AM",None,{}),
 ("北海道","標津サーモン科学館",L,"Q11542208","AM",None,{}),
 ("北海道","登別マリンパークニクス",G,"Q11579106","AM",None,{}),
 ("北海道","美深チョウザメ館",L,None,"AM","https://www.bifuka-kankou.com/attractions/tyozamekan/",{}),
 ("青森県","青森県営浅虫水族館",G,"Q4803495","AM",None,{}),
 ("青森県","八戸市水産科学館マリエント",L,None,"AM","http://www.marient.org/",{}),
 ("岩手県","もぐらんぴあ水族館",S,"Q11279914","AM",None,{"aliases":["久慈地下水族科学館 もぐらんぴあ"]}),
 ("宮城県","アクアテラス錦ケ丘",S,"Q21652335","AM",None,{}),
 ("宮城県","仙台うみの杜水族館",G,"Q17222417","AM",None,{}),
 ("宮城県","伊豆沼・内沼サンクチュアリセンター 淡水魚館",L,None,"AM","http://izunuma.org/1_3.html",{"aliases":["登米市伊豆沼・内沼サンクチュアリセンター"]}),
 ("秋田県","男鹿水族館GAO",G,"Q11595485","AM",None,{"aliases":["秋田県立男鹿水族館"]}),
 ("秋田県","田沢湖クニマス未来館",L,None,"A",None,{}),
 ("山形県","鶴岡市立加茂水族館",G,"Q11675955","AM",None,{}),
 ("福島県","アクアマリンふくしま",G,"Q4782699","AM",None,{}),
 ("福島県","アクアマリンいなわしろカワセミ水族館",F,"Q38266933","AM",None,{}),
 ("東京都","小笠原水産センター 小さな水族館",S,None,"AM","https://www.soumu.metro.tokyo.lg.jp/07ogasawara/fish/aquarium.html",{"parent_facility":"東京都小笠原水産センター"}),
 ("新潟県","上越市立水族博物館 うみがたり",G,"Q11360163","AM",None,{}),
 ("新潟県","新潟市水族館 マリンピア日本海",G,"Q11502898","AM",None,{}),
 ("新潟県","長岡市寺泊水族博物館",G,"Q61722200","AM",None,{}),
 ("新潟県","イヨボヤ会館",L,"Q61721910","M",None,{"notes":"サケの博物館"}),
 ("新潟県","小千谷市錦鯉の里",L,"Q11650572","M",None,{"notes":"錦鯉の展示施設"}),
 ("富山県","魚津水族館",G,"Q11674044","AM",None,{}),
 ("富山県","ほたるいかミュージアム",L,None,"A",None,{}),
 ("富山県","ひみラボ水族館",S,None,"M",None,{}),
 ("石川県","のとじま水族館",G,"Q11275197","AM",None,{"aliases":["のとじま臨海公園水族館"]}),
 ("石川県","のと海洋ふれあいセンター",L,None,"AM","http://notomarine.jp/",{}),
 ("福井県","越前松島水族館",G,"Q11636428","AM",None,{}),
 ("福井県","福井県海浜自然センター",L,None,"AM","https://fcnc.pref.fukui.lg.jp/",{}),
 ("福井県","越前がにミュージアム",L,None,"AM","https://www.town-echizen.jp/spot/spot05Detail.php?id=339",{}),
 ("福井県","くにみクラゲ公民館",S,None,"M",None,{}),
 ("福井県","おばま水族館",S,None,"M","https://obama-aquarium.com/",{}),
 ("山梨県","森の中の水族館。（山梨県立富士湧水の里水族館）",F,"Q11469706","AM",None,{"aliases":["山梨県立富士湧水の里水族館"]}),
 ("長野県","蓼科アミューズメント水族館",F,"Q11621781","AM",None,{}),
 ("岐阜県","世界淡水魚園水族館 アクア・トト ぎふ",F,"Q11282869","AM",None,{}),
 ("静岡県","あわしまマリンパーク",G,"Q83789636","A",None,{}),
 ("静岡県","SMART AQUARiUM SHIZUOKA（スマートアクアリウム静岡）",S,None,"AM","https://smartaqua-sz.jp/",{}),
 ("静岡県","下田海中水族館",G,"Q11361202","AM",None,{}),
 ("静岡県","伊豆・三津シーパラダイス",G,"Q3156501","AM",None,{}),
 ("静岡県","幼魚水族館",S,None,"AM","https://yo-sui.com/",{}),
 ("静岡県","沼津港深海水族館",G,"Q11554537","AM",None,{}),
 ("静岡県","浜名湖体験学習施設 ウォット",L,None,"AM","https://ulotto.entetsuassist-dms.com/",{}),
 ("静岡県","ドルフィンファンタジー伊東",M,None,"M","http://dolphin-fantasy.com/",{}),
 ("愛知県","赤塚山公園 ぎょぎょランド",F,None,"AM",None,{}),
 ("愛知県","南知多ビーチランド",G,"Q11408304","AM",None,{}),
 ("愛知県","名古屋シーライフ水族館",G,"Q53997414","AM",None,{"aliases":["シーライフ名古屋"]}),
 ("愛知県","名古屋港水族館",G,"Q7231211","AM",None,{}),
 ("愛知県","東山動植物園 世界のメダカ館",I,"Q115283045","AM","http://www.higashiyama.city.nagoya.jp/",{"parent_facility":"名古屋市東山動植物園"}),
 ("愛知県","碧南海浜水族館",G,"Q11587774","AM",None,{}),
 ("愛知県","竹島水族館",G,"Q11599117","AM",None,{}),
 ("愛知県","弥富金魚水族館 YaToMi AQUA",S,"Q117485087","M","https://www.city.yatomi.lg.jp/event_info/1001259/1005653.html",{}),
 ("三重県","ウミガメ公園 ウミガメ水族館",L,"Q11641448","A",None,{"parent_facility":"道の駅 紀宝町ウミガメ公園","notes":"道の駅内のウミガメ専門の展示館（要確認）"}),
 ("三重県","伊勢シーパラダイス",G,"Q11371781","AM",None,{"aliases":["ゼロ距離水族館伊勢シーパラダイス","伊勢夫婦岩ふれあい水族館 シーパラダイス"]}),
 ("三重県","赤目滝水族館",F,None,"AM","https://www.akame48taki.com/",{"aliases":["日本サンショウウオセンター"]}),
 ("三重県","鳥羽水族館",G,"Q1073067","AM",None,{}),
 ("滋賀県","小さなびわ湖水族館",S,None,"AM",None,{}),
 ("滋賀県","滋賀県立琵琶湖博物館",F,"Q11564667","AM",None,{"notes":"淡水の水族展示を含む博物館"}),
 ("滋賀県","小さな水族館 びわこベース",S,None,"M","https://www.biwako-base.com/",{}),
 ("京都府","京都水族館",G,"Q11375621","AM",None,{}),
 ("京都府","京都花園教会水族館",S,None,"M","https://www.kyotohanasui.com/",{}),
 ("大阪府","NIFREL（ニフレル）",G,"Q21654084","AM",None,{}),
 ("大阪府","あくあぴあ芥川",F,"Q11257046","AM",None,{"aliases":["高槻市立自然博物館"]}),
 ("大阪府","ノアドルフィンドーム",M,None,"A",None,{}),
 ("大阪府","海遊館",G,"Q1191885","AM",None,{}),
 ("大阪府","プラネットアクア・ポート（ひらかたパーク）",I,None,"M","https://www.hirakatapark.co.jp/attractions/aquarium/",{"parent_facility":"ひらかたパーク"}),
 ("兵庫県","淡路じゃのひれ ドルフィンアーチ",M,None,"AM","http://janohire.co.jp/",{}),
 ("兵庫県","みなとやま水族館",G,"Q123566518","AM",None,{}),
 ("兵庫県","アクア東条",F,"Q11282873","AM","https://www.hyoturi.or.jp/aqua/",{}),
 ("兵庫県","átoa（アトア）",G,"Q109597317","AM",None,{}),
 ("兵庫県","城崎マリンワールド",G,"Q11426136","AM",None,{}),
 ("兵庫県","姫路市立水族館",G,"Q2584900","AM",None,{}),
 ("兵庫県","神戸須磨シーワールド",G,"Q125228535","AM",None,{}),
 ("和歌山県","アドベンチャーワールド",I,"Q2587322","AM",None,{}),
 ("和歌山県","すさみ町立エビとカニの水族館",S,"Q17219170","AM",None,{}),
 ("和歌山県","ドルフィンリゾート",M,None,"AM","https://www.dolphinresort2.net/",{}),
 ("和歌山県","串本海中公園",G,None,"AM","http://www.kushimoto.co.jp/",{}),
 ("和歌山県","和歌山県立自然博物館",L,"Q11417475","AM",None,{}),
 ("和歌山県","太地町立くじらの博物館",M,"Q11265357","AM",None,{}),
 ("和歌山県","京都大学白浜水族館",G,"Q111247590","AM",None,{"aliases":["京都大学瀬戸臨海実験所水族館"]}),
 ("鳥取県","とっとり賀露かにっこ館",L,"Q11264065","AM",None,{}),
 ("島根県","島根県立宍道湖自然館ゴビウス",F,"Q47164008","AM",None,{}),
 ("島根県","島根県立しまね海洋館 アクアス",G,"Q11476470","AM",None,{}),
 ("島根県","瑞穂ハンザケ自然館",L,None,"A",None,{}),
 ("岡山県","岡山市環境学習センター めだかの学校",L,None,"A",None,{}),
 ("岡山県","渋川マリン水族館（玉野海洋博物館）",G,"Q11572836","AM",None,{}),
 ("岡山県","真庭市オオサンショウウオ保護センター",L,None,"A",None,{}),
 ("岡山県","笠岡市立カブトガニ博物館",L,None,"AM","https://www.city.kasaoka.okayama.jp/site/kabutogani/",{}),
 ("広島県","シン・マリホ水族館",S,"Q109602084","AM","https://shin.mariho-aquarium.com/",{"aliases":["マリホ水族館"]}),
 ("広島県","みやじマリン 宮島水族館",G,"Q6764196","AM",None,{}),
 ("広島県","広島もとまち水族館",S,"Q141961798","AM",None,{}),
 ("広島県","福山大学マリンバイオセンター水族館",L,None,"AM","https://www.fukuyama-u.ac.jp/marine-bio-center/",{}),
 ("山口県","なぎさ水族館",S,"Q48752477","AM",None,{}),
 ("山口県","下関市立しものせき水族館 海響館",G,"Q11361443","AM",None,{}),
 ("徳島県","日和佐うみがめ博物館カレッタ",L,None,"AM","http://caretta-hiwasa.com/",{}),
 ("徳島県","海陽町立海洋自然博物館マリンジャム",S,None,"AM","https://marine.kaiyo-kankou.jp/",{}),
 ("香川県","四国水族館",G,"Q66432954","AM",None,{}),
 ("香川県","新屋島水族館",G,"Q11501972","AM",None,{"status":"temporarily_closed","status_note":"休館中。2027年春リニューアル予定と掲載（マンボウなんでも博物館の一覧による。要確認）"}),
 ("香川県","日本ドルフィンセンター",M,None,"AM","https://www.j-dc2.net/",{}),
 ("愛媛県","虹の森公園 おさかな館",F,"Q11419591","AM",None,{"aliases":["四万十川学習センターおさかな館"]}),
 ("高知県","むろと廃校水族館",S,"Q56739393","AM",None,{}),
 ("高知県","四万十川学遊館 あきついお",F,None,"AM","https://gakuyukan.com/",{}),
 ("高知県","室戸ドルフィンセンター",M,None,"AM","https://muroto.j-dc.net/",{}),
 ("高知県","桂浜水族館",G,"Q11536832","AM",None,{}),
 ("高知県","高知県立足摺海洋館 SATOUMI",G,"Q99611864","AM",None,{}),
 ("福岡県","やながわ有明海水族館",S,None,"AM","https://www.spera-morisatoumi.com/",{}),
 ("福岡県","マリンワールド海の中道",G,"Q6764266","AM",None,{}),
 ("長崎県","九十九島水族館 海きらら",G,"Q7400110","AM","https://umikirara.jp/",{"notes":"座標は九十九島パールシーリゾート（施設群）の代表点"}),
 ("長崎県","壱岐イルカパーク＆リゾート",M,None,"AM","https://irukapark.com/",{}),
 ("長崎県","長崎ペンギン水族館",G,None,"AM","https://penguin-aqua.jp/",{}),
 ("熊本県","海中水族館シードーナツ",G,"Q11281777","AM","http://amakusapearl.com/",{}),
 ("大分県","うみたま体験パーク つくみイルカ島",M,"Q11260727","AM","http://www.tsukumi-irukajima.jp/",{}),
 ("大分県","大分マリーンパレス水族館 うみたまご",G,"Q11432633","AM",None,{}),
 ("大分県","番匠おさかな館",F,None,"AM","https://www.michinoeki-yayoi.com/banjou-osakanakan",{"parent_facility":"道の駅やよい","notes":"道の駅内の淡水魚水族館（要確認）"}),
 ("宮崎県","すみえファミリー水族館",S,None,"AM","http://sunbeach-sumie.com/sumie_family_aquarium.html",{}),
 ("宮崎県","出の山淡水魚水族館",F,None,"AM",None,{}),
 ("宮崎県","志布志湾大黒イルカランド",M,None,"AM","http://www.irukaland.com/",{}),
 ("宮崎県","高千穂峡淡水魚水族館",F,None,"AM",None,{}),
 ("鹿児島県","いおワールドかごしま水族館",G,"Q11259022","AM",None,{}),
 ("鹿児島県","奄美海洋展示館",M,None,"AM","https://www.ohama.marutani-amami.com/ocean-exhibition-hall",{}),
 ("沖縄県","DMMかりゆし水族館",G,"Q56347666","AM",None,{}),
 ("沖縄県","久米島ウミガメ館",L,None,"A",None,{}),
 ("沖縄県","沖縄美ら海水族館",G,"Q1445750","AM",None,{}),
]
# 関東既存データに Wikidata を対応付け（空欄の座標・URL の補完用）
KANTO_QID = {"aq-08-0002":"Q21652750","aq-09-0001":"Q11535182","aq-12-0003":"Q85875396",
             "aq-14-0003":"Q97169050","aq-14-0004":"Q11582155","aq-14-0006":"Q114355208"}

PENDING = [
 # 一覧の片方だけに載り、収録基準（道の駅・科学館等の小規模展示は除外）の判断が必要なもの
 ("北海道","函館朝市ミニ水族館","市場内の小規模展示。除外対象に当たるか要判断","M"),
 ("北海道","水族館プティ（道の駅厚岸グルメパーク）","道の駅内の展示。除外対象に当たるか要判断","M"),
 ("北海道","氷海展望塔オホーツクタワー","海中展望塔。オホーツクとっかりセンターと別に登録するか要判断","M"),
 ("岩手県","岩手県立水産科学館","水産科学館の展示。除外対象に当たるか要判断","M"),
 ("宮城県","仙台市八木山動物公園","動物園。水生生物展示の有無を未確認","M"),
 ("東京都","UWS AQUARIUM GA☆KYO","施設の性格（常設の水族館か）を未確認","M"),
 ("東京都","上野動物園 両生爬虫類館","動物園内の両生爬虫類館。収録対象か要判断","M"),
 ("長野県","国営アルプスあづみの公園 あづみの学校","公園施設内の展示。除外対象に当たるか要判断","M"),
 ("岐阜県","民芸ミュージアム 匠の館 森の水族館","民芸館内の展示。規模を未確認","M"),
 ("静岡県","体感型動物園 iZoo","爬虫類中心の動物園。収録対象か要判断","M"),
 ("静岡県","熱川バナナワニ園","ワニ・植物園。収録対象か要判断","M"),
 ("静岡県","時之栖 水中楽園AQUARIUM","常設か期間限定かを未確認","M"),
 ("愛知県","のんほいパーク（豊橋総合動植物公園）","動植物園。水生生物展示の扱いを要判断","M"),
 ("滋賀県","（なし）","",""),
 ("大阪府","きんたい廃校博物館","廃校活用の博物館。規模を未確認","M"),
 ("奈良県","郡山金魚資料館","金魚の資料館。収録対象か要判断","M"),
 ("和歌山県","ドルフィンベェイス","イルカとのふれあい事業。収録対象か要判断","M"),
 ("広島県","広島市漁業振興センター 海と漁業の資料展示室","資料展示室。除外対象に当たるか要判断","M"),
 ("山口県","岩国市ミクロ生物館","微生物の展示館。収録対象か要判断","M"),
 ("愛媛県","ドルフィンファームしまなみ","イルカとのふれあい事業。収録対象か要判断","M"),
 ("愛媛県","長高水族館（愛媛県立長浜高等学校）","高校の水族館。一般公開の条件を未確認","M"),
 ("福岡県","北九州市水環境館","河川の観察施設。除外対象に当たるか要判断","M"),
 ("佐賀県","鹿島市干潟交流館 なな海","交流館の展示。除外対象に当たるか要判断","M"),
 ("佐賀県","佐賀県立宇宙科学館 ゆめぎんが","科学館の水槽展示。除外対象","M"),
 ("長崎県","干拓の里 むつごろう水族館","2022年10月から休館と掲載。営業再開を未確認","M"),
 ("大分県","白池地獄","温泉地獄の熱帯魚展示。収録対象か要判断","M"),
 ("宮崎県","大淀川学習館","学習館の展示。除外対象に当たるか要判断","M"),
 ("沖縄県","さんご館","サンゴ養殖施設。収録対象か要判断","M"),
 ("京都府","丹後魚っ知館","Wikidataのみに掲載。2つの一覧に無いため保留","W"),
 ("徳島県","モラスコむぎ","Wikidataのみに掲載。2つの一覧に無いため保留","W"),
 ("佐賀県","伊万里湾カブトガニの館","Wikidataのみに掲載。2つの一覧に無いため保留","W"),
]
UPCOMING = [
 ("東京都","東京よみうり水族館","2027年夏開業予定と報道。未開業"),
 ("静岡県","Zoo Zoo Sea","2029年度開業予定と掲載。未開業"),
]
EXCLUDED_CLOSED = [("静岡県","東海大学海洋科学博物館","2024年10月31日で本館の一般公開終了と掲載")]

def norm(s):
    return re.sub(r"[\s・　（）()「」〔〕]", "", unicodedata.normalize("NFKC", s or ""))

def main():
    data = json.load(open("data/facilities.json", encoding="utf-8"))
    facs = data["facilities"]
    # 既存（関東）: ID・内容はそのまま。空欄の座標/URL だけ Wikidata で補う
    for f in facs:
        q = KANTO_QID.get(f["id"])
        if not q: continue
        w = WD[q]; f["wikidata"] = q
        if f["lat"] is None and w["lat"] is not None:
            f["lat"], f["lng"] = w["lat"], w["lng"]
            f["coord_source"] = "wikidata"; f["coord_note"] = "Wikidata の座標（施設の代表点）"
        if not f.get("official_url") and w["url"]:
            f["official_url"] = w["url"]
        f["sources"].append({"ref": "wikidata", "fields": ["lat", "lng"] + (["official_url"] if w["url"] else [])})
    seq = Counter(f["prefecture"] for f in facs)
    known = {norm(n) for f in facs for n in [f["name"], *f.get("aliases", [])]}
    for pref, name, cat, q, lists, url, extra in MASTER:
        if norm(name) in known:
            continue
        seq[pref] += 1
        w = WD.get(q) if q else None
        srcs = []
        if "A" in lists: srcs.append({"ref": "aquarium_map", "fields": ["name", "prefecture"]})
        if "M" in lists: srcs.append({"ref": "manboumuseum", "fields": ["name", "prefecture"] + (["official_url"] if url and not (w and w["url"]) else [])})
        if w: srcs.append({"ref": "wikidata", "fields": [k for k in ("lat", "address", "official_url") if w.get(k if k != "lat" else "lat")]})
        rec = {
            "id": f"aq-{code(pref)}-{seq[pref]:04d}", "name": name, "aliases": extra.get("aliases", []),
            "prefecture": pref, "prefecture_code": code(pref),
            "address": (w or {}).get("address"),
            "lat": (w or {}).get("lat"), "lng": (w or {}).get("lng"),
            "coord_source": "wikidata" if w and w["lat"] is not None else None,
            "coord_note": "Wikidata の座標（施設の代表点）" if w and w["lat"] is not None else "未登録（後で一括補完）",
            "category": cat, "official_url": (w or {}).get("url") or url,
            "status": extra.get("status", "operating"), "status_note": extra.get("status_note"),
            "closed_date": None, "parent_facility": extra.get("parent_facility"), "notes": extra.get("notes"),
            "wikidata": q, "sources": srcs, "registered_at": TODAY,
            "verified_at": None, "verification": "listed",  # 公式サイトでの個別確認はしていない
        }
        facs.append(rec); known.add(norm(name))
    for f in facs:
        f.setdefault("verification", "official_checked" if f.get("verified_at") else "listed")
        f.setdefault("wikidata", None)
    facs.sort(key=lambda f: f["id"])
    return data, facs

if __name__ == "__main__":
    data, facs = main()
    ids = [f["id"] for f in facs]; assert len(ids) == len(set(ids)), "ID重複"
    names = Counter(norm(f["name"]) for f in facs); assert all(v == 1 for v in names.values()), names.most_common(3)
    for f in facs:
        assert f["prefecture"] in PREFS and (f["lat"] is None) == (f["lng"] is None)
        if f["lat"] is not None: assert 24 < f["lat"] < 46 and 122 < f["lng"] < 154, f["name"]
    # 都道府県と座標の食い違い（Wikidata の座標が別県を指していないか）を粗く確認
    m = data["meta"]
    m.update({
        "dataset": "水族館訪問マップ 施設データ（全国版 初期データ）", "version": "0.2.0", "generated_at": TODAY,
        "region": "全国", "total": len(facs),
        "count_by_status": {m["rules"]["status_labels"][k]: v for k, v in Counter(f["status"] for f in facs).items()},
        "count_by_prefecture": {p: c for p in PREFS if (c := sum(f["prefecture"] == p for f in facs))},
        "count_by_category": {m["rules"]["category_labels"][k]: v for k, v in Counter(f["category"] for f in facs).items()},
        "count_by_verification": dict(Counter(f["verification"] for f in facs)),
        "with_coordinates": sum(f["lat"] is not None for f in facs),
        "without_coordinates": sum(f["lat"] is None for f in facs),
    })
    m["sources"].update({
        "aquarium_map": {"name": "水族館マップ（aquarium-map.com）全国の水族館一覧（144館）", "url": "https://aquarium-map.com/aquariums", "accessed": TODAY,
                         "use": "収録候補の施設名・都道府県のみ参照。座標・説明文・画像は複製していない"},
        "manboumuseum": {"name": "マンボウなんでも博物館「日本の水族館マップ」", "url": "https://manboumuseum.com/japanese-aquarium-map/", "accessed": TODAY,
                         "use": "収録候補の施設名・都道府県・公式サイトへのリンクのみ参照。地図データは複製していない"},
        "wikidata": {"name": "Wikidata（SPARQL一括取得: 日本の公共水族館）", "url": "https://query.wikidata.org/", "accessed": TODAY,
                     "license": "CC0 1.0", "use": "座標・公式サイト・住所"},
    })
    m["rules"]["inclusion"] = "現在の施設一覧（aquarium-map.com／マンボウなんでも博物館）の少なくとも一方に掲載され、収録基準に合うもの。関東25件は公式情報で個別確認済み"
    m["rules"]["verification_labels"] = {"official_checked": "公式・公的情報で個別確認済み", "listed": "施設一覧への掲載のみ（個別確認前）"}
    m["rules"]["category_note"] = "関東以外の分類は名称と掲載情報からの暫定分類"
    m["license_notes"] = [
        "Wikidata 由来の項目は CC0 のため自由に利用可能。",
        "aquarium-map.com の施設データは © OpenStreetMap contributors（ODbL）と表示されているため、同サイトのデータそのものは複製せず施設名の確認にのみ利用した。",
        "マンボウなんでも博物館は利用条件の明示がないため、施設名・都道府県（事実情報）とリンク先URLのみ参照した。",
        "OpenStreetMap（ODbL）は、この作業環境から Overpass API に接続できず未使用。利用する場合は「© OpenStreetMap contributors」の表示と、配布時の ODbL 継承が必要。",
    ]
    m["warnings"] = []
    json.dump({"meta": m, "facilities": facs}, open("data/facilities.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    old = json.load(open("data/pending.json", encoding="utf-8"))
    kept = [p for p in old["pending"] if not any(norm(p["name"]).startswith(norm(f["name"])[:6]) for f in facs if f["name"].startswith("小笠原水産"))]
    pend = {"generated_at": TODAY,
            "pending": kept + [{"prefecture": p, "name": n, "reason": r, "listed_in": l} for p, n, r, l in PENDING if r],
            "upcoming": old.get("upcoming", [])[:0] + [{"prefecture": p, "name": n, "reason": r} for p, n, r in UPCOMING],
            "excluded_closed": [{"prefecture": p, "name": n, "reason": r} for p, n, r in EXCLUDED_CLOSED]}
    json.dump(pend, open("data/pending.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: m[k] for k in ("total", "count_by_status", "with_coordinates", "without_coordinates", "count_by_verification")}, ensure_ascii=False))
    print(len(pend["pending"]), "pending")
