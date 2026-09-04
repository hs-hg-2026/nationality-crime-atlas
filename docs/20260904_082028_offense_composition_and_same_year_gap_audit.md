# 犯罪類型構成・認知−検挙同年差分 audit

- 実装・local verification時点: 2026-09-04
- 対象年: 2024年
- 状態: 実装・production data生成・browser確認済み。2026-09-04のfresh independent reviewでscope内open finding 0。
- public dashboard input: `web/public/data/dashboard_export.json`
- compact export: schema v5、SHA-256 `102e2f6d589675a4fb45eac239212ff3f160048f5c0479bea62416da67ecb002`

## 結論

日本を含む26の国籍等categoryについて、刑法犯6区分の構成をheatmapと100%積み上げ棒で表示できるようにした。検挙人員／検挙件数、公表順／階層cluster順を切り替えられ、全cellで構成比と実数を確認できる。

全住民regional contextには、`認知件数−検挙件数`の符号付き同年差分件数と、認知件数に占める差分割合を追加した。ただし、この値は事件単位の未解決cohortを追跡していないため、`未解決件数`／`未解決率`とは表示しない。

## Data lineage

| Product | Source | Derivation | Current output |
|---|---|---|---|
| 外国人の犯罪類型構成 | S08・警察庁「令和6年の犯罪」表130 | 公表された国籍等 × 類型別の検挙件数／検挙人員 | `data/processed/_offense_composition/20260903_222026_offense_composition/` |
| 日本の犯罪類型構成 | S15・警察庁表3 − S08表130 | 各類型の全人値から全外国人値を引く残差 | 同上 |
| 認知−検挙同年差分 | S15・警察庁表3 | 同年・同じ公表地理の認知件数と検挙件数をpair | compact export内で明示的にderived |

S08 official landing pageは `https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm`、artifact SHA-256は`23ccb60d89c9b4bdaa898105753506a61d8354a0ae87b01598f6c97f4efd6a83`。S15も同じlanding pageにあり、artifact SHA-256は`f1c597114874c1a0ba6b87e9a7d7fcbb48041defb7cb16a874c2c9542991d75b`。normalized file、processed run manifest、version-controlled contract pinの一致をgeneration gateにした。

## 犯罪類型構成

### Categoryとmetric

mutually exclusiveな6区分は、`凶悪犯`、`粗暴犯`、`窃盗犯`、`知能犯`、`風俗犯`、`その他の刑法犯`である。警察庁の`凶悪犯`はofficial high-severity categoryとして示すが、残り5区分をproject独自に`軽犯罪`とは分類しない。

各国籍等categoryについて次を保持する。

- `cleared_persons_share = 類型別検挙人員 / 刑法犯検挙人員total`
- `cleared_cases_share = 類型別検挙件数 / 刑法犯検挙件数total`
- shareだけでなく類型別実数、total、source row、derivation method、warningを保持

生成結果は156 cell（26 category × 6区分）、statusは156 calculated／0 refused。日本のtotal reconciliationは次のとおり。

| Metric | S15 全人 | S08 全外国人 | 日本の残差参考値 |
|---|---:|---:|---:|
| 検挙人員 | 191,826 | 10,464 | 181,362 |
| 検挙件数 | 287,273 | 18,861 | 268,412 |

日本の各cellには`residual_subtraction`、算式、S15／S08のsource rowを保持する。5つのofficial地域aggregate rowは国籍categoryではないため除外し、categoryを水増ししない。

### 表示とcluster

- heatmap: 色相を犯罪類型、濃さをcategory内shareとし、cellにshareと実数を併記
- 100%積み上げ棒: 6区分のcategory内構成を同じ順序で表示
- metric control: 検挙人員／検挙件数
- order control: 公表順／階層cluster順
- cluster: 6区分のshare vectorにJensen–Shannon distance（log base 2）、average linkageを適用

clusterは類似した構成を隣接させる探索表示であり、犯罪量、優劣、危険度、因果の順位ではない。検挙件数totalが0の`国籍不明`はshareとdistanceを定義せず、cluster末尾で`構成比算出不能`と表示する。0%を作らない。

## 認知−検挙の同年差分

### 算式

同じS15、2024年、同じ公表地理について次を計算する。

