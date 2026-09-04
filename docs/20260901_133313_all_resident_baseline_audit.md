# 全住民を基準にする地域context — source・compatibility・実装audit

- 実施日: 2026-09-01
- 状態: **一次page・official binary・local pipelineで検証済み**
- 対象年: 2024年
- 結論: nationalityをdefault referenceにせず、日本に居住する全住民の地域contextをprimary baselineにする

## 1. 今回確定したproject requirement

このprojectは、特定の国籍を「通常」または「基準」として他の国籍を評価するためのものではない。国籍labelだけが数字の裏付けなく流通し、集団の本質や個人riskを示すかのような印象操作になることを避ける。公表数字をできるだけ正確に集め、比較可能な範囲と比較不能な範囲を分け、公正な可視化から事実ベースの対策につなげることを目的とする。

このため、UIとindicator設計では次を固定する。

1. primary regional baselineは`日本国籍`ではなく`日本に居住する全住民`とする。
2. 日本国籍を含む個別nationality comparisonは、direct dataまたは明示したderivationとして提供できる場合だけsecondary viewにする。
3. 公表されていない`個別国籍 × 都道府県`の犯罪分子を推計・按分しない。
4. nationality差・地域差を集団の本質、因果、個人の犯罪発生確率として説明しない。

## 2. Answer first

| 質問 | 判定 | 根拠 |
|---|---|---|
| 全住民の都道府県別人口は得られるか | **Yes** | 統計局の2024年10月1日人口推計を収録した警察庁表144。`総人口`は外国人を含む。 |
| 全体の都道府県別犯罪統計は得られるか | **Yes** | 警察庁表3の`刑法犯総数（交通業過を除く）`に認知件数、検挙件数、検挙人員がある。 |
| 2024年の全住民地域contextを作れるか | **Yes, descriptive context only** | 表3と表144は同年・同じ47都道府県labelで接続できる。ただしannual flow / 10月1日population、警察集計地域 / 居住人口、人口千人単位丸めを明示する。 |
| 日本国籍の犯罪分子がcurrent sourceに直接入っているか | **No** | S02/S08/S09に`日本`nationality rowはない。S15の`日本`はnational geographyであり国籍ではない。 |
| `国籍 × 都道府県`の犯罪分子は得られるか | **No, current routine official sourceでは未確認** | S08/S09はnationality別だが全国、S02は都道府県別だが来日外国人aggregate。 |
| 日本国籍をdefault comparatorにすべきか | **No** | 全住民contextを先に置く。日本国籍comparisonは必要な分析で明示的に選ぶsecondary comparatorとする。 |

## 3. 一次資料とbinary evidence

### S15: 全体の都道府県別犯罪統計

- 公表主体: 警察庁
- official landing: [令和6年の犯罪](https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm)
- official artifact: [R06_003.xlsx](https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_003.xlsx)
- 表題: `3 年次別 都道府県別 罪種別 認知・検挙件数及び検挙人員`
- 使用sheet / scope: `刑法犯総数` / `刑法犯総数（交通業過を除く）`
- 2024 national anchors: 認知737,679件、検挙287,273件、検挙人員191,826人
- parsed rows: 60 = national 1 + prefecture 47 + police region 7 + Hokkaido subregion 5
- SHA-256: `f1c597114874c1a0ba6b87e9a7d7fcbb48041defb7cb16a874c2c9542991d75b`
- local raw: `data/raw/npa-all-persons-prefecture-crime/S15/20260901_133201_s15/`
- local processed: `data/processed/npa-all-persons-prefecture-crime/S15/20260901_133201_s15/`

`都道府県別`は犯罪者の居住地を意味するとは確認できないため、normalized dataでは`police_reporting_area_unresolved`を維持する。

### S16: 全住民の都道府県別人口

- NPA official artifact: [R06_144.xlsx](https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_144.xlsx)
- 表題: `144 年次別 都道府県別 人口`
- source note: `総務省統計局の人口推計及び国勢調査人口（各年10月1日現在）`
- 2024 national anchor: 総人口123,802千人
- parsed rows: 48 = national 1 + prefecture 47
- source unit: 1,000 persons; normalized valueは1,000倍するが、`source_value`、`source_unit=1000_persons`、`rounding=nearest_1000_persons`を保持する
- SHA-256: `e005fe843a1dc3e840ae7ab030b00ffe5930489326eb9e7a7fd1781a04197965`
- local raw: `data/raw/npa-total-population-prefecture/S16/20260901_133212_s16/`
- local processed: `data/processed/npa-total-population-prefecture/S16/20260901_133212_s16/`

