# Deep Research比較・採否・実装影響

**確認日:** 2026-08-30 JST  
**対象:** 2015年以降の外国人犯罪統計・在留外国人統計のprovenance、schema、定義、取得経路、indicator contract  
**位置付け:** user-provided Deep Research 2本を比較し、load-bearing claim（結論を支える重要主張）だけを一次資料と取得済みbinaryで再確認したauthored review。`inbox/`の原文は変更していない。

## 1. 入力とverification label

- Claude Opus 5 report: [inbox source](../inbox/20260830_174918_compass_artifact_wf-1be02b71-814f-5876-bfed-82fb88a99ccb_text_markdown.md)
- ChatGPT 5.6 sol report: [inbox source](../inbox/20260830_181535_report.md)
- 既存project audit: [source availability audit](./20260830_085603_source_availability_audit.md)

本reviewでは次のlabelを使う。

| Label | 意味 |
|---|---|
| **検証済み—binary** | 公式binaryを実際に読み、hash・cell・sheet等を確認した |
| **検証済み—primary** | 官庁/e-Stat/e-Govの一次page・文書を実際に開いて確認した |
| **部分検証** | 代表年または代表資料のみを一次確認した。全年度への一般化は未検証 |
| **report-only** | 持ち込みreportにはあるが、本reviewでは一次資料を再取得していない |
| **design decision** | data上の事実ではなく、このprojectが選ぶ仕様 |
| **未解決** | 一次資料から一意に確定できなかった |

## 2. Executive judgment

1. **実装材料としてはChatGPT 5.6 sol版を主に採用する。** 現行4 binaryのSHA-256、sheet dimensions、表番号・format transition、e-Stat `statInfId`、definition caveatが具体的で、project側の独立取得結果と一致した。
2. **Claude版は調査質問と高水準のcaveat整理には有用だが、地理・Z・format・completion判定には過剰な断定がある。** そのままregistryやUI labelへ転記しない。
3. **第13表の地理は現行実装の `police_reporting_area_unresolved` を維持する。** 「検挙した都道府県警察の管轄区域」と全列に一律断定する根拠は足りず、刑法犯と特別法犯で原票の帰属手続が異なる可能性がある。
4. **X/Yの次のsame-year pairは2024年表130/131 × 2024年末T1である。** 現在取得済みのS14は2025年末なので、2024年分母 `statInfId=000040292372` を先に追加する。Zは2025年表13 × 2025年末T1でsame-year pairを構成できる。
5. **scaleはdata factではない。** canonical layerでは無次元の `numerator / denominator` とraw numerator/denominatorを保持し、`×1,000` / `×100,000` はdisplay metadataにする。倍率を変えても統計的不安定性は変わらない。
6. **国籍crosswalk不一致は、projectの既決方針上、常にhard refusalとはしない。** exact crosswalk indicatorでは拒否する一方、raw-label/source-pair indicatorは明示的なmismatch flag付きで計算可能にする。推計・按分・fuzzy matchはしない。

## 3. Claim matrix

| Claim | Claude | ChatGPT 5.6 sol | 独立確認 | 採否・実装影響 |
|---|---|---|---|---|
| 現行S08/S09はNPA 2024表130/131 | landing確認、binary未取得 | binary取得・parse | **検証済み—binary/primary** | 採用 |
| 現行S02は2025確定値の第13表 | metadata確認 | binary取得・parse | **検証済み—binary/primary** | 採用 |
| 現行S14は2025-12 T1、hidden raw sheetあり | metadata確認 | binary取得・parse | **検証済み—binary/primary** | 採用 |
| 表130/131は2015–2019が旧132/133、2020–2024が130/131 | 年別番号は未照合 | exact matrix | H27/R01/R02/R06を**部分検証** | transition採用。全年度binary fingerprintは未完 |
| 表13は2015が表11、2016以降が表13 | 未照合 | exact `statInfId` matrix | 2015/2025を**部分検証** | matrixはcandidate registryへ。全IDを順次pin |
| T1/fallbackで2015–2025の都道府県×国籍人口を継続できる | 年次粒度が粗い | exact T1/fallback matrix | 2015/2021 fallback、2024/2025 T1を**部分検証** | feasible。adapterはschema fingerprint単位で追加 |
| 第13表地理は「検挙した警察の管轄区域」 | 確定と表現。ただし表13固有注記は未確認 | 単一semantic未解決 | **未解決**。細則とbinary注記を照合 | Claudeの断定を不採用。現行label維持 |
| NPA 2024「中国」は台湾・香港等を含む | 二次手掛かり中心 | binaryで確認 | **検証済み—binary/primary** | current crosswalkにflag必須 |
| China groupingはX/Y/Zすべてに影響 | 影響すると記載 | Zはaggregate nationality | 第13表に国籍dimensionなし | **誤り。** X/Yには影響、Zには影響しない |
| 参考比率scaleは10万人当たり | 推奨 | 1,000人当たり推奨 | どちらもdesign choice | canonical ratioとdisplay scaleを分離 |
| `-` を一律0または秘匿にできない | binary未確認 | column/source依存と警告 | current T1には`-`なし。historical未確認 | historical adapterでraw value/statusを保持 |
| 2025全国表130/131は未公表 | 明確なmatrixなし | cutoff時点で未公表 | 2026-08-30の公式検索でR07詳細年報を確認できず | current X/Yは2024まで。定期監視対象 |

