import csv,re,sys,os,html
base=sys.argv[1]; out=sys.argv[2]
rows=list(csv.DictReader(open(os.path.join(base,'items.csv'),encoding='utf-8-sig')))
with open(out,'w',encoding='utf-8') as f:
    for r in rows:
        fn=os.path.join(base,'OCR_results',os.path.basename(r['image_file']).replace('.jpg','.html'))
        t=open(fn,encoding='utf-8').read() if os.path.exists(fn) else ''
        t=re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>',r'[IMG:\1]',t)
        t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
        f.write(f"### {r['item_id']} p{r['page']} | {r['date']} | {r['catalog_title']}\n{t}\n\n")
