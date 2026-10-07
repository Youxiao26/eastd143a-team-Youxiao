# 閩中契約 · Minzhong Land Deeds

匹茲堡大學圖書館藏 **Chinese Land Records（1584–1978，235 件）** 的結構化數據集與分析站點。

**→ 網站：** <https://youxiao26.github.io/eastd143a-team-Youxiao/minzhong-land-deeds/>
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

本專案在倉庫中分為「站點輸出」與「源碼」兩處，各自以專案名作目錄，
與其他組員的個案互不干擾：

```
docs/minzhong-land-deeds/        GitHub Pages 輸出
  index.html                     分析站點（單檔，無外部依賴）
  data/                          全部數據集（亦為腳本的讀寫目錄）
projects/minzhong-land-deeds/
  README.md  LICENSE
  scripts/harvest.py             1. 採集（JSON:API）
  scripts/analyze.py             2. 解析、歸併、網絡與字輩抽取
  scripts/extract_prices.py      3. 自 OCR 抽取貨幣與價格
  scripts/build_site.py          4. 生成 index.html
```

重跑全流程：

```bash
cd projects/minzhong-land-deeds
python3 scripts/harvest.py      # 約 15 秒，5 次請求
python3 scripts/analyze.py
python3 scripts/extract_prices.py          # 可傳入 OCR 目錄，預設為 ../../../students_documents/OCR_results
python3 scripts/build_site.py
```

`extract_prices.py` 必須在 `build_site.py` 之前跑；
若 `data/prices.json` 不存在，站點會自動略去「貨幣與價格」一節，其餘照常生成。

`docs/minzhong-land-deeds/data/county_normalization.json` 是**人工考訂**的歷史政區歸併表（沿革依據見其中 `note` 欄），
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
| `prices_mentions.csv` | 383 條金額陳述，逐條附原文脈絡 |
| `prices_records.csv` · `prices.json` | 逐件主價格（116 件）與幣種 |

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

## 貨幣與價格

課程另行提供了這批文書的 **OCR（HTML，407 頁，覆蓋 235 件中的 234 件）**，
`scripts/extract_prices.py` 據此抽出正文中的金額陳述，與主表以 `pid` 對接；
結果呈現於站點[第五節](https://youxiao26.github.io/eastd143a-team-Youxiao/minzhong-land-deeds/#prices)，
含分期幣種構成圖、金額對數散點圖、折算率表與全部 116 件的可覆核明細。

**抽取流程**

1. 去標籤、壓掉 OCR 的退化重複（同一短語連印數十次是這批 OCR 的常見故障）。
2. 以「數字＋單位」連寫式掃出金額：`兩/錢/分/厘`、`元/員/圓/角/毫`、`文/千文/貫`。
   大寫數字（壹貳叁…）與常見 OCR 混淆（壺→壹、式→貳）一併歸一。
3. **錢文的「千」是單位不是位值**：「壹百壹拾伍千文」＝115,000 文，
   「肆拾壹千陸百文」＝41,600 文——按通常中文數字規則會分別誤讀成 5,110 與 1,640，故另寫 `cash2num()` 處理。
4. 以金額**前方最近、最長**的線索詞定用途：`price_sale`／`price_pawn`（典價）／
   `price_supplement`（增找、湊斷）／`redemption`（取贖）／`tax`／`fee`（紙價、中用、罰金）／
   `rent`／`rate`（每兩折錢若干）／`loan`／`other`。幣名（國幣、人民幣、洋銀）本身不說明用途，
   只在無其他線索時作最後依據。
5. 兩個標記欄：`scope` 區分契約正文與契紙上印的**章程布告**（383 條中 84 條是法規條文，
   如「處五元以上五十元以下之罰金」，不可當成交易價）；`confidence` 標出數字串本身可疑者
   （如「壹柒千伍百兩」這類相鄰數字字，多為 OCR 誤識）。
6. 逐件主價格取**契內複述最多**的那個數（契約正文與收訖批文常重複同一價），同票取大。

**結果**

116 件可定主價格，按計價幣種分期：

| 期 | 兩 | 元 | 文 | 兩價中位 |
|---|---:|---:|---:|---:|
| 清前期 –1795 | 7 | 0 | 0 | 18.0 兩 |
| 嘉道咸同 1796–1874 | 18 | 1 | 5 | 25.9 兩 |
| 光宣 1875–1911 | 21 | 3 | 5 | 32.0 兩 |
| 民國 1912–1948 | 8 | 31 | 4 | 42.0 兩 |
| 1949 後 | 0 | 6 | 0 | — |
| 無年 | 2 | 2 | 3 | — |

（民國欄剔除 1 條低可信數字；該期 8 件銀兩契中 5 件是 1913 年驗契證上回填的**舊契原價**，
不代表民國當年的成交價。各期 n 皆在 20 上下，中位數只能看趨勢方向，不宜作價格指數。）

**一、計價單位在民國初年整體翻轉。** 清代 60 件計價文書中 56 件用銀兩或銅錢、僅 4 件用銀元；
民國 43 件中 31 件用元、僅 8 件仍用兩。這不是物價問題而是**記帳本位的更替**：
同一批鄉里契約，從「紋廣銀肆拾兩」改寫為「大洋貳佰貳拾員」。

**二、銀兩契約自報成色，銀元契約不報。** 清契的銀數幾乎都跟著成色或平砝說明——
`紋銀`／`紋廣`／`庫平`／`足色`／`九四星色`／`平戥九七色`／`大錠庫錫`（38 處，見於 25 件），
番銀則標單枚重量（「每員陸錢叁分重」）。民國的 `大洋`／`國幣` 不再附註，
因為鑄幣已把成色鎖死在幣面上——**信用從當事人議定的成色轉移到了發行者**。

**三、契內自帶匯率。** 11 件文書寫明銀錢折算：「每兩一捌百文」「每兩銀折銅錢柒百伍拾文」
「每兩折錢捌百肆拾文算贖」，可用的 10 條落在 750–1,800 文／兩，多數在 800–850。這些是**當事人用的**折算率，
不是市場牌價，但給了跨幣種比較的內部依據（見 `prices_mentions.csv` 中 `category=rate` 者）。

**四、1945 後的數字不是價格而是通脹。** 國幣壹佰萬元（1947）、人民幣捌拾萬元（1954 典價）、
人民幣壹佰捌拾萬元——舊人民幣 1955 年以一萬比一折新幣，故這些數並不說明地價上漲。

**覆核**：`prices_mentions.csv` 每條都附 `raw`（原文數字串）與 `context`（前後文），可逐條回查。

**未定價的 119 件**：47 件稅單／執照／契證中 42 件本就不載價；100 件完全未抽到金額者多為
OCR 殘損、單頁契尾或純執照；另有 10 條金額落入 `other`，多為分家文書中的按年攤派錢文。

## 重要限制

- **館方不提供全文。** 該館藏的 `media--extracted_text` 為空，契約正文僅存在於影像中；
  網絡、字輩與政區分析均**基於編目元資料**。價格部分另據課程提供的 OCR，見上節。
- **OCR 品質不均。** 部分頁面有整段退化重複、人名地名錯字、數字串殘缺。
  金額抽取因此是**有召回損失的**：235 件中僅 116 件可定主價格，其中 1 件標為低可信。
  未抽到不等於文書未載價。
- **價格不可跨幣種直接比較。** 兩、元、文並存，成色與平砝各異，
  本專案**不做統一換算**，僅按幣種分列；契內自載的折算率另存一欄供參。
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