統計局の[2024年人口推計](https://www.stat.go.jp/data/jinsui/2024np/index.html)は全国総人口123,802千人、東京都14,178千人、埼玉県7,332千人を掲載しており、取得binaryと一致した。統計局の[人口推計Q&A](https://www.stat.go.jp/data/jinsui/qa-1.html)は、総人口に国内滞在期間が3か月を超える外国人を含むと明記している。したがってS16は、特定nationalityではなく全住民を置く今回のprimary denominatorに適する。

### alternative denominatorをprimaryにしなかった理由

[e-Statの住民基本台帳2025年表25-01](https://www.e-stat.go.jp/stat-search/files?bunya_l=02&bunya_s=0201&cycle=7&layout=datalist&month=0&page=1&result_page=1&tclass1=000001039601&toukei=00200241&tstat=000001039591&year=20250)にも、2025年1月1日の都道府県別`総計`がある。exact personsで得られる利点はあるが、2024 annual crimeの期中に近い2024年10月1日人口を同じ警察庁publicationから得られるため、MVPのregional contextはS16を選ぶ。住民基本台帳はcross-check / sensitivity sourceとして保持する。

## 4. compatibility matrix

| Proposed value | 状態 | 理由 / 必須表示 |
|---|---|---|
| S15認知件数 / S16総人口 | **計算可能: descriptive regional context** | `case count / rounded October population`; 個人の犯罪発生確率ではない。 |
| S15検挙件数 / S16総人口 | **計算可能: descriptive regional context** | 検挙した事件数であり、認知件数や人数と別metric。 |
| S15検挙人員 / S16総人口 | **計算可能: descriptive regional context** | nationality numeratorの`検挙人員`にdimensionは近いが、同一人の重複、警察活動、居住地semantic等を含む。 |
| nationality `g`の都道府県別分子 / `N[g,p]` | **refuse** | `C[g,p]`が未公表。推計・按分しない。 |
| 日本国籍の都道府県別分子 | **refuse** | current official tablesにdirect rowがない。S02は来日外国人aggregateであり、全外国人を差し引けない。 |
| national total − national all-foreign | **research-only candidate** | 2024刑法犯では検挙件数268,412、検挙人員181,362という残差を算術上得られる。ただしdirect `日本国籍`公表値ではないため、現段階では日本国籍値としてpublishしない。 |
| `O_g / Σ_p N[g,p] r[all,p]` indirect O/E | **hold** | `C[g,p]`なしでも地域分布をadjustできる候補だが、current S08 primary metricは刑法犯＋特別法犯、S15は刑法犯のみ。visitor / residentとpolice geography / residenceも不一致。offense-scope抽出とcontract review前はpublishしない。 |

## 5. 東京・埼玉のmechanical sanity check

以下はS15 / S16を単純に割り100,000倍した検算値で、official crime rateや犯罪発生確率ではない。

| Geography | population | 認知件数 | 認知件数 / 10万人 | 検挙人員 | 検挙人員 / 10万人 |
|---|---:|---:|---:|---:|---:|
| 日本 | 123,802,000 | 737,679 | 595.85 | 191,826 | 154.95 |
| 東京都 | 14,178,000 | 94,752 | 668.30 | 23,731 | 167.38 |
| 埼玉県 | 7,332,000 | 51,667 | 704.68 | 10,054 | 137.12 |

この具体例では、東京都は埼玉県より認知件数のabsolute countが多いが、全住民10万人当たり認知件数は埼玉県の方が高い。一方、全住民10万人当たり検挙人員は東京都の方が高い。したがって「地域の犯罪発生確率」という単一概念へまとめず、認知件数・検挙件数・検挙人員を別metricとして表示する必要がある。

## 6. implemented and verified

- source registryにS15 / S16と2 seriesを追加した。
- `parse_npa_overall_prefecture_crime`と`parse_npa_prefecture_population`をtest-firstで追加した。
- two new frozen record schemas、pipeline dispatch、low-level CLI、quality record types、artifact hash / row count / enum / distinct / anchor gateを追加した。
- official URLsから正式取得し、immutable raw / processed snapshotへpromotionした。
- quality結果: S15 60 row、S16 48 row、duplicate 0、error 0、anchor mismatch 0。
- 47 prefecture label setはS15 / S16で完全一致した。
- S15の47都道府県合計はnationalの認知・検挙件数・検挙人員と全て一致した。
- S16の47都道府県合計はnationalより1,000人多い。sourceが千人単位で丸めるというofficial noteに一致する想定内の差で、silent補正しない。
- mappingを全7 source / 913,345 input rowで再生成: 720 mapping、matched 674、ambiguous 38、unmatched 8。
- indicatorを新mapping / catalogで再生成: 290 row、250 calculated、40 refused。previous canonical indicator JSONLとのSHA-256は完全一致（`b0c352488852ff820f62339616563220ba62a575e0891899d6cb4c977d6f5c9c`）。
- test: 91 passed、skip 0、branch coverage 84.59%。

## 7. ordered next implementation

1. S15 / S16をpinした`all_resident_regional_context` contractとgeneratorを作る。3 metricを混ぜず、raw numerator / denominator / unscaled quotient / display scale / caveatを出す。
2. `個別国籍 × 都道府県`、日本国籍prefecture分子、offense-scope mismatchをmachine-readable refusalとして固定する。
3. primary UIを`全住民の地域context`にし、absolute countとper-population contextを切替可能にする。nationality viewはsecondary layerにする。
4. generated productからGitHub公開用compact exportを作る。
5. 全国overview・都道府県map・filter・source panelを実装する。
6. 表130の刑法犯componentをsource-preservingに抽出できるようにした後、indirect O/Eをsecondary sensitivity viewとして再審査する。

## 8. epistemic labels

- **検証済み**: official landing URL、four official binary files（R06_003 / 129 / 130 / 144）の存在・format・title・header・anchor値・SHA-256、S15 / S16 pipeline、mapping、indicator non-regression、test suite。
- **確認できなかった**: routine official sourceの`個別国籍 × 都道府県`犯罪分子、日本国籍の都道府県別犯罪分子。
- **project decision**: nationality-neutralなall-resident contextをprimaryにし、日本国籍comparisonをdefault referenceにしない。
- **未実装 / 次gate**: all-resident context indicator data product、compact export、visualization。
