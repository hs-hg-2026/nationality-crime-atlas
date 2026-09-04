# Small-number threshold sensitivity audit

- Audit date: 2026-08-31 (Asia/Tokyo)
- Generated run: `data/processed/_indicator_sensitivity/20260831_205122_small_number_sensitivity/`
- Input indicator run: `data/processed/_indicators/20260831_085815_indicators/`
- Status: **sensitivity analysis verified; publication policy not yet approved**
- Question type: comparison / decision support

## 結論

denominatorだけのuniversal cutoffをofficial statistical ruleとして採用できる根拠は確認できなかった。official practiceは対象dataと推定modelに応じ、numerator count、denominator/sample size、confidence interval、coefficient of variation、複数年集約、shading／suppression等を組み合わせている。

このprojectの比率は、母集団compatibilityを確立したofficial rateではなく、異なる公表統計を単純除算した`公表統計由来の参考比率`である。そのため、Poisson model、confidence interval、Bayesian stabilizationを適用すると、存在しないrisk-population modelを暗黙に仮定してしまう。現段階では補正・推計・suppressionをせず、raw numerator／denominatorとsmall-number sensitivityを表示するのが妥当である。

推奨するdecision案は、次の2軸を別flagとして扱うことである。

1. `small_denominator_base`: `denominator_value < 1,000`
2. `sparse_numerator_count`: `numerator_value < 20`

これはofficial crime-statistics reliability standardではなく、projectのnon-suppressing UI warning heuristicである。canonical outputへはまだ適用していない。

## Sourced evidence（一次資料）

### 厚生労働省

