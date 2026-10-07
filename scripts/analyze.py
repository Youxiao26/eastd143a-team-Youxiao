#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤 2／3：解析编目标题、归并历史政区、抽取实体与网络。

输入  docs/data/raw_items.json 與 county_normalization.json
输出  records.json  entities.json  network.json  network_components.json
      lineage_clusters.json  spacetime.json  timeseries.json  period_summary.json
      chinese_land_records_235.csv
"""
import collections, csv, json, math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
D = os.path.join(REPO, "docs", "data")
CJK = r"[一-鿿]"
SURNAMES = set(
    "趙錢孫李周吳鄭王馮陳褚衛蔣沈韓楊朱秦尤許何呂施張孔曹嚴華金魏陶姜戚謝鄒喻柏水竇章雲蘇潘葛奚范彭郎魯韋昌馬苗鳳花方俞任袁柳酆鮑史唐費廉岑薛雷賀倪湯滕殷羅畢郝鄔安常樂于時傅皮卞齊康伍余元卜顧孟平黃和穆蕭尹姚邵湛汪祁毛禹狄米貝明臧計伏成戴談宋茅龐熊紀舒屈項祝董梁杜阮藍閔席季麻強賈路婁危江童顏郭林刁鍾徐邱駱高夏蔡田樊胡凌霍虞萬支柯昝管盧莫房繆干解應宗丁宣賁鄧郁單杭洪包諸左石崔吉鈕龔程嵇邢滑裴陸榮翁荀羊於惠甄曲家封芮羿儲靳汲邴糜松井段富巫烏焦巴弓牧隗山谷車侯宓蓬全郗班仰秋仲伊宮寧仇欒暴甘鈄厲戎祖武符劉景詹束龍葉幸司韶郜黎薊薄印宿白懷蒲邰從鄂索咸籍賴卓藺屠蒙池喬陰鬱胥能蒼雙聞莘黨翟譚貢勞逄姬申扶堵冉宰酈雍郤璩桑桂濮牛壽通邊扈燕冀郟浦尚農溫別莊晏柴瞿閻充慕連茹習宦艾魚容向古易慎戈廖庾終暨居衡步都耿滿弘匡國文寇廣祿闕東歐殳沃利蔚越夔隆師鞏厙聶晁勾敖融冷訾辛闞那簡饒空曾毋沙乜養鞠須豐巢關蒯相查后荊紅游竺權逯蓋益桓公紳")
INSTITUTION = re.compile(r"(老人會|公會|會$|堂$|祠|寺|庵|宮|書院|公司|商行|銀行|學校|局$|社$|房$)")
GOV = re.compile(r"(官方政府|政府|公家)")
# 编目中个别写法的规范化（人工核对后）
NAME_FIX = {"陳國遠立票人": "陳國遠", "黃國興等": "黃國興"}
PERIODS = [("≤1795", "明末—乾隆", lambda y: y <= 1795),
           ("1796–1874", "嘉道咸同", lambda y: 1796 <= y <= 1874),
           ("1875–1911", "光緒—清末", lambda y: 1875 <= y <= 1911),
           ("1912–1948", "民國", lambda y: 1912 <= y <= 1948),
           ("1949–", "1949以後", lambda y: y >= 1949)]

cjk = lambda s: "".join(re.findall(CJK + "+", s))
jload = lambda n: json.load(open(os.path.join(D, n), encoding="utf-8"))
def jdump(o, n): json.dump(o, open(os.path.join(D, n), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def classify(s):
    """把一个当事人字符串判为 person / woman / institution / government / surname_only。"""
    note, orig = [], s
    s = re.sub(r"[（(]\s*(出租|出典|代筆|代書)\s*[)）]", "", s)
    if "出租" in orig: note.append("lease")
    if re.search(r"[?？]", orig): note.append("uncertain")
    s = re.sub(r"[?？\s]", "", s)
    m = re.match(r"^(" + CJK + r"+?)代(" + CJK + r"+)$", s)
    agent = None
    if m:
        agent, s = m.group(1), m.group(2); note.append("agent")
    s = NAME_FIX.get(s, s)
    if not s: return None, None, note, agent
    if GOV.search(s): return s, "government", note, agent
    if INSTITUTION.search(s): return s, "institution", note, agent
    if s.endswith("氏"): return s, "woman", note, agent          # 以「氏」稱者為女性
    if len(s) == 1: return s, ("surname_only" if s in SURNAMES else "unknown"), note, agent
    return s, "person", note, agent


def split_people(v):
    v = re.sub(r"(?<=\])\s*(?=" + CJK + ")", " and ", v)   # 「A [ROM] B [ROM]」無連詞
    return [p.strip() for p in re.split(r"\s+and\s+|、|，", v) if p.strip()]


def parse_records(raw, norm):
    v2u, meta = {}, {}
    for u in norm["units"]:
        meta[u["unit_id"]] = u
        for v in u["variants"]: v2u[v] = u["unit_id"]
    nonfj = set(norm["non_fujian"])
    records, entities = [], []
    for it in raw:
        a = it["attributes"]; t = a.get("title") or ""
        seg = [s.strip() for s in re.split(r"\s*--\s*", t)]
        ds = (a.get("field_date_str") or "").strip()
        m = re.match(r"^(\d{3,4})(?:/(\d{3,4}))?$", ds)
        ys, ye = (m.group(1), m.group(2) or m.group(1)) if m else ("", "")
        nid = a.get("drupal_internal__nid")
        r = {"nid": nid, "pid": a.get("field_pid"), "date_raw": ds,
             "year_start": ys, "year_end": ye, "is_range": "Y" if (ys and ye and ys != ye) else "",
             "box_folder": "; ".join(a.get("field_source_location") or []),
             "extent": "; ".join(a.get("field_extent") or []), "title": t,
             "url": "https://digital.library.pitt.edu" + (a.get("path") or {}).get("alias", ""),
             "iiif_manifest": f"https://digital.library.pitt.edu/node/{nid}/manifest",
             "nature": seg[-1] if seg and seg[-1] in ("Government", "Personal") else ""}
        place, parties = "", collections.defaultdict(list)
        for s in seg:
            m2 = re.match(r"^(Owner|Seller|Buyer|Place)\s*:\s*(.+)$", s)
            if not m2: continue
            k, v = m2.group(1), re.sub(r"\s+", " ", m2.group(2)).strip()
            if k == "Place": place = v
            else: parties[k].extend(split_people(v))
        pc = cjk(place)
        r["place_full"], r["place_cjk"] = place, pc
        ids = norm["multi_county"].get(pc) or ([v2u[pc]] if pc in v2u else [])
        r["unit_ids"] = ids
        r["unit"] = " / ".join(meta[i]["unit"] for i in ids) if ids else ""
        r["geo_status"] = ("ok" if ids else "non_fujian" if pc in nonfj
                           else "unresolved" if pc in norm["unresolved"]
                           else "unlabeled" if not pc else "other")
        lease = False
        for role in ("Owner", "Seller", "Buyer"):
            names = []
            for v in parties.get(role, []):
                nm, ty, note, agent = classify(cjk(v))
                if not nm: continue
                if "lease" in note: lease = True
                names.append(nm)
                entities.append({"nid": nid, "role": role.lower(), "name": nm, "type": ty,
                                 "agent": agent or "", "notes": ";".join(note)})
            r[role.lower()] = " | ".join(names); r[role.lower() + "_n"] = len(names)
        r["is_lease"] = "Y" if lease else ""
        records.append(r)
    return records, entities, meta


def build_network(records, entities):
    """只把可识别的个体连成网络：光杆姓氏（如「林」）不是同一个人，一律排除。"""
    VALID = {"person", "woman", "institution", "government"}
    by_nid = {r["nid"]: r for r in records}
    bydoc = collections.defaultdict(lambda: collections.defaultdict(list))
    for e in entities:
        if e["type"] in VALID: bydoc[e["nid"]][e["role"]].append(e)
    nodes, edges = {}, collections.Counter()
    for nid, roles in bydoc.items():
        r = by_nid[nid]
        for role, lst in roles.items():
            for e in lst:
                n = nodes.setdefault(e["name"], {"type": e["type"], "docs": set(),
                                                 "roles": collections.Counter(),
                                                 "units": set(), "years": []})
                n["docs"].add(nid); n["roles"][role] += 1
                if r["unit"]: n["units"].add(r["unit"])
                if r["year_start"]: n["years"].append(int(r["year_start"]))
        S = [e["name"] for e in roles.get("seller", [])]
        B = [e["name"] for e in roles.get("buyer", [])]
        O = [e["name"] for e in roles.get("owner", [])]
        for s in S:
            for b in B:
                if s != b: edges[(min(s, b), max(s, b), "trade")] += 1
        for lst in (S, B, O):
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    if lst[i] != lst[j]: edges[(min(lst[i], lst[j]), max(lst[i], lst[j]), "co_party")] += 1
    return nodes, edges


def components(nodes, edges):
    adj = collections.defaultdict(set)
    for (a, b, _) in edges: adj[a].add(b); adj[b].add(a)
    seen, comps = set(), []
    for n in nodes:
        if n in seen: continue
        stack, c = [n], set()
        while stack:
            x = stack.pop()
            if x in c: continue
            c.add(x); seen.add(x); stack.extend(adj[x] - c)
        comps.append(c)
    return comps, adj


def layout(comp, adj, W=200, H=150, iters=600):
    """确定性 Fruchterman-Reingold；种子固定，便于复现。"""
    random.seed(42)
    ns = sorted(comp)
    pos = {n: [W / 2 + 40 * math.cos(2 * math.pi * i / len(ns)),
               H / 2 + 40 * math.sin(2 * math.pi * i / len(ns))] for i, n in enumerate(ns)}
    if len(ns) == 2:
        pos[ns[0]], pos[ns[1]] = [W / 2 - 45, H / 2], [W / 2 + 45, H / 2]
        return pos
    k = min(W, H) / 3.2
    for it in range(iters):
        t = 0.9 * (1 - it / iters) + 0.02
        disp = {n: [0, 0] for n in ns}
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or .01; f = k * k / d
                disp[a][0] += dx / d * f; disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f; disp[b][1] -= dy / d * f
        for a in ns:
            for b in adj[a]:
                if b not in comp or b <= a: continue
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or .01; f = d * d / k
                disp[a][0] -= dx / d * f; disp[a][1] -= dy / d * f
                disp[b][0] += dx / d * f; disp[b][1] += dy / d * f
        for n in ns:
            dx, dy = disp[n]; d = math.hypot(dx, dy) or .01
            pos[n][0] = max(26, min(W - 26, pos[n][0] + dx / d * min(d, t * 18)))
            pos[n][1] = max(22, min(H - 22, pos[n][1] + dy / d * min(d, t * 18)))
    return pos


def main():
    raw, norm = jload("raw_items.json"), jload("county_normalization.json")
    records, entities, meta = parse_records(raw, norm)
    jdump(records, "records.json"); jdump(entities, "entities.json")

    cols = ["nid", "pid", "date_raw", "year_start", "year_end", "is_range", "nature",
            "unit", "geo_status", "place_cjk", "owner", "seller", "buyer",
            "owner_n", "seller_n", "buyer_n", "is_lease", "place_full", "extent",
            "box_folder", "title", "url", "iiif_manifest"]
    with open(os.path.join(D, "chinese_land_records_235.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(records)

    nodes, edges = build_network(records, entities)
    jdump({"nodes": [{"id": n, "type": d["type"], "docs": sorted(d["docs"]), "n_docs": len(d["docs"]),
                      "roles": dict(d["roles"]), "units": sorted(d["units"]),
                      "year_min": min(d["years"]) if d["years"] else None,
                      "year_max": max(d["years"]) if d["years"] else None} for n, d in nodes.items()],
           "edges": [{"source": a, "target": b, "kind": k, "weight": w} for (a, b, k), w in edges.items()]},
          "network.json")

    comps, adj = components(nodes, edges)
    comps = sorted([c for c in comps if len(c) > 1],
                   key=lambda c: (-len(c), -len({d for n in c for d in nodes[n]["docs"]})))
    ew = {}
    for (a, b, k), w in edges.items(): ew[(a, b)] = {"kind": k, "weight": w}
    out = []
    for c in comps:
        pos = layout(c, adj)
        docs = sorted({d for n in c for d in nodes[n]["docs"]})
        yrs = [y for n in c for y in nodes[n]["years"]]
        sur = collections.Counter(n[0] for n in c if nodes[n]["type"] == "person")
        dom, domn = sur.most_common(1)[0] if sur else ("", 0)
        es = [{"s": a, "t": b, "kind": ew[(a, b)]["kind"], "w": ew[(a, b)]["weight"]}
              for a in sorted(c) for b in adj[a] if b in c and b > a and (a, b) in ew]
        out.append({"nodes": [{"id": n, "type": nodes[n]["type"], "x": round(pos[n][0], 1),
                               "y": round(pos[n][1], 1), "n_docs": len(nodes[n]["docs"]),
                               "roles": dict(nodes[n]["roles"]), "units": sorted(nodes[n]["units"])}
                              for n in sorted(c)],
                    "edges": es, "n": len(c), "n_docs": len(docs), "docs": docs,
                    "years": [min(yrs), max(yrs)] if yrs else None,
                    "units": sorted({u for n in c for u in nodes[n]["units"]}),
                    "dominant_surname": dom, "surname_share": round(domn / len(c), 2)})
    jdump(out, "network_components.json")

    # 字辈：同姓且名第二字相同
    gen = collections.defaultdict(list)
    for n, d in nodes.items():
        if d["type"] == "person" and len(n) >= 3: gen[(n[0], n[1])].append((n, d))
    lin = []
    for (sur, g), mem in gen.items():
        if len(mem) < 2: continue
        docs = sorted({x for _, d in mem for x in d["docs"]})
        yrs = [y for _, d in mem for y in d["years"]]
        lin.append({"surname": sur, "generation": g, "label": f"{sur}氏「{g}」字輩",
                    "members": sorted(n for n, _ in mem), "n_members": len(mem),
                    "docs": docs, "n_docs": len(docs),
                    "year_min": min(yrs) if yrs else None, "year_max": max(yrs) if yrs else None,
                    "units": sorted({u for _, d in mem for u in d["units"]})})
    lin.sort(key=lambda c: (-c["n_members"], -c["n_docs"]))
    jdump(lin, "lineage_clusters.json")

    # 时空矩阵
    mat = collections.defaultdict(collections.Counter)
    for r in records:
        if not r["year_start"] or not r["unit_ids"]: continue
        y = int(r["year_start"])
        for code, _, f in PERIODS:
            if f(y):
                for uid in r["unit_ids"]: mat[uid][code] += 1
                break
    units = sorted(mat, key=lambda u: -sum(mat[u].values()))
    jdump({"periods": [{"code": c, "label": l} for c, l, _ in PERIODS],
           "rows": [{"unit_id": u, "unit": meta[u]["unit"], "modern": meta[u]["modern"],
                     "note": meta[u]["note"], "cells": [mat[u][c] for c, _, _ in PERIODS],
                     "total": sum(mat[u].values())} for u in units]}, "spacetime.json")

    # 官民契时间序列
    ts = collections.defaultdict(collections.Counter)
    for r in records:
        if r["year_start"]: ts[int(r["year_start"]) // 10 * 10][r["nature"] or "未标"] += 1
    jdump([{"decade": d, "government": ts[d].get("Government", 0),
            "personal": ts[d].get("Personal", 0), "total": sum(ts[d].values())}
           for d in sorted(ts)], "timeseries.json")

    summary = []
    for code, lab, f in PERIODS:
        sub = [r for r in records if r["year_start"] and f(int(r["year_start"]))]
        g = sum(1 for r in sub if r["nature"] == "Government")
        p = sum(1 for r in sub if r["nature"] == "Personal")
        summary.append({"period": f"{lab} {code}", "government": g, "personal": p,
                        "pct_gov": round(100 * g / (g + p), 1) if g + p else 0, "n": len(sub)})
    jdump(summary, "period_summary.json")

    print(f"records {len(records)} | entities {len(entities)} | nodes {len(nodes)} "
          f"| clusters {len(out)} | lineages {len(lin)}")


if __name__ == "__main__":
    main()
