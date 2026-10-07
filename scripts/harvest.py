#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤 1／3：从 Pitt ULS 的 JSON:API 采集 Chinese Land Records 全部元数据。

平台为 Islandora 2 / Drupal 11，JSON:API 公开免 token。
注意两点（见 README「踩过的坑」）：
  * User-Agent 不可含 harvest 等词，否则被 nginx bad-bot 过滤拒为 502
  * 必须用 sparse fieldset，否则单笔约 17KB，整页易超时
"""
import json, os, sys, time, urllib.parse, urllib.request

BASE = "https://digital.library.pitt.edu"
COLLECTION_UUID = "6985ef8a-1fe9-4b46-91ee-e14ba00d0822"
UA = "EASTD143A-coursework/1.0 (academic research)"
FIELDS = ",".join([
    "title", "field_date_str", "field_edtf_date", "field_pid", "field_extent",
    "field_source_location", "drupal_internal__nid", "path",
])
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "docs", "data")


def get(url, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/vnd.api+json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as exc:
            print(f"   retry {i+1}/{tries}: {exc}", file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise SystemExit("harvest failed after retries")


def main():
    q = {"filter[field_member_of.id]": COLLECTION_UUID,
         "fields[node--islandora_object]": FIELDS,
         "page[limit]": "50"}
    url = f"{BASE}/jsonapi/node/islandora_object?" + urllib.parse.urlencode(q)
    items, page = [], 0
    while url:
        d = get(url); page += 1
        items.extend(d.get("data", []))
        print(f"  page {page}: total {len(items)}", file=sys.stderr)
        url = d.get("links", {}).get("next", {}).get("href")
        if url:
            time.sleep(1.5)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "raw_items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f"harvested {len(items)} items -> docs/data/raw_items.json")


if __name__ == "__main__":
    main()