## 4. Load-bearing verification

### 4.1 現行binary identity

手元の公式取得fileを再hashし、ChatGPT版appendixの値と一致した。

| Source | Local artifact | SHA-256 | Status |
|---|---|---|---|
| S02 | 2025確定値 犯罪統計・第13表を含むworkbook | `0404e10b0ab45b35f9be86c7b748bb039469cff2efc63584b2ac9660056b7323` | **検証済み—binary** |
| S08 | R06_130.xlsx | `23ccb60d89c9b4bdaa898105753506a61d8354a0ae87b01598f6c97f4efd6a83` | **検証済み—binary** |
| S09 | R06_131.xlsx | `70d180220c3b53cd5d832acb1c86460b005c47215c0409c7b14ea0f0057a2e30` | **検証済み—binary** |
| S14 | 25-12-t1 | `3a7c603c42927fc441ba0c062777223754d238df904bd15a034220dffd229a86` | **検証済み—binary** |

S02のdownloadは`.xlsx`風の扱いを受け得るが、実体はOLE2/legacy XLSである。現行parserがmagic byteで判定する方針は正しい。e-StatはS02を2025確定値、公開日時2026-02-12 10:00として掲載している。[e-Stat S02](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040410682)

S14はvisible `PVT`（204×199）とhidden raw sheet（468,642×7）を持ち、raw headerは国籍・地域、在留資格、性別、年齢階級、年齢、都道府県、在留外国人数である。e-Stat metadataは表番号`25-12-t1`、対象2025年12月、公開日時2026-07-10 10:00を示す。[e-Stat S14](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040472265)

### 4.2 National table transition

NPA official landingで代表年を照合した。

