import re, json, collections
exec(open('scale.py', encoding='utf-8').read().split('# 价格')[0])
CAND = re.compile(rf'(價|值|價錢|價銀)([^。]{{0,14}}?)({N})\s*(兩|[仟千]\s*文|[員元圓])(.{{0,2}})')
def price(b):
    best = None
    for m in CAND.finditer(b):
        pre = b[max(0, m.start()-8):m.start()] + m.group(2)
        if re.search(r'稅|費|印花|每|折|賦|罰', pre): continue
        v = cn2n(m.group(3))
        if not v: continue
        u = m.group(4)
        if u == '兩': cur = '银两'
        elif '文' in u: cur = '铜钱（千文）'
        elif re.search(r'人民幣', pre): cur = '人民币（元）'
        elif re.search(r'法幣|國幣|國帶|國弊', pre): cur = '法币/国币（元）'
        else: cur = '银元（元）'
        score = (2 if '正' in m.group(5) else 0) + (1 if re.search(r'價', m.group(1)) else 0)
        if best is None or score > best[0]: best = (score, cur, v)
    return best
def area2(b):
    for m in re.finditer(rf'({N})\s*[畝亩]\s*(?:({N})\s*分)?\s*(?:({N})\s*[厘釐])?', b):
        ctx = b[max(0, m.start()-8):m.start()]
        if re.search(r'租|穀|谷|受\s*種|種', ctx): continue
        a = cn2n(m.group(1))
        if a is None: continue
        v = a + ((cn2n(m.group(2)) or 0) if m.group(2) else 0)/10 + ((cn2n(m.group(3)) or 0)/100 if m.group(3) else 0)
        if 0 < v <= 60: return round(v, 3)
    m = re.search(rf'零\s*[畝亩]\s*({N})\s*分\s*(?:({N})\s*[厘釐])?', b)
    if m:
        v = (cn2n(m.group(1)) or 0)/10 + (((cn2n(m.group(2)) or 0) if m.group(2) else 0)/100 if m.group(2) else 0)
        if v > 0: return round(v, 3)
    return None
out = []
for iid, b in items.items():
    r = tx[iid]; p = price(b)
    out.append(dict(id=r['id'], land=r['land'], tx=r['tx'], year=r['year'], county=r['county'],
                    cur=p[1] if p else None, price=p[2] if p else None, mu=area2(b)))
json.dump(out, open('scale.json', 'w', encoding='utf-8'), ensure_ascii=False)
o = open('scale_out.txt', 'w', encoding='utf-8')
o.write('price %d area %d\n' % (sum(1 for x in out if x['price']), sum(1 for x in out if x['mu'])))
o.write(str(collections.Counter(x['cur'] for x in out)) + '\n')
for x in out:
    if x['price'] or x['mu']:
        o.write(f"{x['id'][-6:]} {x['year']} {'/'.join(x['land'])} {x['tx'][0][:2]} {x['cur']} {x['price']} mu={x['mu']}\n")