[人口動態保健所・市区町村別統計](https://www.mhlw.go.jp/toukei/saikin/hw/jinkou/tokusyu/hoken04/1.html)は、市区町村別指標が少ない出現数による偶然性の影響で不安定になるため、5年間のdataをまとめ、Bayesian estimationで安定化すると説明している。

[市区町村別生命表のBayesian estimation解説](https://www.mhlw.go.jp/toukei/saikin/hw/life/ckts00/8.html)は、人口100人では観測event 1件の増減がrate 0.05に対して0.04–0.06、すなわち20%の変動を生む例を示す。一方、人口1万人／event 500件では1件増減の相対影響が小さい。

適用境界: これらは死亡・出生のsmall-area estimationであり、本projectのcrime numeratorへ直接移植できるthresholdではない。small-number問題がdenominatorだけでなくevent countと1件単位の離散性に関係することの根拠として用いた。

### U.S. National Center for Health Statistics / CDC

[Implementation of New Data Presentation Standards for Rates and Counts for Mortality](https://wonder.cdc.gov/controller/pdf/presentation-standards-mortality-2024.pdf)は、complete countでも少数eventではrandom variationが大きいとし、2023 data以降はまず10 deaths未満を非表示にし、10以上でも95% confidence intervalのrelative widthが160%を超える場合はrateを表示しない。旧20-death基準は文書自身が“somewhat arbitrary”なconvenient benchmarkと説明している。

[CDC WONDER analysis guidance](https://www.cdc.gov/asthma/data-analysis-guidance/ucd-data.htm)は、small numerator／denominatorへの対応として、複数年・categoryのaggregation、confidence interval、rate／count suppressionを検討し、event count 20未満なら複数年化を例示している。

適用境界: mortalityにはPoisson modelと対応するresident populationがある。本projectではnumerator populationとresident denominatorが一致しないため、NCHSのCI／suppression ruleを統計的保証として流用しない。`20`はcross-domain sensitivity benchmarkとしてのみ使う。

### UK Office for National Statistics

[Measuring and reporting reliability of LFS and APS estimates](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/methodologies/measuringandreportingreliabilityoflabourforcesurveyandannualpopulationsurveyestimates)は、組織内でも異なるthreshold ruleが併存し、一貫しない理由が明確でなかったと報告する。sample sizeだけでなくcoefficient of variationやconfidence intervalを使い、低precision outputはshadingと注記でcommunicateする案を採用している。

適用境界: LFS／APSはsample surveyで、本projectのadministrative full countsとは異なる。domainに依存しない単一thresholdを外部からコピーせず、warningの意味を明示する必要性の根拠として用いた。

## Local evidence

input 290 recordのうち250件がcalculated、40件がrefusedである。sensitivity analyzerはrefused rowを除き、実際にwarning対象となるrecord数と、policy／metric viewの重複を除いたunique observation数を別集計した。比較演算はすべてstrict `<`である。

### Denominator sensitivity

| Candidate threshold | Affected calculated records | Unique denominator observations | Newly included observations |
|---:|---:|---:|---|
| `<100` | 0 | 0 | — |
| `<500` | 8 | 1 | `無国籍` 468 |
| `<1,000` | 8 | 1 | なし |
| `<2,000` | 8 | 1 | なし |
| `<5,000` | 16 | 2 | `イラン` 4,399 |
| `<10,000` | 42 | 9 | `イタリア` 5,556、秋田6,333、鳥取6,511、高知7,355、ドイツ8,749、青森9,419、徳島9,717 |
| `<50,000` | 146 | 40 | 31 observation追加 |

current dataでは`<500`、`<1,000`、`<2,000`の対象が完全に同じなので、現datasetだけからこの3候補の優劣は決められない。`<1,000`を選ぶ理由は、人口1,000人当たり表示で1 eventのabsolute stepが1.0以上になる境界として説明しやすいことにある。これはdisplay heuristicであり、統計的validity cutoffではない。`無国籍`468人では1 eventのstepは約2.137 per 1,000である。

### Numerator sensitivity

| Candidate threshold | Affected calculated records | Unique numerator observations |
|---:|---:|---:|
| `<1` | 2 | 1 |
| `<5` | 6 | 3 |
| `<10` | 11 | 6 |
| `<20` | 20 | 12 |
| `<50` | 64 | 43 |

`<20`では、`無国籍`のS08／S09 cases/persons、`イタリア`のS08／S09 cases/persons、高知・秋田・宮崎・島根のS02 personsが対象となる。positive numeratorが20未満なら1 event増減はnumeratorに対して少なくとも約5.3%の相対変化になる。0件ではrelative changeを定義できないが、翌年1件になるだけで比率が0から非0へ変わる。

`denominator <1,000`の8 recordはすべて`numerator <20`にも該当する。dual warningのunionは20 / 250 calculated recordである。

## Inference

- small-number sensitivityはdenominatorとnumeratorを分離して表示すべきで、単一の`unstable=true`へ潰すべきではない。
- `per 1,000`を`per 100,000`へ変えても、one-event sensitivityや情報量は変わらない。
- confidence intervalやBayesian smoothingは、compatible population／probability modelが未確立な現状ではmisleadingになり得る。
- privacy suppressionはofficial source側で処理済みのaggregateを扱う本projectの現在の目的とは別問題である。warningをsuppressionと混同しない。
- warning対象をrankingやtop/bottom calloutへ既定表示すると、偶然変動とsource mismatchを過度に強調するriskがある。

## Recommendation（user decision待ち）

次のpolicyを推奨する。

1. denominator `<1,000`に`small_denominator_base`を付ける。
2. numerator `<20`に`sparse_numerator_count`を付ける。
3. どちらもratioをsuppressionせず、raw numerator／denominatorと同じ画面でwarning表示する。
4. flagged recordはdefault rankingとtop/bottom calloutから除外するが、filterで閲覧可能にする。
5. warning文に「official reliability thresholdではない」「母集団不一致は解消しない」「1件増減の影響が大きい」を明記する。
6. CI、Bayesian smoothing、複数年poolingは現MVPでは行わない。historical backfill後に、source compatibilityと目的を再reviewして別indicatorとして検討する。

この選択はcanonical outputのflagとvisualization behaviorを変えるため、user approval後にindicator contractへversioned policyとして実装する。

## Reproducibility / integrity

- command: `.venv/bin/nca-audit-small-numbers`
- config: `config/small_number_sensitivity.json`
- generator: `src/nationality_crime_atlas/small_numbers.py`
- input indicator run: `20260831_085815_indicators`
- output sensitivity record count: 119
- JSONL SHA-256: `bc97f2c0c162b96641722b67b807c952d58b59e74c077a5e60c01fc69840397f`
- CSV SHA-256: `493b4278f1d3b7b09af6ffb3e67d4e1a1ed13b2025cba351b70341f28e2c2b7e`
- summary SHA-256: `8ff23aa46caea2a0bc46c46fb433d81bb9c60d393c48faf9d70277f611c1ee3b`
- config SHA-256: `12c49a60030820173af1876673c74850d9daf0087f1aa4ba95c0b319ac08787b`

独立したset-based再集計で、全12 threshold summary、119 output record、indicator input hash、JSONL／CSV／summary latest hashの一致を確認した。

## Verification

- focused: `tests/test_small_numbers.py` 4 passed
- full suite: 80 passed、skip 0
- branch計測total coverage: 84.27%（required 80%をpass）
- RED: module未実装による意図したcollection failure
- GREEN: unique-observation deduplication、strict threshold、input hash gate、immutable output、CLIを確認
