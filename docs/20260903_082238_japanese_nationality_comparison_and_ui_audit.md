# 日本人を含む全国籍比較・UI audit

- audit時点: 2026-09-03 08:22 JST
- scope: S17 acquisition、全国籍comparison product、compact export schema v3、dashboard model／UI、responsive表示
- status: root agentによる実行・目視検証済み。fresh independent reviewerはscoped finding 0。旧numerator selector消失はその後に判明した別のproduct-design issue

## 結論

primary regional viewの`総人口`は、日本人と外国人を含む全住民である。secondaryな全国比較には日本を欠落させず、外国籍等categoryと同じ人口1,000人当たりの軸で掲載した。ただし日本人の犯罪分子はdirect公表値ではなく残差であるため、`日本（残差による参考値）`として、算式・構成値・source ID・mismatchを常時表示する。

高い側だけに注目させないため、同じ22 calculated rowから高い側5件／低い側5件を対称に選び、さらに26 categoryの全表をpublication orderで表示する。4件の非計算rowは0にせずrefusal理由を表示し、small-number warning対象も除外せずwarning付きで見せる。

## 入力sourceとprovenance

| 役割 | Source | Period / value | Local verification |
|---|---|---|---|
| 全体の刑法犯検挙人員 | S15, NPA Table 3 | 2024 annual / 191,826人 | normalized SHA-256をcontract pinと照合済み |
| 全外国人の刑法犯検挙人員 | S08, NPA Table 130 | 2024 annual / 10,464人 | normalized SHA-256をcontract pinと照合済み |
| 外国籍等別人口 | S14_2024_12, ISA Table 1 | 2024-12-31 stock | normalized SHA-256をcontract pinと照合済み |
| 日本人人口 | S17, Statistics Bureau Table 2 | 2024-10-01 / 120,296,000人 | official artifactを取得・parse・quality validation・catalog登録済み |

S17のofficial artifact SHA-256は`171c9930a3c881c42ded00fbaace83b4e6dd226d1a90cfddecd1daca2e376e82`、normalized SHA-256は`f82690c52a318abcdd2252b578075651d3daca5ebca16cbaabbf1278be62203b`である。current comparison contractはS08、S14_2024_12、S15、S17のprocessed input hashを独立にpinする。

## 日本人reference rowの再計算

```text
Japanese numerator
  = S15 all-person criminal-code cleared persons
  - S08 all-foreign criminal-code cleared persons
  = 191,826 - 10,464
  = 181,362 persons

Unscaled quotient
  = 181,362 / 120,296,000
  = 0.001507631176431469

Display value
  = quotient × 1,000
  = 1.507631176431469 per 1,000 persons
```

このrowには少なくとも次の制約をmachine-readableに保持する。

- `japanese_numerator_derived_by_residual_subtraction`
- `all_persons_minus_all_foreign_scope_assumption`
- `japanese_population_rounded_to_nearest_1000`
- `denominator_reference_dates_differ_across_rows`
- `annual_flow_vs_point_in_time_stock`
- `cleared_person_records_not_unique_risk_population`

したがって、この値はdirect日本人統計でもofficial crime rateでもなく、異なる公表統計を明示的な仮定のもとで組み合わせた参考比率である。

## Complete-set / symmetric表示

current productは26 rowを出力し、22 calculated／4 refusedである。UI calloutは同じ22 rowを値でsortして次を表示する。

| 側 | 5 category（表示順） |
|---|---|
| 高い側 | 無国籍、イラン、パキスタン、アメリカ、ロシア |
| 低い側 | インドネシア、ドイツ、日本、インド、イタリア |

これは観測された参考比率の並びであり、groupの本質、因果、個人riskを示さない。日本は低い側5件に実値として現れるが、正常／異常を判定するnormative baselineにはしない。

### 旧nationality viewとのmetric差

旧local MVPのdefault `x_cleared_persons_exact`は、S08の`総数・検挙人員`を使っていた。new日本人-inclusive comparisonは、S15のall-person numeratorとscopeを合わせるため、S08の`刑法犯・計・検挙人員`を使う。同じ2024年のVietnamでは、旧値が`4,113 / 634,361 × 1,000 = 6.4837`、new値が`1,679 / 634,361 × 1,000 = 2.6468`である。この差は時系列変化ではなくnumerator scopeの変更であり、両値を増減として比較してはいけない。UIはnew metricを`刑法犯検挙人員`と表示しているが、旧画面とのtransitionをどこまで常設説明するかはreview対象とする。

