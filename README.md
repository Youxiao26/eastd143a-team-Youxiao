# 閩中契約 · Minzhong Land Deeds

匹茲堡大學圖書館藏 **Chinese Land Records（1584–1978，235 件）** 的結構化數據集與分析站點。

**→ 網站：** <https://youxiao26.github.io/eastd143a-team-Youxiao/>
（需先由倉庫管理員在 Settings → Pages 將來源設為 `main` 分支的 `/docs` 目錄）

這批文書以福建中部（福州府一帶）為主，包含官契、民契、稅單、執照與分家文書。
本專案把館方以自由文字記錄的編目還原為可計算的結構，據以考察歷史政區、宗族網絡與國家契約管控的變化。
EASTD 143A《東亞人文的數位工具與方法》課程個案。

---

## 三個主要結果

**一、縣名歸併改變了整批材料的面貌。**
原編目有 38 種地名寫法。閩縣與侯官縣於 1913 年合併為閩侯縣，1943 年改名林森縣，1950 年復名——
四個名字指的是同一片土地。歸併前最大的單一「縣」為 37 件；歸併後閩侯單元合計 **90 件，占全藏 38%**。

**二、字輩是重建宗族的最強線索。**
314 個當事人散成 104 個互不相連的小簇，沒有貫通全藏的大網。
但同姓且名第二字相同者（如陳欽瑞／陳欽隆）多為同輩族人：**32 組字輩涵蓋 72 人、75 件**。
陳欽瑞在 1932–36 年間四次買入、陳欽隆在 1936 年四次賣出，土地是在宗族內部重新分配，而非單向流失。

**三、官契比重隨時代單調上升。**
嘉道咸同期 58% → 民國期 82% → 1949 年後 96%。
但這條曲線不能直接讀作「國家管控強度」：鈐印納稅的官契存世率本就高於民間白契，且這是一批經兩次選擇的材料。

---

## 倉庫結構

```
docs/                GitHub Pages 輸出
  index.html         分析站點（單檔，無外部依賴）
  data/              全部數據集（亦為腳本的讀寫目錄）
scripts/
  harvest.py         1. 採集（JSON:API）
  analyze.py         2. 解析、歸併、網絡與字輩抽取
  build_site.py      3. 生成 index.html
```

重跑全流程：

```bash
python3 scripts/harvest.py      # 約 15 秒，5 次請求
python3 scripts/analyze.py
python3 scripts/build_site.py
```

`docs/data/county_normalization.json` 是**人工考訂**的歷史政區歸併表（沿革依據見其中 `note` 欄），
不由腳本生成；其餘數據檔案均可重建。

## 數據說明

| 檔案 | 內容 |
|---|---|
| `raw_items.json` | API 原始回應，未經處理 |
| `records.json` / `chinese_land_records_235.csv` | 235 件結構化主表 |
| `entities.json` | 413 條當事人記錄，含類型判定 |
| `network.json` · `network_components.json` | 人物網絡與分簇佈局 |
| `lineage_clusters.json` | 32 組字輩族群 |
| `spacetime.json` · `timeseries.json` · `period_summary.json` | 時空矩陣與官民契序列 |

當事人分為 `person`／`woman`（以「氏」稱）／`institution`（如老人會）／`government`／`surname_only` 五類。
**僅記姓氏者（15 處）不計入網絡**——文書未載全名時編目只記姓氏，若視為同一節點會憑空造出虛假的樞紐。

## 採集方法

平台為 **Islandora 2 / Drupal 11**，`JSON:API` 公開免 token，不需解析 HTML：

```
https://digital.library.pitt.edu/jsonapi/node/islandora_object
  ?filter[field_member_of.id]=6985ef8a-1fe9-4b46-91ee-e14ba00d0822
  &fields[node--islandora_object]=title,field_date_str,field_pid,path
  &page[limit]=50
```

跟 `links.next` 翻頁，五次取完 235 筆。

**兩個踩過的坑：**

1. **`User-Agent` 不可含 `harvest` 等詞。** 站點裝有 nginx bad-bot 過濾，含敏感詞的 UA 一律返回 502——
   諷刺的是，誠實標明用途反而被擋。改用 `EASTD143A-coursework/1.0 (academic research)` 即可。
2. **必須用 sparse fieldset。** 不加 `fields[]` 時單筆約 17 KB，整頁 880 KB，易間歇超時；加了降至約 1/25。

**影像**走 IIIF（Cantaloupe，Image API 2.0），manifest 位於 `/node/{nid}/manifest`，
原圖約 5776×8280，可用 `/full/1000,/0/default.jpg` 按需縮放。

## 重要限制

- **沒有全文。** 該館藏未提供 OCR 或釋文（`media--extracted_text` 為空），契約正文僅存在於影像中。
  本專案所有分析均**基於編目元資料，而非文書本身**，無法涉及田地面積、價銀、稅率等正文信息。
- **年代以起始年歸入。** 67 件日期為區間（如 `1946/1951`，代表一冊跨年文書）；11 件無日期。
- **地名未必是文書當時的行政名。** 部分 1913 年前的文書已被標為「閩侯縣」，顯示編目中存在以今名回標，
  故本專案按**地理單元**而非縣名統計。
- **這不是隨機樣本**，而是經原藏家與入藏機構兩次選擇的材料；比例性結論僅在這批文書內部成立。

## 權利

原館藏權利狀態為 **Copyright Undetermined**（未定），並非公有領域聲明。
本專案僅使用描述性元資料並連結回原始條目，**未轉載任何影像**。
如需公開發布影像，請先聯繫 University of Pittsburgh, Archives & Special Collections。

本倉庫的衍生數據與程式碼以 **CC0 1.0** 釋出，可自由用於教學與研究。

## 引用

> University of Pittsburgh Library System, *Chinese Land Records, 1584-1978*,
> EAL.2011.01, Archives & Special Collections.
> <https://digital.library.pitt.edu/collection/chinese-land-records>

政區沿革依據中文維基百科「閩侯縣」「永泰縣」條目。採集日期 2026-10-07。
