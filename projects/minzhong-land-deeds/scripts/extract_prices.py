# -*- coding: utf-8 -*-
"""閩中契約 · 貨幣與價格抽取

從 OCR（HTML，每件文書 1–N 頁）中抽出金額陳述，判定幣種與用途，
再與 chinese_land_records_235.csv 的 235 件主表對接。

    python3 scripts/extract_prices.py [OCR_DIR]

輸出至 docs/minzhong-land-deeds/data/：
    prices_mentions.csv   逐條金額（含原文脈絡，可覆核）
    prices_records.csv    逐件主價格
    prices.json           兩者合一 + 統計摘要
"""
import os, re, sys, csv, json, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DATA = os.path.join(REPO, 'docs', 'minzhong-land-deeds', 'data')
OCR_DEFAULT = os.path.abspath(os.path.join(REPO, '..', 'students_documents', 'OCR_results'))

# ---------------------------------------------------------------- 數字解析
DIG = {'〇':0,'零':0,'0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
       '一':1,'壹':1,'二':2,'貳':2,'弍':2,'两':2,'三':3,'叁':3,'參':3,'四':4,'肆':4,
       '五':5,'伍':5,'六':6,'陸':6,'七':7,'柒':7,'八':8,'捌':8,'九':9,'玖':9}
MUL = {'十':10,'拾':10,'百':100,'佰':100,'千':1000,'仟':1000}
NUMCH  = ''.join(sorted(set(list(DIG) + list(MUL) + ['萬', '万'])))
NUMCLS = '[' + re.escape(NUMCH) + ']'

def cn2num(s):
    """中文數字（含大寫）→ float；無法解析回 None。"""
    if not s:
        return None
    if re.fullmatch(r'[0-9]+', s):
        return float(s)
    total, section, cur, seen = 0, 0, None, False
    for ch in s:
        if ch in DIG:
            cur = DIG[ch] if cur is None else cur * 10 + DIG[ch]
            seen = True
        elif ch in MUL:
            section += (1 if cur is None else cur) * MUL[ch]
            cur = None; seen = True
        elif ch in ('萬', '万'):
            section += (cur or 0)
            total += (section if section else 1) * 10000
            section, cur, seen = 0, None, True
        else:
            return None
    return float(total + section + (cur or 0)) if seen else None

def cash2num(s):
    """錢文專用：「壹百壹拾伍千」＝115 千文；「肆拾壹千陸百」＝41,600 文。
    以最後一個千／仟切分，左段為「千文」之數，右段為零頭。"""
    i = max(s.rfind('千'), s.rfind('仟'))
    if i < 0:
        return cn2num(s)
    left, right = cn2num(s[:i]) if i else 1.0, cn2num(s[i+1:]) if i+1 < len(s) else 0.0
    if left is None or right is None:
        return cn2num(s)
    return left * 1000 + right

# ---------------------------------------------------------------- 單位
UNITS   = ['千文','兩','两','錢','分','厘','釐','元','員','圓','文','角','毫','貫']
UNIT_RE = '(?:' + '|'.join(UNITS) + ')'
RUN_RE  = re.compile(r'(?:' + NUMCLS + r'+' + UNIT_RE + r')+')
PAIR_RE = re.compile('(' + NUMCLS + r'+)(' + UNIT_RE + ')')

TAEL   = {'兩':1, '两':1, '錢':0.1, '分':0.01, '厘':0.001, '釐':0.001}
DOLLAR = {'元':1, '員':1, '圓':1, '角':0.1, '毫':0.1, '分':0.01, '厘':0.001, '釐':0.001}
CASH   = {'貫':1000, '千文':1000, '文':1}

def parse_run(run):
    """→ (值, 幣種族, 基本單位) 或 None。"""
    pairs = PAIR_RE.findall(run)
    us = {u for _, u in pairs}
    if us & {'兩', '两'}:
        fam, scale, label = 'tael', TAEL, '兩'
    elif us & {'元', '員', '圓'}:
        fam, scale, label = 'dollar', DOLLAR, '元'
    elif us & {'文', '千文', '貫'}:
        fam, scale, label = 'cash', CASH, '文'
    else:
        return None
    total = 0.0
    for num, u in pairs:
        if u not in scale:
            return None
        if fam == 'cash' and u == '文':
            v = cash2num(num)          # 「…千…文」的虛位千
        else:
            v = cn2num(num)
            if fam == 'cash' and u == '千文':
                v = v if v is not None else None
        if v is None:
            return None
        total += v * (1 if (fam == 'cash' and u == '文') else scale[u])
    return (round(total, 4), fam, label)

# ---------------------------------------------------------------- 文本清理
OCRFIX = str.maketrans({'壺':'壹', '壼':'壹', '式':'貳', '弍':'貳', '陌':'佰', '阡':'仟'})

def load_text(fp):
    s = open(fp, encoding='utf-8', errors='replace').read()
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', html.unescape(s))