refused rowは`その他（アジア州の国）`、`その他（ヨーロッパ州の国）`、`その他（南北アメリカ州の国）`、`国籍不明`で、いずれも`no_canonical_denominator_components`を表示する。warning対象は、無国籍が`small_denominator_base`かつ`sparse_numerator_count`、ドイツとイタリアが`sparse_numerator_count`である。これらもcallout／全表から除外せず、warningを同時表示する。

## Data productとpublication boundary

- comparison run: `data/processed/_nationality_comparison/20260903_074525_nationality_comparison/`
  - 26 row、22 calculated、4 refused
  - JSONL SHA-256 `dba75ed68edef46e9ab8db6b2360672cf667b925f1c7acd285987241cbb0ee61`
- supplementary indicator run: `data/processed/_indicators/20260903_075423_indicators/`
  - 290 row、250 calculated、40 refused
- compact export: `output/compact_export/20260903_075440_compact_export/`
  - schema v3
  - all-resident 186 + comparison 26 + supplementary indicators 290
  - sanitized source 8件
  - dashboard SHA-256 `b0f950baa23aac85e44d644b4609ec0bd70d0567d307bfaf013377d85e4ee060`
- checked-in UI data: `web/public/data/dashboard_export.json`
  - compact exportとbyte-identicalとしてhash verification済み

## UI verification

Browser skillを使い、local server `http://localhost:3000/`を実画面で確認した。

- desktop: 全住民の定義、日本人を含む全国比較、高い側／低い側各5件、全26 row、4 refusal、source導線を確認
- mobile: viewport幅390 pxで3列のcomparison table、長いwarning、日本rowが画面内で読めることを確認
- console error: 0
- finding: side tableのwarning headerとmobile warning列がCSS specificity／最小幅でclipしていた
- fix: `.nationality-table.nationality-side-table`の幅制約とmobile wrappingを追加し、再目視でclosureを確認

## Automated verification

- Python: 116 passed、skip 0、total coverage 84.12%
- Web: 56 passed、statement 94.92%、branch 80.41%、function 97.50%、line 96.66%
- `npm run typecheck`: pass
- `npm run lint`: pass
- `npm run format:check`: pass
- `npm run verify:data`: pass
- production static build: pass（sandboxのsocket制約外で実行確認）
- GitHub Pages条件: `/nationality-crime-atlas` base pathとproduction site URLでbuildし、prepare後の32-file artifactを検証済み
- `git diff --check`: pass at the implementation checkpoint

Pages artifactの初回検証では、framework bundle内のescaped Unicode regex `\\u200B\\...`をUNC pathと誤認し、private-path gateがfalse positiveで停止した。実際のlocal path漏洩ではないことをmatch位置まで特定し、failure testを先に追加した。UNC検知を`server + share`まで要求するよう狭め、`/private/...`と完全なUNC pathは引き続き拒否するregression testを追加した。修正後、実artifact 32 filesはprivate-path、base-path、OG URL、dashboard hashをすべてpassした。

## 残る限界と次のwork

1. fresh reviewerに、残差算式、source scope、26-row completeness、高低対称性、warning表示、refusal、documentationをadversarialに再確認させる。
2. 旧`総数・検挙人員`とnew`刑法犯・検挙人員`のscope変更を常設注記にするか、旧metricをJapan=`refused`のsupplementary viewとして残すかを決める。
3. reviewed commitをpushした後、GitHub Pagesのactual URL、asset base path、data hash、source linkを実地確認する。
4. historical editionを追加し、同じcategoryの年次変化が再現するか、small denominatorで振れているかを可視化する。
5. year-over-year category／schema driftを明示し、定義が変わった区間を連続seriesとして誤接続しない。
6. official catalog discovery、scheduled acquisition、validation failure時のlast-known-good publicationを実装する。

## Fresh independent review

[20260903_182500_japanese_nationality_comparison_independent_review.md](./20260903_182500_japanese_nationality_comparison_independent_review.md)に詳細を保存した。reviewer側でPython 116 test、web 56 test、typecheck、data verification、32-file Pages artifact verificationをread-only実行し、current fixed-metric comparisonの算術・provenance・complete set・対称表示・warning／refusal・publication boundaryについてfinding 0と判定した。Vietnamから判明したselector消失は、review完了後に追加されたproduct requirementとして別途解消する。