| Period | Table numbers | Format | Verification |
|---|---|---|---|
| 2015 | 132（外国人）/133（来日外国人） | XLS | **検証済み—primary** ([H27 landing](https://www.npa.go.jp/toukei/soubunkan/h27/h27hanzaitoukei.htm)) |
| 2019 | 132/133 | XLSX | **検証済み—primary** ([R01 landing](https://www.npa.go.jp/toukei/soubunkan/R01/R01hanzaitoukei.htm)) |
| 2020 | 130/131 | XLSX | **検証済み—primary** ([R02 landing](https://www.npa.go.jp/toukei/soubunkan/R02/R02hanzaitoukei.htm)) |
| 2024 | 130/131 | XLSX | **検証済み—binary/primary** ([R06 landing](https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm)) |

したがってChatGPT版の大区分は採用できる。ただし2016–2018、2021–2023を含む各年binaryのsheet/header/hashは、production registryへpinするときに個別確認する。

### 4.3 Table 13 geography

Claude版の根拠である犯罪白書には、特定の「都道府県別の刑法犯検挙人員と人口比」について、検挙した都道府県警察の管轄区域によるとの注記が実在する。[令和元年版犯罪白書](https://hakusyo1.moj.go.jp/jp/66/nfm/n66_2_2_1_1_1.html)

しかし、これを第13表の全columnへそのまま移すことはできない。

- [犯罪統計細則](https://www.npa.go.jp/laws/notification/1971kunrei16-soubunkan.pdf)第7条は、刑法犯認知票を最初に扱った警察官、その他の原票を主たる処理を行った警察官が作るとする。
- 同第9条は、刑法犯検挙情報を、既存の認知票を報告した警察署、または未報告なら発生地を管轄する警察署へ通知し、その署が警察庁へ報告する仕組みを定める。
- current第13表は「刑法犯・特別法犯」combined、刑法犯、特別法犯を同時掲載する。実binaryの第13表sheetには地理帰属の固有注記がなく、特別法犯sheetの注記は交通関係の除外だけである。

**結論（evidence-backed inference）:** 地理rowは「警察統計上の都道府県等別集計区分」と安全にlabelできるが、犯罪発生地・認知票所属・主たる取扱警察・検挙警察のいずれか一つに全metricを統一して断定できない。被疑者居住地ではない可能性が高いが、`police_reporting_area_unresolved`を維持し、照会はenrichment trackに残す。

### 4.4 Population scope and nationality grouping

[出入国在留管理庁の用語解説](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040472267&fileKind=2)は、`在留外国人 = 中長期在留者 + 特別永住者`、`総在留外国人 = 在留外国人 + 3月以下・短期滞在・外交/公用等`と区別する。denominatorは前者を使い、後者へsilent substitutionしない。

[利用上の注意](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040472268&fileKind=2)によれば、ISA統計は台湾を2012年末から中国と別に集計し、韓国・朝鮮を2015年末から分離している。current T1 raw sheetでも`01_022：台湾`と`01_023：中国`は別labelで、香港単独labelは確認できなかった。

一方、NPA 2024 binaryは次を明記する。

- 表130: `「中国」には、台湾、香港等を含む。`
- 表131: 同じ注記。加えて、`来日外国人`は表129脚注を参照し、交通業過・交通法令違反を除外。
- 表129: `来日外国人`は定着居住者、在日米軍関係者、在留資格不明者を除く。[R06 chapter 26](https://www.npa.go.jp/toukei/soubunkan/R06/pdf/R06_26.pdf)

従ってNPA `中国`とISA `中国`のlabel-to-label joinは不正確である。NPAの`等`の完全な構成が不明なため、`ISA中国 + 台湾`もexact crosswalkとは断定しない。

ただし、userが確定したpublication policyは「一致する分子を待つ」のではなく、公開source pairを明示した参考比率を出すことである。そのため実装は二層にする。

1. `crosswalk_status=exact` indicator: 対応集合が完全な場合だけ公開。
2. `crosswalk_status=as_published_mismatch` indicator: numerator raw label、denominator component list、未解決点を常時表示し、推計せず単純除算。UIでexactと同列に見せない。

### 4.5 Same-year pairing

現在の取得済みartifactは、S08/S09が2024 annual flow、S14が2025-12-31 stockである。これを「2024年参考比率」として直接結合してはいけない。

- X/Y: 2024表130/131 × 2024-12-31 T1 `statInfId=000040292372`。[e-Stat 24-12-t1](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040292372)
- Z: 2025第13表 × 2025-12-31 T1 `statInfId=000040472265`。

同年のannual flowとyear-end stockであっても母集団・時間構造は一致しないため、`annual_flow_vs_point_in_time_stock`は残す。

### 4.6 `検挙人員` and value status

e-Statのofficial definitionは、刑法犯検挙人員を「警察において検挙した事件の被疑者の数」とする。[e-Stat definition K](https://www.e-stat.go.jp/koumoku/koumoku_teigi/K) 年間のunique offender risk populationであるとの保証は確認できないので、UIは`人`と表示しても、metadataでは`cleared_person_records`相当として母集団不一致を警告する。

current T1 raw dataで`-`は観測されず、468,641 data rowはpositive countだった。よって現行S14 smoke testに問題はない。一方、historical fallback表の`-`、blank、non-publicationを一律に`0`または`suppressed`へ変換してはいけない。adapterごとに`raw_value`と`value_status`を保存し、意味を確認できないものは`missing_unknown`にする。

## 5. Report quality assessment

### ChatGPT 5.6 sol版

**採用できる点**

- 現行4 binaryのhashとschema記述がlocal evidenceに完全一致。
- national tables、Table 13、T1/fallbackの年次matrixが具体的。
- Table 13 geographyをsingle semanticに潰さず、47 prefecture filteringを明示。
- `在留外国人` / `総在留外国人`、flow/stock、来日外国人/residentの違いをcontractへ落としている。
- raw preservation、fingerprint、revision、publish gateの設計が現行offline pipelineと整合。

**そのまま採用しない点**

- `per 1,000`推奨はdesign proposalでありfactではない。
- 2023–2024 Chinaを常にhard refusalとする仕様は、user-approved publication policyより厳しい。exact indicatorとmismatch indicatorを分ける。
- 「12 adapterを先に全部実装」は大きすぎる。verified binaryからschema fingerprintを作り、current same-year MVP → historical backfillの順に進める。
- full year matrixは本reviewで全binaryを再取得していないため、candidateとしてregistryに入れ、edition pin時に再検証する。

### Claude Opus 5版

**採用できる点**

- source別definitionを表示し、official crime rateと呼ばない方針。
- NPA/ISAのChina category conflict、Table 13照会文案、revision monitoringの問題提起。
- binary未取得・旧ID未照合を自ら明示している。

**不採用または修正が必要な点**

- Table 13 geographyを「確定」としつつ表13固有注記未確認としており、epistemic labelが矛盾する。
- Zはnationality aggregateなのでChina groupingの影響を受けない。
- S02 current artifactをXLSX系として扱う記述は、実体legacy XLSと不一致。
- `per 100,000`の方がsmall denominatorの不安定性を抑えるような説明は誤り。倍率は不安定性を変えない。
- completion criteriaの「verified registry」はlanding-levelであり、binary-level verificationとは区別が必要。

## 6. Accepted implementation rules

以下は、既存方針・一次確認・両reportの有用部分を合わせたworking rulesである。

1. source registryを`series`とimmutable `edition`へ分け、editionにperiod、publication time、revision status、stable ID、landing/download URL、hash、schema fingerprintを持たせる。
2. parserは年番号ではなくverified `schema_version`へdispatchする。未知fingerprintは自動推測せず停止する。
3. source labelとraw cellを保存した後にcanonical mappingを適用する。unknown labelをfuzzy matchしない。
4. Zはcanonical 47都道府県だけを計算対象にし、全国計、管区計、北海道方面、市区町村を除外する。
5. Table 13 geographyは`police_reporting_area_unresolved`。UIは「都道府県等別（警察統計上の集計区分）」とする。
6. ratio outputはraw numerator、raw denominator、unscaled quotient、display multiplier、source pair、period、mismatch flagsを同じrecordから辿れるようにする。
7. hard refusalはmissing/non-numeric、denominator ≤ 0、period identity不明、unknown schema、duplicate、Z geography不正等に限定する。
8. population scope、flow/stock、police geography/residence geography、nationality grouping等は常時表示するsoft mismatch。exact crosswalkを名乗る場合のみcrosswalk ambiguityをhard refusalにする。
9. raw countはderived ratioがrefuseでも公開可能。存在しないnationality × prefecture numeratorは生成しない。
10. current same-year MVPを先に成立させ、historical 2015–latestはedition/binaryごとにbackfillする。

## 7. 次のTODO（実行順）

1. **source registry v2を設計・test-first実装**: `series` / `edition`分離、stable IDs、publication/revision/hash/schema fingerprintを追加。
2. **2024-12 T1を取得・snapshot・parse・validate**: S08/S09とsame-year X/Y pairを作る。既存2025 T1はZ用に維持。
3. **current canonical mappingを実装**: 47 prefecture crosswalk、NPA/ISA nationality raw labels、`crosswalk_status`、value status。
4. **6 indicator contractをconfig化**: X/Y/Z × cases/persons。unscaled ratioとdisplay scaleを分離し、hard refusal/soft mismatchをtestする。
5. **current formal production run**: X/Y 2024、Z 2025を計算し、raw numerator/denominator、provenance、mismatch flagsをinspection tableに出す。
6. **official discovery/downloaderを追加**: landing/catalogからeditionを解決し、直URLの年置換をしない。same-ID hash変更をrevisionとして停止・reviewする。
7. **historical registryをedition単位で検証**: ChatGPT版のexact ID matrixをcandidateにし、2015→latestをbinary hash/schema fixture付きでpinする。
8. **historical adapter/backfill**: current schemaに近い年から追加し、fallbackの`-`/blank semanticsとaggregate reconciliationをyear-specific testで守る。
9. **visualization MVP**: countと参考比率を切替え、source pair・算式・mismatchを同じ画面から開けるようにする。
10. **enrichment track**: NPAへTable 13地理とChina `等`の完全定義、ISAへsparse row semanticsを照会。MVP blockerにはしない。

## 8. Historical candidate IDs retained from the reports

具体情報を失わないため、ChatGPT版で提示されたIDをここに保持する。ただし、本reviewで一次pageまたはbinaryを再確認していない行は**report-only candidate**であり、production pinではない。

### NPA/e-Stat Table 13 series

| Year | Table | `statInfId` | Review status |
|---:|---:|---|---|
| 2015 | 11 | `000031368126` | **検証済み—primary** |
| 2016 | 13 | `000031530270` | report-only candidate |
| 2017 | 13 corrected | `000031672741` | report-only candidate |
| 2018 | 13 corrected | `000031797656` | report-only candidate |
| 2019 | 13 | `000031911224` | report-only candidate |
| 2020 | 13 | `000032049031` | report-only candidate |
| 2021 | 13 | `000032168154` | report-only candidate |
| 2022 | 13 | `000040015380` | report-only candidate |
| 2023 | 13 | `000040141107` | report-only candidate |
| 2024 | 13 | `000040247461` | report-only candidate |
| 2025 | 13 | `000040410682` | **検証済み—binary/primary** |

### ISA denominator series

| Year end | Source form | `statInfId` | Review status |
|---:|---|---|---|
| 2015 | 第4表 fallback | `000031399580` | **検証済み—primary** via official e-Gov catalog |
| 2016 | T1 | `000040281956` | report-only candidate |
| 2017 | T1 | `000040281959` | report-only candidate |
| 2018 | T1 | `000040281962` | report-only candidate |
| 2019 | 第4表 fallback | `000031964919` | report-only candidate |
| 2020 | 第4表 fallback | `000032104295` | report-only candidate |
| 2021 | 第3表の1 fallback | `000032213255` | **検証済み—primary** via official e-Gov catalog |
| 2022 | T1 | `000040068664` | report-only candidate |
| 2023 | T1 | `000040186956` | report-only candidate |
| 2024 | T1 | `000040292372` | **検証済み—primary** |
| 2025 | T1 | `000040472265` | **検証済み—binary/primary** |

## 9. Official sources used in this review

All accessed 2026-08-30.

1. [NPA R06 annual crime landing](https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm)
2. [NPA R06 foreign crime chapter](https://www.npa.go.jp/toukei/soubunkan/R06/pdf/R06_26.pdf)
3. [NPA Crime Statistics Detailed Rules](https://www.npa.go.jp/laws/notification/1971kunrei16-soubunkan.pdf)
4. [Ministry of Justice 2019 Crime White Paper](https://hakusyo1.moj.go.jp/jp/66/nfm/n66_2_2_1_1_1.html)
5. [e-Stat 2025 finalized crime statistics](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040410682)
6. [e-Stat 2025-12 resident-foreigner T1](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040472265)
7. [ISA terminology notes](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040472267&fileKind=2)
8. [ISA usage notes](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040472268&fileKind=2)
9. [e-Stat 2024-12 resident-foreigner T1](https://www.e-stat.go.jp/stat-search/files?stat_infid=000040292372)
10. [NPA H27 annual crime landing](https://www.npa.go.jp/toukei/soubunkan/h27/h27hanzaitoukei.htm)
11. [NPA R01 annual crime landing](https://www.npa.go.jp/toukei/soubunkan/R01/R01hanzaitoukei.htm)
12. [NPA R02 annual crime landing](https://www.npa.go.jp/toukei/soubunkan/R02/R02hanzaitoukei.htm)
13. [e-Stat 2015 finalized crime statistics](https://www.e-stat.go.jp/stat-search/files?stat_infid=000031368126)
14. [NPA current crime-statistics index](https://www.npa.go.jp/publications/statistics/sousa/statistics.html)
15. [e-Stat statistical-definition catalog K](https://www.e-stat.go.jp/koumoku/koumoku_teigi/K)
16. [e-Gov 2015 prefecture × nationality resident-foreigner table](https://data.e-gov.go.jp/data/dataset/moj_20160628_0024/resource/ba6fbe31-93f4-4113-a607-787d736aca07)
17. [e-Gov 2021 municipality × nationality resident-foreigner table](https://data.e-gov.go.jp/data/dataset/moj_20230119_0011/resource/f8d67064-0802-44b3-9db9-ac82df90a2cd)
18. [NPA terms of use](https://www.npa.go.jp/rules/index.html) and [e-Stat terms of use](https://www.e-stat.go.jp/terms-of-use)

## 10. Verification boundary

**検証済み:** 2本の全文、current 4 binaryのhash、current notes/schema、current/representative official landing metadata、Table 13 geographyに関係する細則、2024/2025 denominator metadata。  
**部分検証:** 2015–2025のfull continuity matrix。具体IDは保持したが、全binaryのhash・sheet・noteはまだpinしていない。  
**未解決:** 第13表の全metricに共通する単一地理semantic、NPA `中国`の`等`の完全集合、historical sparse/`-` semantics、UIのdefault display multiplier。  
**未実施:** 外部機関への照会、automatic downloader、historical full backfill、indicator calculation。
