#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从分析结果生成静态站点 index.html。"""
import json, os, sys, html, collections

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(REPO, "docs", "data")
L = lambda f: json.load(open(os.path.join(P, f), encoding="utf-8"))
recs   = L("records.json");      ents  = L("entities.json")
norm   = L("county_normalization.json"); st = L("spacetime.json")
ts     = L("timeseries.json");   per   = L("period_summary.json")
comps  = L("network_components.json");   lin = L("lineage_clusters.json")
net    = L("network.json")
e = lambda s: html.escape(str(s), quote=True)

# ---------- 调色板（已通过 validate_palette.py 六项检查）----------
C = {"gov":"var(--series-1)","per":"var(--series-2)"}

# ---------- 统计 ----------
n_docs  = len(recs)
yrs     = [int(r["year_start"]) for r in recs if r["year_start"]]
n_units = len(st["rows"])
persons = [n for n in net["nodes"] if n["type"]=="person"]
women   = [n for n in net["nodes"] if n["type"]=="woman"]
insts   = [n for n in net["nodes"] if n["type"] in ("institution","government")]
geo     = collections.Counter(r["geo_status"] for r in recs)
raw_places = len({r["place_cjk"] for r in recs if r["place_cjk"]})

def tip(t):  # tooltip 属性
    return f'tabindex="0" data-tip="{e(t)}"'

# ================= 1. 县名归并 =================
pre = collections.Counter()
for r in recs:
    if r["place_cjk"]: pre[r["place_cjk"]] += 1
merge_unit = next(u for u in norm["units"] if u["unit_id"]=="minhou")
minhou_pre = [(v, pre.get(v,0)) for v in merge_unit["variants"] if pre.get(v,0)]
minhou_pre.sort(key=lambda x:-x[1])
minhou_total = st["rows"][0]["total"]

merge_rows = []
for u in norm["units"]:
    vs = [(v,pre.get(v,0)) for v in u["variants"] if pre.get(v,0)]
    if not vs: continue
    vs.sort(key=lambda x:-x[1])
    row = next((r for r in st["rows"] if r["unit_id"]==u["unit_id"]), None)
    merge_rows.append({"unit":u["unit"],"modern":u["modern"],"note":u["note"],
                       "variants":vs,"total":row["total"] if row else sum(v[1] for v in vs)})
merge_rows.sort(key=lambda r:-r["total"])

# ================= 2. 时空热力图 =================
MAXC = max(c for r in st["rows"] for c in r["cells"]) or 1
RAMP = ["#eef4fd","#cde2fb","#9ec5f4","#6da7ec","#3987e5","#256abf","#104281"]
def ramp(v):
    if v==0: return "var(--cell-zero)"
    i = min(len(RAMP)-1, 1+int((len(RAMP)-2) * (v/MAXC)**0.55))
    return RAMP[i]
def ink(v):
    return "#ffffff" if v/MAXC > 0.42 else "var(--text-primary)"

# ================= 3. 官契/民契 =================
dec = [d for d in ts if d["total"]>0]
MAXD = max(d["government"]+d["personal"] for d in dec) or 1

# ---------- SVG：官契/民契 分年代堆叠柱 ----------
BW, GAP, H, PAD = 26, 8, 300, 46
w_bars = len(dec)*(BW+GAP)
svg_w  = w_bars + PAD + 24
def bars_svg():
    out=[f'<svg viewBox="0 0 {svg_w} {H+54}" role="img" aria-label="各年代官契与民契件数堆叠柱状图" class="chart">']
    for gy in range(0, MAXD+1, 10):
        y = H - gy/MAXD*(H-20)
        out.append(f'<line class="grid" x1="{PAD}" y1="{y:.1f}" x2="{svg_w-10}" y2="{y:.1f}"/>')
        out.append(f'<text class="ax" x="{PAD-8}" y="{y+4:.1f}" text-anchor="end">{gy}</text>')
    for i,d in enumerate(dec):
        x = PAD + i*(BW+GAP)
        tot = d["government"]+d["personal"]
        hg = d["government"]/MAXD*(H-20); hp = d["personal"]/MAXD*(H-20)
        yg = H-hg; yp = yg-hp-(2 if (hg>0 and hp>0) else 0)   # 2px 间隔
        t = f'{d["decade"]}年代　官契 {d["government"]}　民契 {d["personal"]}　共 {tot}'
        out.append(f'<g class="bar" {tip(t)}>')
        out.append(f'<rect class="hit" x="{x-GAP/2:.1f}" y="0" width="{BW+GAP}" height="{H}"/>')
        if hg>0: out.append(f'<rect x="{x}" y="{yg:.1f}" width="{BW}" height="{hg:.1f}" rx="0" fill="{C["gov"]}"/>')
        if hp>0: out.append(f'<rect x="{x}" y="{yp:.1f}" width="{BW}" height="{hp:.1f}" rx="4" fill="{C["per"]}"/>')
        if hg>0 and hp==0: out.append(f'<rect x="{x}" y="{yg:.1f}" width="{BW}" height="4" rx="4" fill="{C["gov"]}"/>')
        out.append('</g>')
        if d["decade"] % 40 == 0 or i==len(dec)-1:
            out.append(f'<text class="ax" x="{x+BW/2}" y="{H+18}" text-anchor="middle">{d["decade"]}</text>')
    out.append(f'<text class="axlab" x="{PAD}" y="{H+44}">年代（以文书起始年归入）</text>')
    out.append('</svg>')
    return "\n".join(out)

