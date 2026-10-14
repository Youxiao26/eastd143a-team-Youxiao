"""把 land_contracts 下的 9 个页面合并成一个单文件网页 index.html。

每个页面原样嵌入（iframe srcdoc），互不干扰；导航切换时才渲染对应页面。
用法：python build_index.py   （在 scripts 目录下运行）
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGES = [
    ("map", "land_map.html", "地理分布", "各类土地在福建各县的分布"),
    ("timeline", "land_timeline.html", "逐年分布", "各类土地按年份的件数"),
    ("tx", "land_transactions.html", "交易方式", "卖、典、找价、赠送等"),
    ("units", "land_units.html", "计量单位", "亩分厘、受种、坵号、柱栏、两文元"),
    ("scale", "land_scale.html", "交易规模", "金额与面积的分布"),
    ("lin", "lin_wankai_case.html", "林萬開个案", "交易占家庭田产的比例"),
    ("minhou", "minhou_prices.html", "闽侯房价田价", "1805–1935 年逐年散点"),
    ("permu", "field_price_per_mu.html", "田每亩价格", "田面、田根、根面全的单价"),
    ("events", "events_evidence_timeline.html", "事件与证据", "历史事件对照时间线"),
]
data = {}
for key, fn, *_ in PAGES:
    with open(os.path.join(ROOT, fn), encoding="utf-8") as f:
        data[key] = f.read()
nav = [{"k": k, "fn": fn, "name": n, "desc": d} for k, fn, n, d in PAGES]
with open(os.path.join(HERE, "index_template.html"), encoding="utf-8") as f:
    tpl = f.read()
# 防止页面内容里的 </script> 提前结束外层脚本
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
out = tpl.replace("__NAV__", json.dumps(nav, ensure_ascii=False)).replace("__PAGES__", payload)
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(out)
print("wrote", os.path.join(ROOT, "index.html"), len(out), "chars")
