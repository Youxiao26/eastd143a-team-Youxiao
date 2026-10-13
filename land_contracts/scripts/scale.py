import re, json, collections
txt = open('all.txt', encoding='utf-8').read()
items = collections.OrderedDict()
for blk in txt.split('### ')[1:]:
    head, _, body = blk.partition('\n'); iid = head.split()[0]
    items.setdefault(iid, ''); items[iid] += ' ' + body
tx = {('pitt:' + r['id']): r for r in json.load(open('tx.json', encoding='utf-8'))}

D = {'〇':0,'零':0,'○':0,'一':1,'壹':1,'壺':1,'乙':1,'二':2,'貳':2,'贰':2,'式':2,'弍':2,'兩':2,'三':3,'參':3,'叁':3,'參':3,'四':4,'肆':4,'五':5,'伍':5,'六':6,'陸':6,'陆':6,'七':7,'柒':7,'八':8,'捌':8,'九':9,'玖':9}
U = {'十':10,'拾':10,'百':100,'佰':100,'千':1000,'仟':1000,'萬':10000,'万':10000}
NUMC = '〇零○一壹壺乙二貳贰式弍三參叁四肆五伍六陸陆七柒八捌九玖十拾百佰千仟萬万0-9'
def cn2n(s):
    if re.fullmatch(r'[0-9]+', s): return int(s)
    total, sec, cur = 0, 0, None
    for ch in s:
        if ch in D: cur = D[ch] if cur is None else cur*10 + D[ch]
        elif ch.isdigit(): cur = int(ch) if cur is None else cur*10 + int(ch)
        elif ch in U:
            u = U[ch]
            if u == 10000: total += (sec + (cur or 0)) * u; sec = 0
            else: sec += (1 if cur is None else cur) * u
            cur = None
    return total + sec + (cur or 0) or None

N = f'[{NUMC}]+'
# 价格：只在“价”字附近找，按币种分开
PRICE = [
  ('银两',   re.compile(rf'價[^。]{{0,8}}?銀[^。]{{0,6}}?({N})兩')),
  ('铜钱（千文）', re.compile(rf'價[^。]{{0,6}}?錢[^。]{{0,4}}?({N})[仟千]文')),
  ('铜钱（千文）', re.compile(rf'價[^。]{{0,6}}?({N})[仟千]文')),
  ('人民币（元）', re.compile(rf'人民幣[^。]{{0,4}}?({N})[員元圓萬]')),
  ('法币/国币（元）', re.compile(rf'(?:法幣|國幣|國帶|國弊)[^。]{{0,4}}?({N})[員元圓]')),
  ('银元（元）', re.compile(rf'價[^。]{{0,8}}?(?:大洋|小洋|洋|台伏|番|伏|銀|錢)?[^。]{{0,4}}?({N})[員元圓](?!年)')),
  ('银元（元）', re.compile(rf'(?:大洋|台伏|番銀)({N})[員元圓]')),
]
# 面积：X畝X分X厘
AREA = re.compile(rf'({N})?[畝亩]({N})?[分]?(?:({N})[厘釐])?')
def area(b):
    best = None
    for m in re.finditer(rf'(?:官丈|官文|計|面積|田|地|共|丈|載)?\s*({N})\s*[畝亩]\s*(?:({N})\s*分)?\s*(?:({N})\s*[厘釐])?', b):
        a = cn2n(m.group(1));
        if a is None: continue
        f = cn2n(m.group(2)) if m.group(2) else 0
        l = cn2n(m.group(3)) if m.group(3) else 0
        v = a + (f or 0)/10 + (l or 0)/100
        ctx = b[max(0,m.start()-6):m.start()]
        if '租' in ctx or '穀' in ctx or '谷' in ctx: continue
        if 0 < v <= 60: best = best or v
    if best is None:  # 只写“X分X厘”的小块宅地
        m = re.search(rf'零\s*[畝亩]\s*({N})\s*分\s*(?:({N})\s*[厘釐])?', b)
        if m:
            v = (cn2n(m.group(1)) or 0)/10 + ((cn2n(m.group(2)) or 0)/100 if m.group(2) else 0)
            if v > 0: best = v
    return best

out = []
for iid, b in items.items():
    r = tx[iid]
    price = None
    for cur, pat in PRICE:
        for m in pat.finditer(b):
            v = cn2n(m.group(1))
            if v and v > 0:
                price = (cur, v); break
        if price: break
    out.append(dict(id=r['id'], land=r['land'], tx=r['tx'], year=r['year'], county=r['county'],
                    cur=price[0] if price else None, price=price[1] if price else None, mu=area(b)))
json.dump(out, open('scale.json', 'w', encoding='utf-8'), ensure_ascii=False)
o = open('scale_out.txt', 'w', encoding='utf-8')
o.write('price found %d, area found %d\n' % (sum(1 for x in out if x['price']), sum(1 for x in out if x['mu'])))
o.write(str(collections.Counter(x['cur'] for x in out)) + '\n')
for x in out:
    if x['price'] or x['mu']:
        o.write(f"{x['id']} {x['year']} {x['land']} {x['tx'][:1]} {x['cur']} {x['price']} mu={x['mu']}\n")