# ---------- SVG：官契占比 分期折线 ----------
def pct_svg():
    W,Hh,PL = 640, 230, 52
    pts=[]; n=len(per)
    for i,p in enumerate(per):
        x = PL + (W-PL-30)*(i/(n-1)); y = Hh-20 - (p["pct_gov"]/100)*(Hh-56)
        pts.append((x,y,p))
    out=[f'<svg viewBox="0 0 {W} {Hh+42}" role="img" aria-label="官契占比随分期变化折线图" class="chart">']
    for gy in (0,25,50,75,100):
        y = Hh-20-(gy/100)*(Hh-56)
        out.append(f'<line class="grid" x1="{PL}" y1="{y:.1f}" x2="{W-20}" y2="{y:.1f}"/>')
        out.append(f'<text class="ax" x="{PL-8}" y="{y+4:.1f}" text-anchor="end">{gy}%</text>')
    out.append('<polyline class="pline" points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in pts)+'"/>')
    for x,y,p in pts:
        t=f'{p["period"]}　官契 {p["government"]} / 民契 {p["personal"]}　官契占 {p["pct_gov"]}%'
        out.append(f'<g class="pt" {tip(t)}><circle class="hit" cx="{x:.1f}" cy="{y:.1f}" r="14"/>'
                   f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="5.5"/>'
                   f'<text class="val" x="{x:.1f}" y="{y-14:.1f}" text-anchor="middle">{p["pct_gov"]:.0f}%</text></g>')
        lbl=p["period"].split(" ")[0]
        out.append(f'<text class="ax sm" x="{x:.1f}" y="{Hh+4}" text-anchor="middle">{e(lbl)}</text>')
        rng=p["period"].split(" ")[1] if " " in p["period"] else ""
        out.append(f'<text class="ax xs" x="{x:.1f}" y="{Hh+20}" text-anchor="middle">{e(rng)}</text>')
    out.append('</svg>')
    return "\n".join(out)

# ---------- SVG：单个宗族簇 ----------
TYPE_FILL={"person":"var(--series-1)","woman":"var(--series-2)",
           "institution":"var(--series-3)","government":"var(--series-3)"}
def comp_svg(c, W=200, Hh=150):
    out=[f'<svg viewBox="0 0 {W} {Hh}" class="net" role="img" aria-label="宗族交易关系图">']
    pos={n["id"]:(n["x"],n["y"]) for n in c["nodes"]}
    for ed in c["edges"]:
        x1,y1=pos[ed["s"]]; x2,y2=pos[ed["t"]]
        cls="edge trade" if ed["kind"]=="trade" else "edge co"
        out.append(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    cy_mean = sum(p[1] for p in pos.values())/len(pos)
    for n in c["nodes"]:
        x,y=pos[n["id"]]; r=5+min(4,n["n_docs"]-1)
        roles="・".join({"seller":"賣","buyer":"買","owner":"業主"}.get(k,k)+str(v) for k,v in n["roles"].items())
        t=f'{n["id"]}　{n["n_docs"]}件　{roles}'
        shp=(f'<circle cx="{x}" cy="{y}" r="{r}"/>' if n["type"]=="person"
             else f'<rect x="{x-r}" y="{y-r}" width="{2*r}" height="{2*r}" rx="1.5" transform="rotate(45 {x} {y})"/>'
             if n["type"]=="woman"
             else f'<rect x="{x-r}" y="{y-r}" width="{2*r}" height="{2*r}" rx="1.5"/>')
        below = y < cy_mean
        ly = y + r + 12 if below else y - r - 6
        out.append(f'<g class="node t-{n["type"]}" {tip(t)} style="fill:{TYPE_FILL[n["type"]]}">'
                   f'<circle class="hit" cx="{x}" cy="{y}" r="15"/>{shp}'
                   f'<text class="nlab" x="{x}" y="{ly:.1f}" text-anchor="middle">{e(n["id"])}</text></g>')
    out.append('</svg>')
    return "\n".join(out)

# ================= HTML =================
CSS = """
:root{
  color-scheme:light;
  --surface-0:#f7f6f3; --surface-1:#fcfcfb; --surface-2:#f0efec;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#86857f;
  --rule:#e0dfda; --rule-strong:#cbcac4;
  --series-1:#2a78d6; --series-2:#eb6834; --series-3:#1baf7a;
  --cell-zero:#f4f3f0; --accent:#1c5cab;
}
@media (prefers-color-scheme:dark){ :root:where(:not([data-theme=light])){
  color-scheme:dark;
  --surface-0:#121211; --surface-1:#1a1a19; --surface-2:#242423;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8e8d85;
  --rule:#333331; --rule-strong:#45443f;
  --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
  --cell-zero:#232322; --accent:#86b6ef;
}}
:root[data-theme=dark]{
  color-scheme:dark;
  --surface-0:#121211; --surface-1:#1a1a19; --surface-2:#242423;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8e8d85;
  --rule:#333331; --rule-strong:#45443f;
  --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
  --cell-zero:#232322; --accent:#86b6ef;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--surface-0);color:var(--text-primary);
  font-family:"Source Han Serif SC","Noto Serif CJK SC","Songti SC",Georgia,"Times New Roman",serif;
  line-height:1.75;font-size:16px}
.wrap{max-width:980px;margin:0 auto;padding:0 16px}
header.hero{border-bottom:1px solid var(--rule);background:var(--surface-1);padding:56px 0 34px}
.kicker{font-size:13px;letter-spacing:.14em;color:var(--text-muted);text-transform:uppercase;
  font-family:ui-sans-serif,system-ui,-apple-system,"Helvetica Neue",sans-serif;margin:0 0 12px}
h1{font-size:clamp(28px,5vw,42px);line-height:1.25;margin:0 0 10px;letter-spacing:-.01em}
.sub{color:var(--text-secondary);font-size:17px;margin:0 0 26px;max-width:62ch}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;
  background:var(--surface-1);border:1px solid var(--rule);border-radius:10px;overflow:hidden}
/* 線由每格自身的 1px 外框拼出，末行空位才不會露出一塊灰 */
.stat{background:var(--surface-1);padding:16px 18px;box-shadow:0 0 0 1px var(--rule)}
.stat b{display:block;font-size:26px;line-height:1.15;letter-spacing:-.02em}
.stat span{display:block;font-size:12.5px;color:var(--text-muted);margin-top:4px;
  font-family:ui-sans-serif,system-ui,sans-serif}
section{padding:52px 0;border-bottom:1px solid var(--rule)}
h2{font-size:25px;margin:0 0 6px;letter-spacing:-.01em}
h2 .num{color:var(--text-muted);font-size:15px;margin-right:10px;font-variant-numeric:tabular-nums}
h3{font-size:17px;margin:34px 0 10px}
.lede{color:var(--text-secondary);max-width:68ch;margin:0 0 26px}
p{max-width:68ch}
.finding{border-left:3px solid var(--accent);background:var(--surface-1);
  padding:14px 18px;margin:22px 0;border-radius:0 8px 8px 0}
.finding p{margin:0;font-size:15.5px}
.caveat{border-left:3px solid var(--series-2)}
figure{margin:26px 0;background:var(--surface-1);border:1px solid var(--rule);
  border-radius:10px;padding:20px 18px 14px}
figcaption{font-size:13.5px;color:var(--text-muted);margin-top:12px;line-height:1.6;
  font-family:ui-sans-serif,system-ui,sans-serif}
.chart{width:100%;height:auto;overflow:visible}
.grid{stroke:var(--rule);stroke-width:1}
text{font-family:ui-sans-serif,system-ui,-apple-system,sans-serif}
.ax{font-size:11px;fill:var(--text-muted)} .ax.sm{font-size:11.5px;fill:var(--text-secondary)}
.ax.xs{font-size:10px;fill:var(--text-muted)}
.axlab{font-size:11.5px;fill:var(--text-muted)}
.val{font-size:11.5px;fill:var(--text-primary);font-weight:600}
.pline{fill:none;stroke:var(--series-1);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.dot{fill:var(--series-1);stroke:var(--surface-1);stroke-width:2}
.hit{fill:transparent}
.bar .hit,.pt .hit,.node .hit{cursor:pointer}
.bar:hover rect:not(.hit),.bar:focus rect:not(.hit){opacity:.78}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin:0 0 14px;font-size:13px;
  font-family:ui-sans-serif,system-ui,sans-serif;color:var(--text-secondary)}
.legend i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.legend .dia{transform:rotate(45deg);border-radius:1px}
/* 寬表在窄屏自行橫向滾動，避免整頁橫向滾動 */
.tablescroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:14px 0;
  background:linear-gradient(to right,var(--surface-1) 30%,transparent),
             linear-gradient(to left,var(--surface-1) 30%,transparent) 100% 0,
             radial-gradient(farthest-side at 0 50%,rgba(0,0,0,.12),transparent),
             radial-gradient(farthest-side at 100% 50%,rgba(0,0,0,.12),transparent) 100% 0;
  background-repeat:no-repeat;background-size:40px 100%,40px 100%,14px 100%,14px 100%;
  background-attachment:local,local,scroll,scroll}
.tablescroll table{margin:0}
table{border-collapse:collapse;width:100%;font-size:14px;margin:14px 0}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-family:ui-sans-serif,system-ui,sans-serif;font-size:12.5px;color:var(--text-muted);
  font-weight:600;letter-spacing:.02em;border-bottom:1px solid var(--rule-strong)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tbody tr:hover{background:var(--surface-2)}
.hm{border-collapse:separate;border-spacing:2px}
.hm td.c{text-align:center;border:0;border-radius:3px;font-variant-numeric:tabular-nums;
  font-size:13px;padding:7px 4px;min-width:62px}
.hm th{border:0;font-size:11.5px;text-align:center}
.hm td.rowlab{border:0;font-size:13.5px;white-space:nowrap;padding-right:12px}
.hm td.rowlab small{color:var(--text-muted);font-size:11.5px;display:block;line-height:1.4}
.netgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(216px,1fr));gap:14px;margin:18px 0}
.netcard{background:var(--surface-1);border:1px solid var(--rule);border-radius:9px;padding:10px 10px 6px}
.netcard h4{margin:0 0 2px;font-size:14px}
.netcard .meta{font-size:11.5px;color:var(--text-muted);margin:0 0 4px;
  font-family:ui-sans-serif,system-ui,sans-serif;line-height:1.5}
.net{width:100%;height:auto;overflow:visible}
.edge{stroke:var(--rule-strong)} .edge.trade{stroke-width:2} .edge.co{stroke-width:1.5;stroke-dasharray:3 3}
.node text.nlab{font-size:9.5px;fill:var(--text-secondary);paint-order:stroke;
  stroke:var(--surface-1);stroke-width:3px;stroke-linejoin:round}
.node:hover circle:not(.hit),.node:focus circle:not(.hit),
.node:hover rect,.node:focus rect{stroke:var(--surface-1);stroke-width:2}
details{margin:16px 0;border:1px solid var(--rule);border-radius:8px;background:var(--surface-1)}
summary{cursor:pointer;padding:11px 16px;font-size:14px;color:var(--text-secondary);
  font-family:ui-sans-serif,system-ui,sans-serif}
summary:hover{color:var(--text-primary)}
details[open] summary{border-bottom:1px solid var(--rule)}
.dwrap{padding:4px 16px 12px;overflow-x:auto}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;
  background:var(--surface-2);padding:1.5px 5px;border-radius:4px}
pre{background:var(--surface-2);padding:13px 15px;border-radius:8px;overflow-x:auto;
  font-size:12.5px;line-height:1.6;border:1px solid var(--rule)}
pre code{background:none;padding:0}
a{color:var(--accent);text-underline-offset:2px}
.tag{display:inline-block;font-size:11px;padding:1.5px 7px;border-radius:20px;
  background:var(--surface-2);color:var(--text-secondary);margin-left:6px;
  font-family:ui-sans-serif,system-ui,sans-serif;vertical-align:1px}
.dl{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.dl a{display:block;border:1px solid var(--rule);border-radius:8px;padding:11px 15px;
  background:var(--surface-1);text-decoration:none;font-size:14px;min-width:190px}
.dl a b{display:block;color:var(--text-primary)}
.dl a span{font-size:12px;color:var(--text-muted);font-family:ui-sans-serif,system-ui,sans-serif}
.dl a:hover{border-color:var(--rule-strong)}
footer{padding:36px 0 60px;color:var(--text-muted);font-size:13.5px}
footer a{color:var(--text-secondary)}
#tip{position:fixed;z-index:50;pointer-events:none;opacity:0;transition:opacity .11s;
  background:var(--text-primary);color:var(--surface-1);font-size:12.5px;padding:6px 10px;
  border-radius:6px;max-width:300px;line-height:1.5;
  font-family:ui-sans-serif,system-ui,sans-serif;box-shadow:0 3px 14px rgba(0,0,0,.2)}
.themebtn{position:fixed;right:14px;top:14px;z-index:60;border:1px solid var(--rule-strong);
  background:var(--surface-1);color:var(--text-secondary);border-radius:7px;padding:6px 11px;
  font-size:12.5px;cursor:pointer;font-family:ui-sans-serif,system-ui,sans-serif}
@media (max-width:620px){
  body{font-size:15.5px} section{padding:38px 0}
  .netgrid{grid-template-columns:repeat(auto-fill,minmax(168px,1fr))}
  .hm td.c{min-width:44px;font-size:12px;padding:6px 2px}
}
@media print{.themebtn,#tip{display:none}}
"""

# ---------- 片段 ----------
def merge_table():
    r=['<table><thead><tr><th>歸併後地理單元</th><th>原編目寫法（件數）</th><th class="num">合計</th><th>今屬</th></tr></thead><tbody>']
    for m in merge_rows:
        vs="　".join(f'{e(v)} <span class="tag">{n}</span>' for v,n in m["variants"])
        note=f'<br><small style="color:var(--text-muted);font-size:12px">{e(m["note"])}</small>' if m["note"] else ""
        r.append(f'<tr><td><b>{e(m["unit"])}</b>{note}</td><td>{vs}</td>'
                 f'<td class="num">{m["total"]}</td><td style="color:var(--text-secondary);font-size:13px">{e(m["modern"])}</td></tr>')
    r.append('</tbody></table>')
    return '<div class="tablescroll">' + "\n".join(r) + '</div>'

def heatmap():
    o=['<table class="hm"><thead><tr><th></th>']
    for p in st["periods"]: o.append(f'<th>{e(p["code"])}<br><span style="color:var(--text-muted);font-weight:400">{e(p["label"])}</span></th>')
    o.append('<th class="num">合計</th></tr></thead><tbody>')
    for row in st["rows"]:
        o.append(f'<tr><td class="rowlab">{e(row["unit"])}<small>{e(row["modern"])}</small></td>')
        for i,v in enumerate(row["cells"]):
            t=f'{row["unit"]}　{st["periods"][i]["label"]}（{st["periods"][i]["code"]}）　{v} 件'
            o.append(f'<td class="c" style="background:{ramp(v)};color:{ink(v)}" {tip(t)}>{v or "·"}</td>')
        o.append(f'<td class="num" style="font-weight:600">{row["total"]}</td></tr>')
    o.append('</tbody></table>')
    return '<div class="tablescroll">' + "\n".join(o) + '</div>'

def netcards(n=12):
    o=['<div class="netgrid">']
    for c in comps[:n]:
        yr=f'{c["years"][0]}–{c["years"][1]}' if c["years"] else "年份不明"
        if c["years"] and c["years"][0]==c["years"][1]: yr=str(c["years"][0])
        u="、".join(c["units"]) or "地點不明"
        o.append(f'<div class="netcard"><h4>{e(c["dominant_surname"])}氏等 {c["n"]} 人</h4>'
                 f'<p class="meta">{c["n_docs"]} 件 · {e(yr)}<br>{e(u)}</p>{comp_svg(c)}</div>')
    o.append('</div>')
    return "\n".join(o)

def lineage_table(n=16):
    o=['<table><thead><tr><th>字輩</th><th class="num">人</th><th class="num">文書</th>'
       '<th>年代</th><th>地理單元</th><th>成員</th></tr></thead><tbody>']
    for c in lin[:n]:
        o.append(f'<tr><td><b>{e(c["label"])}</b></td><td class="num">{c["n_members"]}</td>'
                 f'<td class="num">{c["n_docs"]}</td><td class="num">{c["year_min"] or "?"}–{c["year_max"] or "?"}</td>'
                 f'<td style="font-size:13px;color:var(--text-secondary)">{e("、".join(c["units"]) or "—")}</td>'
                 f'<td style="font-size:13px">{e("、".join(c["members"]))}</td></tr>')
    o.append('</tbody></table>')
    return '<div class="tablescroll">' + "\n".join(o) + '</div>'

top_people = sorted([n for n in net["nodes"] if n["type"]=="person"], key=lambda n:-n["n_docs"])[:12]
def people_table():
    o=['<table><thead><tr><th>人物</th><th class="num">文書</th><th>角色</th><th>年代</th><th>地理單元</th></tr></thead><tbody>']
    RL={"seller":"賣主","buyer":"買主","owner":"業主"}
    for n in top_people:
        rs="、".join(f'{RL.get(k,k)}×{v}' for k,v in sorted(n["roles"].items(),key=lambda x:-x[1]))
        yr=f'{n["year_min"]}–{n["year_max"]}' if n["year_min"] else "—"
        if n["year_min"]==n["year_max"]: yr=str(n["year_min"] or "—")
        o.append(f'<tr><td><b>{e(n["id"])}</b></td><td class="num">{n["n_docs"]}</td><td>{e(rs)}</td>'
                 f'<td class="num">{e(yr)}</td><td style="font-size:13px;color:var(--text-secondary)">{e("、".join(n["units"]) or "—")}</td></tr>')
    o.append('</tbody></table>')
    return '<div class="tablescroll">' + "\n".join(o) + '</div>'

def decade_table():
    o=['<table><thead><tr><th class="num">年代</th><th class="num">官契</th><th class="num">民契</th>'
       '<th class="num">合計</th><th class="num">官契占比</th></tr></thead><tbody>']
    for d in dec:
        t=d["government"]+d["personal"]
        pc=f'{100*d["government"]/t:.0f}%' if t else "—"
        o.append(f'<tr><td class="num">{d["decade"]}s</td><td class="num">{d["government"]}</td>'
                 f'<td class="num">{d["personal"]}</td><td class="num">{t}</td><td class="num">{pc}</td></tr>')
    o.append('</tbody></table>')
    return '<div class="tablescroll">' + "\n".join(o) + '</div>'

gov_tot=sum(p["government"] for p in per); per_tot=sum(p["personal"] for p in per)
early=per[1]; late=per[4]; rep=per[3]

HTML = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>閩中契約：匹茲堡大學藏中國土地文書 235 件</title>
<meta name="description" content="University of Pittsburgh 藏 Chinese Land Records（1584–1978，235 件）的歷史政區歸併、宗族網絡、時空分布與官民契比例分析。">
<style>{CSS}</style>
</head>
<body>
<button class="themebtn" id="tb" aria-label="切換深淺色">◐ 深／淺</button>
<div id="tip" role="status" aria-live="polite"></div>

<header class="hero"><div class="wrap">
  <p class="kicker">EASTD 143A · 數位人文個案</p>
  <h1>閩中契約</h1>
  <p class="sub">匹茲堡大學圖書館藏「Chinese Land Records」235 件，始於明萬曆十二年（1584），
  迄於 1978 年。本頁將館方編目中以自由文字記錄的當事人、地點與文書性質，
  還原為可計算的結構，並據以考察歷史政區、宗族網絡與國家契約管控的變化。</p>
  <div class="stats">
    <div class="stat"><b>{n_docs}</b><span>契約文書</span></div>
    <div class="stat"><b>{min(yrs)}–{max(yrs)}</b><span>年代跨度</span></div>
    <div class="stat"><b>{raw_places} → {n_units}</b><span>地名歸併後單元</span></div>
    <div class="stat"><b>{len(persons)}</b><span>可識別個人</span></div>
    <div class="stat"><b>{len(lin)}</b><span>字輩族群</span></div>
  </div>
</div></header>

<section><div class="wrap">
  <h2><span class="num">一</span>縣名歸併：同一個地方的四個名字</h2>
  <p class="lede">原始編目共出現 {raw_places} 種地名寫法。若直接統計，福州府核心區會被拆成互不相干的若干「縣」——
  因為近代閩中政區屢經改制，而編目者忠實照錄了文書上的當時名稱。</p>

  <div class="finding"><p><b>最關鍵的一組：</b>閩縣與侯官縣於 1913 年 3 月合併為閩侯縣；
  1943 年 10 月為紀念該縣出身的林森改名林森縣；1950 年 4 月復名閩侯縣。
  這四個名字（連同文言寫法「閩邑」與省會「福州市」）指的是同一片土地。</p></div>

  <figure>
    <div class="legend">{"".join(f'<span><i style="background:var(--series-1);opacity:{0.3+0.7*n/minhou_total:.2f}"></i>{e(v)} {n} 件</span>' for v,n in minhou_pre)}</div>
    <p style="margin:6px 0 0;font-size:15px">歸併前最大的單一「縣」為 <b>{minhou_pre[0][1]} 件</b>；
    歸併後，閩侯單元合計 <b>{minhou_total} 件</b>，占全藏 <b>{100*minhou_total/n_docs:.0f}%</b>。</p>
    <figcaption>不做歸併，這批文書看起來像是分散於十餘縣的雜項；歸併之後才顯出它其實是一批高度集中於福州府核心區的地方文書。</figcaption>
  </figure>

  <h3>歸併對照表</h3>
  {merge_table()}

  <div class="finding caveat"><p><b>未歸併者。</b>
  「福建省(清源縣?)」2 件——問號為館方原有，近代福建無清源縣建制（清源為唐代泉州郡名），不予歸併；
  「福建省上竹林」1 件為村落級地名；「華東」1 件為 1949 年大行政區；另有 9 件僅標至省級、
  {geo["unlabeled"]} 件完全未標地點。非福建者 {geo["non_fujian"]} 件（皖、川、滇、遼、滬）。
  以上均排除於下節時空統計之外。</p></div>
</div></section>

<section><div class="wrap">
  <h2><span class="num">二</span>宗族網絡：字輩是最強的線索</h2>
  <p class="lede">把當事人連成網絡，{len(persons)+len(women)+len(insts)} 個節點散成 {len([c for c in comps])} 個互不相連的小簇，
  沒有貫通全藏的大網——這本就是一批來源分散的文書。真正的結構藏在<b>字輩</b>裡。</p>

  <div class="finding"><p><b>買進與賣出可能出自同一房。</b>
  陳欽瑞（1932–1936 年間四次買入）與陳欽隆（1936 年四次賣出）同屬「欽」字輩；
  黃氏在永泰的「同」字輩與「國」字輩分屬兩代。
  土地並非單向流失，而是在宗族內部重新分配。</p></div>

  <figure>
    <div class="legend">
      <span><i style="background:var(--series-1);border-radius:50%"></i>男性個人</span>
      <span><i class="dia" style="background:var(--series-2)"></i>女性（以「氏」稱）</span>
      <span><i style="background:var(--series-3)"></i>法人／官方</span>
      <span style="color:var(--text-muted)">—— 買賣關係　‑‑‑ 共同具名</span>
    </div>
    {netcards()}
    <figcaption>最大的 12 個交易簇；節點大小表示該人出現的文書數。簇內多數同姓，
    虛線表示在同一契約中共同具名（多為兄弟或族人）。</figcaption>
  </figure>

  <h3>字輩族群 <span class="tag">共 {len(lin)} 組，涵蓋 {len({m for c in lin for m in c["members"]})} 人、{len({d for c in lin for d in c["docs"]})} 件</span></h3>
  <p>同姓且名字第二字相同者，在閩中宗族中通常為同輩族人。此一線索把孤立的人名連成了可追索的世代。</p>
  {lineage_table()}

  <h3>出現最頻繁的個人</h3>
  {people_table()}
  <div class="finding"><p><b>林萬開</b>在 1875 至 1913 年間五次作為買主出現，另有一次賣出、一次登記為業主，
  全部位於閩侯單元——近四十年持續購入，是這批材料中土地集中最清晰的個案。</p></div>

  <details><summary>為什麼「林」「陳」這類單姓不計入網絡？</summary>
  <div class="dwrap"><p style="font-size:14.5px">編目中有 15 處當事人僅記姓氏（如「Buyer: 林 [LIN]」），
  因為文書本身未載全名。若把它們當作同一個節點，8 件互不相干的契約會被錯接成一個虛假的樞紐，
  並憑空造出一個「最大家族」。本頁將其一律視為不可識別，排除於網絡之外。
  同理，「（出租）」為文書性質標註而非姓名的一部分，「陳國遠代陳國龍」中的「代」表示代理關係。</p></div></details>
</div></section>

<section><div class="wrap">
  <h2><span class="num">三</span>時空分布</h2>
  <p class="lede">歸併後的 {n_units} 個地理單元與五個分期交叉。深色表示件數多。</p>
  <figure>
    {heatmap()}
    <figcaption>僅計入可定年且地點可歸併者（{sum(r["total"] for r in st["rows"])} 件）。
    單元按總件數排序；一件跨兩縣的文書在兩列各計一次。</figcaption>
  </figure>
  <div class="finding"><p><b>1949 年前後重心南移。</b>
  清至民國，文書幾乎全部集中於福州府一帶（閩侯、永泰、古田、閩清）；
  1949 年以後，東山、晉江、南安等閩南沿海縣份首次成批出現，而閩侯僅餘 3 件。
  這更可能反映文書的徵集與流傳路徑，而非土地交易本身的地理轉移。</p></div>
</div></section>

<section><div class="wrap">
  <h2><span class="num">四</span>官契與民契：國家何時介入田土</h2>
  <p class="lede">館方將每件文書標為 Government（經官府鈐印、納稅、發照的「紅契」一類）
  或 Personal（民間自立的「白契」一類）。全藏官契 {gov_tot} 件、民契 {per_tot} 件。</p>

  <figure>
    <div class="legend">
      <span><i style="background:var(--series-1)"></i>官契 Government</span>
      <span><i style="background:var(--series-2)"></i>民契 Personal</span>
    </div>
    {bars_svg()}
    <figcaption>各年代件數。1920 年代（36 件）與 1940 年代（32 件）兩個高峰，
    與民國歷次田賦整理、土地陳報登記的時間吻合。</figcaption>
  </figure>

  <figure>
    {pct_svg()}
    <figcaption>官契占比隨分期變化。縱軸為官契占該期官民契總數之比。</figcaption>
  </figure>

  <div class="finding"><p><b>官契占比單調上升：</b>
  {early["period"]} 期 {early["pct_gov"]}% → {rep["period"]} 期 {rep["pct_gov"]}% → {late["period"]} 期 {late["pct_gov"]}%。
  經官府確認的土地契約比重持續擴大，1949 年後僅餘 1 件民契。</p></div>

  <div class="finding caveat"><p><b>這條曲線不能直接讀作「國家管控強度」。</b>
  其一，鈐印納稅的官契更易被保存與收藏，存世率本就高於民間白契，年代越早差距越大；
  其二，{per[0]["period"]} 期僅 {per[0]["n"]} 件，統計意義有限；
  其三，這是一批經過兩次選擇（原藏家、後入藏）的材料，不是隨機樣本。
  可靠的結論只是：<b>在這批文書中</b>，晚近者更多地帶有官方印記。</p></div>

  <details><summary>分年代數據表</summary><div class="dwrap">{decade_table()}</div></details>
</div></section>

<section><div class="wrap">
  <h2><span class="num">五</span>方法與局限</h2>
  <h3>資料來源</h3>
  <p>全部元資料取自匹茲堡大學 ULS 數位館藏的公開 <code>JSON:API</code>（平台為 Islandora 2 / Drupal 11），
  未解析 HTML 頁面。館藏節點 UUID 為 <code>6985ef8a-1fe9-4b46-91ee-e14ba00d0822</code>，
  五次請求取完 235 筆，採集於 2026-10-07。</p>
  <pre><code>https://digital.library.pitt.edu/jsonapi/node/islandora_object
  ?filter[field_member_of.id]=6985ef8a-1fe9-4b46-91ee-e14ba00d0822
  &amp;fields[node--islandora_object]=title,field_date_str,field_pid,path
  &amp;page[limit]=50</code></pre>
  <p>兩點實務經驗：站點裝有 nginx bad-bot 過濾，<code>User-Agent</code> 含 <code>harvest</code>
  一類詞彙會被直接拒為 502，需使用正常的識別字串；不加 <code>fields[]</code> 時單筆約 17 KB，
  易因負載過大而間歇失敗，使用稀疏欄位可降至約 1/25。</p>

  <h3>結構化的依據</h3>
  <p>館方的 <code>title</code> 欄位以固定句式編碼了當事人、角色、地點與文書性質，例如
  <code>Seller: 藍炳孫 [LAN Bingsun] -- Buyer: 程長孫 [CHENG Changsun] -- Personal</code>。
  本頁的全部結構化欄位由此解析而來，並按類型區分為個人、女性（以「氏」稱）、法人、官方與不可識別五類。</p>

  <h3>必須說明的限制</h3>
  <ul>
    <li><b>沒有全文。</b>該館藏未提供 OCR 或釋文（<code>media--extracted_text</code> 為空），
      契約正文僅存在於影像中。本頁所有分析均<b>基於編目元資料，而非文書本身</b>，
      因此無法涉及田地面積、價銀、稅率等正文信息。</li>
    <li><b>年代以起始年歸入。</b>67 件的日期為區間（如 <code>1946/1951</code>，代表一冊跨年文書），
      統計時取起始年；11 件無日期。</li>
    <li><b>地名為編目者所記，未必是文書當時的行政名。</b>部分 1913 年前的文書已被標為「閩侯縣」，
      顯示編目中存在以今名回標的情況，故本頁按<b>地理單元</b>而非縣名統計。</li>
    <li><b>這不是隨機樣本</b>，而是一批經原藏家與入藏機構兩次選擇的材料；
      任何比例性的結論都只在這批文書內部成立。</li>
  </ul>

  <h3>權利狀態</h3>
  <p>原館藏權利狀態標為 <b>Copyright Undetermined</b>（未定），並非公有領域聲明。
  本頁僅使用描述性元資料並連結回原始條目，未轉載影像。如需公開發布影像，
  請先聯繫 University of Pittsburgh, Archives &amp; Special Collections。</p>
</div></section>

<section><div class="wrap">
  <h2><span class="num">六</span>數據下載</h2>
  <p class="lede">全部衍生數據以 CC0 釋出，可自由用於教學與研究；原始元資料之權利歸屬匹茲堡大學。</p>
  <div class="dl">
    <a href="data/chinese_land_records_235.csv" download><b>records.csv</b><span>235 件 · 結構化主表</span></a>
    <a href="data/records.json" download><b>records.json</b><span>同上 · JSON</span></a>
    <a href="data/entities.json" download><b>entities.json</b><span>413 條當事人記錄（含類型）</span></a>
    <a href="data/network.json" download><b>network.json</b><span>人物網絡 節點／邊</span></a>
    <a href="data/lineage_clusters.json" download><b>lineage_clusters.json</b><span>{len(lin)} 組字輩族群</span></a>
    <a href="data/county_normalization.json" download><b>county_normalization.json</b><span>歷史政區歸併表</span></a>
    <a href="data/spacetime.json" download><b>spacetime.json</b><span>時空矩陣</span></a>
    <a href="data/raw_items.json" download><b>raw_items.json</b><span>未經處理的 API 原始回應</span></a>
  </div>
  <p style="font-size:14px;color:var(--text-secondary)">每件文書的 <code>url</code> 欄位可回到館方條目頁，
  <code>iiif_manifest</code> 欄位為 IIIF Presentation 2.0 清單，影像原尺寸約 5776×8280，
  可用 <code>/full/1000,/0/default.jpg</code> 按需縮放。</p>
</div></section>

<footer><div class="wrap">
  <p>資料來源：University of Pittsburgh Library System,
  <a href="https://digital.library.pitt.edu/collection/chinese-land-records"><i>Chinese Land Records, 1584-1978</i></a>,
  EAL.2011.01, Archives &amp; Special Collections.</p>
  <p>政區沿革依據中文維基百科「閩侯縣」「永泰縣」條目。採集日期 2026-10-07。
  本頁為 EASTD 143A《東亞人文的數位工具與方法》課程個案。</p>
</div></footer>

<script>
(function(){{
  var tb=document.getElementById('tb');
  try{{var s=localStorage.getItem('theme'); if(s)document.documentElement.setAttribute('data-theme',s);}}catch(e){{}}
  tb.addEventListener('click',function(){{
    var cur=document.documentElement.getAttribute('data-theme');
    if(!cur) cur = matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
    var nx = cur==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',nx);
    try{{localStorage.setItem('theme',nx);}}catch(e){{}}
  }});
  var tip=document.getElementById('tip'), cur=null;
  function show(el,x,y){{
    var t=el.getAttribute('data-tip'); if(!t)return;
    tip.textContent=t; tip.style.opacity='1';
    var r=tip.getBoundingClientRect();
    var left=Math.min(Math.max(8,x-r.width/2), innerWidth-r.width-8);
    var top=y-r.height-12; if(top<8) top=y+18;
    tip.style.left=left+'px'; tip.style.top=top+'px';
  }}
  function hide(){{tip.style.opacity='0'; cur=null;}}
  document.addEventListener('mousemove',function(ev){{
    var el=ev.target.closest('[data-tip]');
    if(!el){{if(cur)hide();return;}}
    cur=el; show(el,ev.clientX,ev.clientY);
  }});
  document.addEventListener('focusin',function(ev){{
    var el=ev.target.closest('[data-tip]'); if(!el)return;
    var b=el.getBoundingClientRect(); show(el,b.left+b.width/2,b.top);
  }});
  document.addEventListener('focusout',hide);
  document.addEventListener('scroll',hide,{{passive:true}});
}})();
</script>
</body></html>"""

out=os.path.join(os.path.dirname(P),"index.html")
os.makedirs(os.path.dirname(out),exist_ok=True)
open(out,"w",encoding="utf-8").write(HTML)
print("wrote",out,f"({len(HTML)/1024:.0f} KB)")