```text
same_year_gap_count = recognized_cases - cleared_cases
same_year_gap_share = same_year_gap_count / recognized_cases × 100
```

差分はsigned valueとして保持し、負値を0へclampしない。認知件数が0の場合、件数差は保持できても割合はdivision-by-zeroとなるためrefuseする。current exportは62 row（60 calculated／2 request-scope refusal）。

### なぜ「未解決率」ではないか

警察庁の検挙率の定義では、分子となる当年の検挙件数に前年以前に認知した事件の検挙が含まれ得る。そのため、当年認知件数と当年検挙件数は同一事件集合ではなく、単純差は「当年認知事件のうち未解決の事件」を表さない。検挙率が100%を超え得るのも同じ理由である。

一次根拠: 警察庁 [令和6年警察白書・統計資料の凡例](https://www.npa.go.jp/hakusyo/r06/honbun/html/aah000000.html)。当年の検挙件数には前年以前に認知した事件が含まれるという検挙率定義と、100%を超える場合があることを明記している。

この境界をmachine-readableにするため、`not_unresolved_case_cohort`、`clearance_can_include_prior_year_recognitions`、`same_year_flow_difference`を常設し、publication policyの`same_year_gap_is_unresolved_cohort`を`false`に固定した。UI headlineも`strictな未解決率ではありません`とする。

### Current anchor values

| Geography | 認知件数 | 検挙件数 | 同年差分件数 | 認知件数に占める割合 |
|---|---:|---:|---:|---:|
| 日本 | 737,679 | 287,273 | 450,406 | 61.0572% |
| 東京都 | 94,752 | 33,961 | 60,791 | 64.1580% |
| 埼玉県 | 51,667 | 16,691 | 34,976 | 67.6950% |

これらはS15の公表flow同士の算術結果であり、居住者による事件、当年発生事件、未解決事件のcohortへ読み替えない。

## Compact publication

compact exportをschema v5へ更新した。record countsは次のとおり。

| Section | Records |
|---|---:|
| all-resident context（既存186 + 同年差分62） | 248 |
| nationality comparison | 26 |
| nationality indicators | 290 |
| offense composition | 156 |

definition countsはcontext 4、indicator 10、nationality comparison 1、offense composition 1、offense category 6。8つのpublic source metadataだけをwhitelistし、local absolute pathを含めない。checked-in dashboard copy、manifest、publication pointerのhash closureを検証した。

## Test・browser verification

### Automated

- Python: 128 passed、skip 0、coverage 83.45%（required 80%）
- Web: 68 passed
- Web coverage: statements 90.55%、branches 84.14%、functions 95.83%、lines 91.73%
- typecheck: pass
- lint: pass
- format check: pass
- `verify:data`: pass、expected SHA-256一致
- production build: pass、static route 1件prerender成功

### Browser

desktopと390 × 844 mobileで、regional metric、count／ratio、nationality perspective、composition metric、source／cluster orderを操作した。47 map path、26 category × 6区分、page horizontal overflowなし、console error 0を確認した。

browser確認では、同年差分のcount mode map detailに`同年差分率 64.16 件`と表示するunit bugを発見した。再現testをREDで追加し、ratio detailだけ`%`を使うよう修正後、東京都で次を再確認した。

```text
60,791 件
同年差分件数 60,791
認知件数 94,752
同年差分率 64.16 %
```

## Remaining limitations / next work

- currentは2024年のみ。時系列で構成の再現性、small-number volatility、category/schema driftを評価する段階は未実装。
- 日本の犯罪類型値はdirect公表値ではなく残差で、S15全人scopeとS08全外国人scopeが引き算可能というassumptionを伴う。
- nationality別構成は検挙統計の内訳であり、犯罪発生、全住民risk、因果を示さない。
- 同年差分は未解決cohortではない。真の未解決件数を得るには事件ID／認知年cohortと解決statusを結ぶ別統計が必要。
- 実装に関与していないfresh reviewerによるmath、provenance、semantic、UI warningのadversarial reviewを実施し、Blocking／High／Medium／Lowすべて0件、scope内open finding 0だった。詳細は [independent review](./20260904_082803_offense_composition_and_same_year_gap_independent_review.md) を参照。