def collapse(s):
    """壓掉 OCR 的退化重複（同一短語連印數十次）。"""
    return re.sub(r'(.{4,40}?)\1{3,}', r'\1', s)

# ---------------------------------------------------------------- 分類
CUES = [
    (r'每[兩两員元圓斤石張畝坪號]|折[錢銀]|作[錢銀]|類推|加收', 'rate'),
    (r'紙價|契紙費|工本費|驗契費|註冊費|附加|附捐|印花|手續費|罰金|'
     r'中用|中書|中見|外中|中銀|謝中|書禮|酒席錢|處以', 'fee'),
    (r'稅額|契稅|稅銀|納稅|完糧|糧錢|錢糧|正課|課銀|稅率|徵收|正耗|地丁|漕|'
     r'應納|稅價|正稅|實收.{0,2}稅', 'tax'),
    (r'地租|租谷|租穀|納租|租錢|佃租|禾租|租金|厝租|山租|租伐|月租', 'rent'),
    (r'增找|找洗|杜斷|湊斷|增我|找價|找出|貼|外加|修理|加添', 'price_supplement'),
    (r'借出|借入|出借|本利|利息|借錢|借銀', 'loan'),
    (r'典價|典得|典與|典出|典銀|典受|當價|抵', 'price_pawn'),
    (r'產價|契價|價銀|價洋|價錢|原價|中銀|申銀|時值|估價|斷價|本錢|面錢|銀水|'
     r'合共|共成|共計|金額|甘出|出價|得價|價|契內銀|內銀|錢票', 'price_sale'),
    (r'賣|買|承受|成交|承買|承典', 'price_sale'),
]
# 幣名本身不說明用途，僅在無其他線索時作最後依據
FALLBACK = re.compile(r'人民幣|國幣|法幣|金圓|洋銀|大銀|實銀|出銀|交銀|收銀|幣')
CUE_RE = [(re.compile(p), c) for p, c in CUES]

BOILER = re.compile(r'條例|辦法|罰金|逾限|凡屬|稅率|摘要|政務會議|佈告|通令|訓令|'
                    r'第[一二三四五六七八九十]+條|以上.{0,4}以下|等因奉此|奉此|'
                    r'徵收方法|定章|每張收|依此類推')

QUAL = ['紋銀','紋廣','庫平','番銀','佛銀','大洋','光洋','龍洋','國幣','法幣','人民幣',
        '銀元','銀圓','銅錢','銅元','足色','足錢','庫錠','庫錫','大錠','九四','九七',
        '星色','平戥','台伏','洋銀','鷹洋']

def classify(pre, post=''):
    """取語境中結束位置最靠後、最長的線索詞；贖回由下文判定。"""
    if re.search(r'每[兩两員元圓石斤].{0,4}$|折\s*[錢銀鈔].{0,2}$|折成$', pre):
        return 'rate'                       # 折算率優先於下文的贖回語
    if re.search(r'取贖|回贖|聽贖', post):
        return 'redemption'
    best, cat = (-1, -1), None
    for rx, c in CUE_RE:
        for m in rx.finditer(pre):
            key = (m.end(), m.end() - m.start())
            if key > best:
                best, cat = key, c
    if cat:
        return cat
    return 'price_sale' if FALLBACK.search(pre) else 'other'

BAD_NUM = re.compile('[' + re.escape(''.join(k for k, v in DIG.items() if v)) + ']{2}')
STOP_BEFORE = re.compile(r'[畝坵丘號都圖甲年月日第戶坪斤石斗)]$')
MONEY_KW    = re.compile(r'[價銀錢洋幣稅費租佃贖找貼當典賣買納繳交收糧課算折每]')

def extract(text):
    out = []
    for m in RUN_RE.finditer(text):
        run = m.group(0)
        if not re.search(r'[兩两元員圓文貫]', run):
            continue                                   # 需有確定的貨幣單位
        pre  = text[max(0, m.start() - 30):m.start()]
        post = text[m.end():m.end() + 12]
        if STOP_BEFORE.search(pre[-1:]):
            continue                                   # 面積／編號／日期
        if not MONEY_KW.search(pre[-14:]):
            continue
        if re.match(r'\s*[尺丈寸坪畝坵斤]', post):
            continue                                   # 緊接丈量單位，非金額
        parsed = parse_run(run)
        if not parsed:
            continue
        value, fam, money_unit = parsed
        if value <= 0:
            continue
        out.append(dict(
            raw=run, value=value, family=fam, unit_label=money_unit,
            category=classify(pre[-20:], post),
            currency='|'.join(q for q in QUAL if q in pre[-18:] or q in post),
            scope='regulation' if BOILER.search(pre + run + post) else 'deed',
            confidence='low' if BAD_NUM.search(run) else 'ok',
            context=(pre[-24:] + '【' + run + '】' + post).strip(),
        ))
    return out

