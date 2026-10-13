import re, json, collections
txt = open('all.txt', encoding='utf-8').read()
items = collections.OrderedDict()
for blk in txt.split('### ')[1:]:
    head, _, body = blk.partition('\n'); iid = head.split()[0]
    items.setdefault(iid, ''); items[iid] += ' ' + body
tx = {('pitt:' + r['id']): r for r in json.load(open('tx.json', encoding='utf-8'))}

N = '[〇零○一壹壺乙二貳贰式弍三參叁四肆五伍六陸陆七柒八捌九玖十拾百佰千仟萬万半0-9]+'
# (组, 单位名, 正则)
UNITS = [
 ('面积', '亩（畝）',            rf'{N}\s*[畝亩]'),
 ('面积', '分／厘（亩以下）',     rf'{N}\s*分\s*{N}?\s*[厘釐毫]|[畝亩]\s*{N}\s*分'),
 ('面积', '丈／尺（长宽）',       rf'{N}\s*丈|{N}\s*尺'),
 ('面积', '市亩（土改后）',       r'市畝|市亩'),
 ('产量与税粮', '受种（石斗升）', rf'受\s*種[^。]{{0,6}}?{N}\s*[石斗升合畝]'),
 ('产量与税粮', '租额（斤／石／箩／斛）', rf'(?:租|租谷|租穀|租米|禾租|面租)[^。]{{0,8}}?{N}\s*[斤觔石斗升籮羅斛秤]'),
 ('产量与税粮', '载粮／苗米',     rf'(?:糧|粮|苗米|載民|載畝)[^。]{{0,6}}?{N}\s*[畝分石斗升合]'),
 ('块数与编号', '坵（丘）',        rf'{N}\s*[坵丘]'),
 ('块数与编号', '号（田号）',      rf'(?:田|園|山)[^。第]{{0,6}}?{N}\s*[號号]'),
 ('块数与编号', '段',             rf'(?<!第){N}\s*段'),
 ('块数与编号', '片',             rf'{N}\s*片'),
 ('块数与编号', '所',             rf'{N}\s*所'),
 ('块数与编号', '块',             rf'{N}\s*[塊块]'),
 ('块数与编号', '穴（墓穴）',      rf'{N}\s*穴'),
 ('块数与编号', '口（池、井）',     rf'池\s*{N}\s*口|{N}\s*口池'),
 ('房屋构件', '柱',               rf'{N}\s*柱'),
 ('房屋构件', '栏（欄）',          rf'{N}\s*[欄櫚棚]'),
 ('房屋构件', '堵',               rf'{N}\s*堵'),
 ('房屋构件', '间',               rf'{N}\s*[間间]'),
 ('房屋构件', '座',               rf'{N}\s*座'),
 ('房屋构件', '进',               rf'{N}\s*進'),
 ('价格', '两（银两）',           rf'{N}\s*兩\s*正|銀[^。]{{0,8}}?{N}\s*兩'),
 ('价格', '文／千文（铜钱）',      rf'{N}\s*[千仟]\s*文|錢[^。]{{0,6}}?{N}\s*文'),
 ('价格', '元／员（银元、法币、人民币）', rf'{N}\s*[員元圓](?!年|月)'),
]
NOISE = ['柱易知','田園屋地各類不動產', '畝 分 厘', '畝分', '分則']
LAND = ["田", "房屋", "地基/屋地/空地", "山", "園", "墳地/墓穴", "池/塘", "蕩地", "土改證"]
docs = []
for iid, b in items.items():
    bb = b
    for n in NOISE: bb = bb.replace(n, ' ')
    hits = {}
    for g, name, pat in UNITS:
        m = re.search(pat, bb)
        if m:
            s = max(0, m.start() - 8); hits[name] = bb[s:m.end() + 2].strip()
    r = tx[iid]
    docs.append(dict(id=r['id'], land=r['land'], tx=r['tx'], year=r['year'], county=r['county'], units=hits))
json.dump(dict(units=[[g, n] for g, n, _ in UNITS], docs=docs), open('units.json', 'w', encoding='utf-8'), ensure_ascii=False)
o = open('units_out.txt', 'w', encoding='utf-8')
for L in LAND:
    sub = [d for d in docs if L in d['land']]
    o.write(f"\n## {L} ({len(sub)})\n")
    for g, name, _ in UNITS:
        hs = [d for d in sub if name in d['units']]
        if hs: o.write(f"  {name}: {len(hs)}  e.g. {hs[0]['units'][name]} | {hs[-1]['units'][name]}\n")
