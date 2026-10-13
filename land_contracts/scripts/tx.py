import re, json, collections
txt = open('all.txt', encoding='utf-8').read()
items = collections.OrderedDict()
for blk in txt.split('### ')[1:]:
    head, _, body = blk.partition('\n'); iid = head.split()[0]
    items.setdefault(iid, ''); items[iid] += ' ' + body
geo = {('pitt:' + x['id']): x for x in json.load(open('geo.json', encoding='utf-8'))}

# 契尾、税单等印刷套话与契约常见的否定套语，先去掉再判定
NOISE = ['買主或承典人','賣主或出典人','賣主與買主或','出典人與承典人','賣契稅','典契稅','買賣契','典契時','或典契','買契或','承典人須','出典人赴','出典人請領','出典人須','典契遺失','出典人另書典','出典人不得拒','出典人尚在','買主或出典人','賣主、買主、','出典人書立','賣主或','或出典人','承典人分擔','典契照產價','賣契照產價','賣契本契','買賣田產', '田房稅契', '重典', '典賣', '典掛', '典當他人', '典當', '重張典', '重復典', '重複典', '典借',
         '田園屋地各類不動產', '買賣典當', '買賣或', '之買賣', '買賣田房', '土地房屋之', '賣買田產']
TX = [
 ('卖（卖断/杜卖/绝卖）', r'賣斷|斷賣|杜賣|賣盡|盡賣|立賣|賣契|賣與|賣出|出賣|賣新|新賣|分賣|買受|買斷|賣價|價賣|賣主|賣田|賣山|賣屋'),
 ('典（典当/胎押）',     r'典契|立典|典與|典出|典受|典斷|繳典|出典|承典|曲契|胎押|典價|當山契|典田|典屋|典得|撥典'),
 ('找价/凑断（加价）',   r'找價|增找|湊斷|湊與|湊價|加找|說找|找人|湊字|找契|找洗|找貼'),
 ('赠送',               r'送字|送斷|送友|送入|送賣|送與'),
 ('分家/阄分',           r'拈閭|拈鬮|鬮書|鬮分為定|分立|抽養膳|長子長孫份下|房份下'),
 ('租佃/借用',           r'租票|收票|憑票支|山租錢|借厝|借過|佃田賣|租金'),
 ('合约/公约',           r'合約字|公約字|立合約'),
]
OFFICIAL = r'契尾|執照|驗契|易知單|田賦|所有證|陳報|契稅|收據|稅契|管業'
LAND = ["田", "房屋", "地基/屋地/空地", "山", "園", "墳地/墓穴", "池/塘", "蕩地", "土改證"]

rows = []
for iid, b in items.items():
    bb = b
    for n in NOISE: bb = bb.replace(n, '')
    tx = [name for name, pat in TX if re.search(pat, bb)]
    if not tx:
        tx = ['仅官方凭证（契尾/税单/执照等）'] if re.search(OFFICIAL, b) or b.strip() else ['无法判定']
        if not b.strip(): tx = ['无法判定']
    rows.append(dict(id=iid[5:], land=geo[iid]['big'], tx=tx, year=geo[iid]['year'], county=geo[iid]['county']))

json.dump(rows, open('tx.json', 'w', encoding='utf-8'), ensure_ascii=False)
names = [n for n, _ in TX] + ['仅官方凭证（契尾/税单/执照等）', '无法判定']
o = open('tx_out.txt', 'w', encoding='utf-8')
o.write('TOTAL ' + str(collections.Counter(t for r in rows for t in r['tx'])) + '\n')
for L in LAND + ['(未归类土地)']:
    sub = [r for r in rows if (L in r['land'] if L != '(未归类土地)' else not r['land'])]
    c = collections.Counter(t for r in sub for t in r['tx'])
    o.write(f"{L}\t{len(sub)}\t" + '\t'.join(f"{n}:{c[n]}" for n in names if c[n]) + '\n')
# 交易方式组合
o.write(str(collections.Counter('+'.join(r['tx']) for r in rows).most_common(15)) + '\n')