# ---------------------------------------------------------------- 主流程
PRICE_CATS = ('price_sale', 'price_pawn', 'price_supplement')

DEED_TYPES = [
    ('division',   r'鬮書|鬮分|分關|分家|闔族|長房.{0,6}次房'),
    ('supplement', r'增找|找洗|杜斷|湊斷|找價|絕賣杜斷'),
    ('pawn',       r'典契|立典|典與|轉典|當契|典出'),
    ('lease',      r'佃批|租約|招佃|批耕'),
    ('sale',       r'賣斷|絕賣|立賣|賣契|杜賣'),
    ('taxdoc',     r'契尾|驗契|稅單|執照|契證|串票|完糧執照|契稅申報'),
]
DEED_RE = [(t, re.compile(p)) for t, p in DEED_TYPES]

def deed_type(text):
    hits = [t for t, rx in DEED_RE if rx.search(text)]
    return hits[0] if hits else ''

def main():
    ocr_dir = sys.argv[1] if len(sys.argv) > 1 else OCR_DEFAULT
    pages = collections.defaultdict(list)
    for f in sorted(os.listdir(ocr_dir)):
        m = re.match(r'(\d+)_(\d+)\.html$', f)
        if m:
            pages[m.group(1)].append(f)

    with open(os.path.join(DATA, 'chinese_land_records_235.csv'), encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))

    mentions, records = [], []
    for r in rows:
        key = r['pid'].split(':')[-1]
        rec = dict(nid=r['nid'], pid=r['pid'], year_start=r['year_start'], year_end=r['year_end'],
                   nature=r['nature'], unit=r['unit'], place_cjk=r['place_cjk'],
                   is_lease=r['is_lease'], ocr_pages=len(pages.get(key, [])))
        mine, dtypes = [], []
        for f in pages.get(key, []):
            text = collapse(load_text(os.path.join(ocr_dir, f))).translate(OCRFIX)
            dt = deed_type(text)
            if dt:
                dtypes.append(dt)
            for i, mt in enumerate(extract(text)):
                mt.update(nid=r['nid'], pid=r['pid'], page=f, seq=i,
                          year_start=r['year_start'], nature=r['nature'], unit=r['unit'])
                mine.append(mt)
        mentions += mine

        deed = [m for m in mine if m['scope'] == 'deed' and m['category'] in PRICE_CATS]
        if any(m['confidence'] == 'ok' for m in deed):
            deed = [m for m in deed if m['confidence'] == 'ok']
        rec['deed_type'] = dtypes[0] if dtypes else ''
        rec['n_mentions'] = len(mine)
        rec['n_price_mentions'] = len(deed)
        if deed:
            fams = collections.Counter(m['family'] for m in deed)
            fam = fams.most_common(1)[0][0]
            same = [m for m in deed if m['family'] == fam]
            cnt = collections.Counter(m['value'] for m in same)
            top = max(cnt.items(), key=lambda kv: (kv[1], kv[0]))   # 複述最多者；同票取大
            best = next(m for m in same if m['value'] == top[0])
            rec.update(price_value=top[0], price_family=fam, price_unit=best['unit_label'],
                       price_category=best['category'], price_currency=best['currency'],
                       price_raw=best['raw'], price_context=best['context'],
                       price_repeats=top[1], price_confidence=best['confidence'],
                       price_values_all='|'.join(str(v) for v in sorted(cnt)))
        else:
            rec.update(price_value='', price_family='', price_unit='', price_category='',
                       price_currency='', price_raw='', price_context='', price_repeats='',
                       price_confidence='',
                       price_values_all='')
        records.append(rec)

    os.makedirs(DATA, exist_ok=True)
    mcols = ['nid','pid','page','seq','year_start','nature','county','category','scope',
             'confidence','family','value','money_unit','currency','raw','context']
    with open(os.path.join(DATA, 'prices_mentions.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, mcols); w.writeheader()
        for m in mentions:
            w.writerow({'county': m['unit'], 'money_unit': m['unit_label'],
                        **{c: m.get(c, '') for c in mcols if c not in ('county', 'money_unit')}})

    with open(os.path.join(DATA, 'prices_records.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, list(records[0].keys())); w.writeheader(); w.writerows(records)

    with open(os.path.join(DATA, 'prices.json'), 'w', encoding='utf-8') as fh:
        json.dump(dict(mentions=mentions, records=records), fh, ensure_ascii=False, indent=1)

    priced = [r for r in records if r['price_value'] != '']
    print('文書 %d 件，OCR 覆蓋 %d 件' % (len(records), sum(1 for r in records if r['ocr_pages'])))
    print('金額陳述 %d 條；可定主價格 %d 件' % (len(mentions), len(priced)))
    print(collections.Counter(m['category'] for m in mentions).most_common())
    print(collections.Counter(r['price_family'] for r in priced).most_common())

if __name__ == '__main__':
    main()
