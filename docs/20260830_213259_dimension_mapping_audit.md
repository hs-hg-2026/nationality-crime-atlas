# Canonical dimension mapping audit — 2026-08-30

## Outcome

取得・quality検証済み5 edition、合計913,237 normalized rowから、612件のdistinct source dimensionを抽出した。結果は`matched` 578、`ambiguous` 26、`unmatched` 8である。

このmappingは**label/category crosswalkだけ**を表す。`matched`であっても、犯罪統計のpopulation scope、在留人口、期間、地理semanticが統計的に一致するとは判断しない。その適否は次工程のindicator contractでsource pairごとに判定する。

## Inputs and provenance

- source artifact catalog: `data/processed/_catalog/artifacts.jsonl`
- catalog SHA-256: `01684f9d0595089062239bcfa84a669396917dabc35b63034b43fb70c3aa09b7`
- authored rules: `config/dimension_mappings.json`
- rule SHA-256: `253b1af9932b12aeb6288b2fe70c8950c3fd0c5de719bf36e5d2d111e1b8e6c3`
- generated mapping: `data/processed/_mappings/20260830_213259_dimension_mapping/`
- generated input count: 913,237 normalized row
- canonical reference: ISA国籍・地域197 code、都道府県等48 code

ISA 2024年末と2025年末のcodeを比較したところ、2024年の196 code/labelは2025年にも同一labelで存在し、2025年には`02_092：モナコ`が1区分追加されていた。既存codeのlabel driftは0件だった。

## Status contract

| Status | 意味 |
|---|---|
| `matched` | source label/codeがcanonical category 1件へ明示的に対応する |
| `ambiguous` | 複合category、aggregate、または異なる粒度で、単一の同値categoryへ還元できない |
| `unmatched` | 公表情報からcanonical targetを確定できない |

fuzzy match、推計、按分は使用しない。raw source label、row kind、region、subcategory、geography type、parent region、geography semanticsをmapping rowに保持する。

## Results by source

| Source | Matched | Ambiguous | Unmatched | 主な内容 |
|---|---:|---:|---:|---|
| `S14` | 245 | 0 | 0 | 197国籍・地域＋48都道府県等 |
| `S14_2024_12` | 244 | 0 | 0 | 196国籍・地域＋48都道府県等 |
| `S08` | 22 | 7 | 4 | 表130の国籍・region・subcategory |
| `S09` | 19 | 7 | 4 | 表131の国籍・region |
| `S02` | 48 | 12 | 0 | 日本全国＋47都道府県、7警察region、5北海道方面 |

### Ambiguous 26件

- `S02`: `中国`、`中部`、`九州`、`四国`、`東北`、`近畿`、`関東`の7警察region。
- `S02`: `函館方面`、`北見方面`、`旭川方面`、`札幌方面`、`釧路方面`の5 police subregion。
- `S08`／`S09`: それぞれ5 source region total。
- `S08`／`S09`: `韓国・朝鮮`。ISAの`韓国`と`（朝鮮）`を一つに潰さない。
- `S08`／`S09`: `中国`。同名のISA `中国`が存在しても、NPA注記が台湾・香港等を含むためexact matchにしない。known targetとして`中国`と`台湾`を記録するが、完全な同値集合とは扱わない。

### Unmatched 8件

- `S08`／`S09`: context別の`その他`が各3件。bucket membershipが公表されていないため推測しない。
- `S08`／`S09`: `国籍不明`が各1件。ISA表に対応する国籍categoryを確認できない。

### Matchedの境界

- `S02`の47都道府県labelはISAの47都道府県codeと1対1で対応した。
- NPA `アメリカ`→ISA `米国`、NPA `イギリス`→ISA `英国`はauthored aliasとして1対1対応した。
- `日本`は`jp:all`というderived national aggregateへ対応するが、単一のISA prefecture source codeではない。
- 表13はmapping後も`police_reporting_area_unresolved`を保持する。都道府県名が一致しても、居住地・発生地と読み替えない。

## Verification

- RED: production module未実装時の`ModuleNotFoundError`を確認。
- GREEN: mapping unit/integration/CLI 15 test成功。
- full suite: 62 test成功、skip 0、branch計測total coverage 85.71%。
- production run: 612 mapping rowに重複なし。47 prefecture mappingは全件matched、population self-mappingのnon-matchedは0件。
- generated `summary.json`と`dimension_mappings.jsonl`は`latest.json`記載のSHA-256と一致した。

## Next

X/Y/Zを別indicatorとしてregistry化し、分子・分母・period・population scope・geography semantics・nationality grouping mismatchを契約へ固定する。mapping statusだけを根拠にratio計算を許可しない。
