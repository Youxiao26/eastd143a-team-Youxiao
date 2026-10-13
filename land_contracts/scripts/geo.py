import csv,re,json,collections,os
src=open('c2.py',encoding='utf-8').read()
exec(src.split('res={}')[0])
rows=list(csv.DictReader(open(os.path.join(os.environ.get('DATA_DIR','students_documents'),'items.csv'),encoding='utf-8-sig')))
meta={}
for r in rows: meta.setdefault(r['item_id'],r)
# county rules: (canonical, patterns)
C=[('闽侯（闽县/侯官/林森）',['閩侯','閩縣','閩邑','侯官','侯邑','林森','福州','Min Xian','Minhou','Houguan','Linsen','Min Yi','草市','白龍','西關外','嘉崇里','文山鋪','秋龍','橫街鋪','魁輔']),
('福清',['福清']),('古田',['古田']),('永安',['永安']),('永定',['永定']),('闽清',['閩清']),('建阳',['建陽']),
('永泰',['永泰','永福']),('屏南',['屏南']),('南平',['南平']),('晋江',['晉江','泉晉']),('连江',['連江']),('连城',['連城']),
('南安',['南安']),('东山',['東山']),('邵武',['邵武']),('顺昌',['順昌']),('安徽歙县',['歙縣']),('四川合川',['合川']),
('四川荣县',['榮縣']),('云南鹤庆',['鶴慶']),('辽宁新金',['新金']),('上海',['上海'])]
def county(t):
    for name,ps in C:
        if any(p in t for p in ps): return name
    return None
out=[]; src_count=collections.Counter()
for iid,b in items.items():
    m=meta[iid]; t=m['catalog_title']
    c=None
    if 'Place' in t:
        c=county(t.split('Place')[1]); 
        if c: src_count['catalog']+=1
    if not c:
        c=county(b[:3000])
        if c: src_count['text']+=1
    bb=b
    for x in boiler: bb=bb.replace(x,'')
    cats=[]
    for name,terms in T:
        if terms is None: hit=any(k in b for k in ['可耕地','非耕地'])
        else: hit=any(k in bb for k in terms)
        if hit: cats.append(name)
    big=sorted(set(x.split('·')[0] for x in cats))
    if '田' not in big and re.search(r'田契|田價|田地|種類 田|田畝|田一|一田|田壹|田土名',bb): big.append('田'); cats.append('田·未注明')
    y=re.match(r'\d{4}',m['date'] or '')
    out.append(dict(id=iid[5:],county=c or '未知',year=int(y.group()) if y else None,big=big,sub=cats,title=t))
json.dump(out,open('geo.json','w',encoding='utf-8'),ensure_ascii=False)
o=open('geo_sum.txt','w',encoding='utf-8')
o.write(str(src_count)+'\n')
cc=collections.Counter(x['county'] for x in out); o.write(str(cc.most_common())+'\n')
tab=collections.defaultdict(collections.Counter)
for x in out:
    for k in x['big']: tab[k][x['county']]+=1
for k,v in tab.items(): o.write(k+' '+str(v.most_common())+'\n')
