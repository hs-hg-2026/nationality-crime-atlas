# Local visualization MVP audit

- Audit timestamp: 2026-09-02 20:09 JST
- Scope: `web/` local visualization MVP、static dashboard bundle、map／social preview provenance、frontend verification、fresh read-only review
- Status: **local MVP verified / external publication pending**
- Epistemic label: 下記のhash、row count、test、build、HTTP status、review closureは実file／実行結果で検証済み。browserを使うvisual QAと外部deploymentは未実施。

## Outcome

全住民をprimary regional baselineにするlocal dashboardを実装した。initial viewは2024年の`刑法犯認知件数`を全住民10万人当たりで表示し、全国、東京・埼玉比較、47都道府県choropleth、top-10、source、refusalを同じ画面で確認できる。`刑法犯検挙件数`と`刑法犯検挙人員`へ切り替えられ、count modeではcase metricを`件／件数`、person metricを`人／人員`と表示する。

nationality viewはsecondaryかつ全国集計に限定した。X/Y × cases/persons × exact/as-publishedの8 indicatorを選択でき、count／人口1,000人当たり参考比率、raw numerator、denominator、ranking exclusion、refusal、mismatch、sourceを表示する。非公表の`個別国籍 × 都道府県`分子は作成・推計・按分しない。

このMVPは`web/`でlocal実行できるが、GitHub Pages、`gh-pages`、CI artifact等にはまだ接続していない。したがってM4全体は進行中であり、完了ではない。

## Data and provenance closure

| Artifact | Verified identity / status |
|---|---|
| reviewed compact source | `output/compact_export/20260901_232700_compact_export/dashboard_export.json` |
| UI static copy | `web/public/data/dashboard_export.json` |
| both dashboard files | SHA-256 `1617a13037899e862def08b9bab37c5facc711d6d195812d1faf8fa8d39395bc`; `cmp` exit 0 |
| bundle schema | compact-export schema v2 |
| nationality records | 290 total: 250 calculated / 40 refused |
| all-resident context records | 186 total: 144 calculated / 42 refused |
| public sources | 7 |
| public JSON path leakage scan | `/Users/`, `file://`, `data/processed/`, `output/compact_export/` match 0 |
| map source | lalamalink `japan-map-svg`, version `2026.06.30`, commit `b6008cd22e6993a62860f5afafcc810ef4f9c69f`, CC0 1.0 |
| map SVG | SHA-256 `c4817c97dedab08d20a2f4afccd4a780befc57040d48f7f0cded79d10e084fbc` |
| social preview | `web/public/og.png`, 1200 × 630, SHA-256 `02f0526c0fa9f25e3ca1bf59a5482993037870ff6e842da16a9511d30f556732` |

`web/public/data/dashboard_export.json`はpublication copyであり、source-of-truthではない。現時点ではreview済みcompact outputとbyte-identicalだが、自動syncは未実装である。次のpublication工程ではcopy前後のSHA-256をhard gateにする。

Map generator `web/scripts/generate-japan-map-data.mjs`は、SVG bytesのSHA-256をchecked-in digestと照合してからparse／writeする。不一致ではoutputを書かず停止する。47 prefecture codeの一意性、47 path、border overlay、canonical assetからのgenerated TypeScript byte identityをtestで固定した。UIは、このSVGがdeformed mapであり、正確な地形・面積・距離を表さないことを常設表示する。

## Display contract and interpretation boundary

- primary population: 日本国籍ではなく、日本に居住する全住民
- regional denominator: 2024-10-01時点総人口
- regional numerator: 2024 calendar-year crime flow
- primary default: `刑法犯認知件数`、人口10万人当たり
- all-resident options: 認知件数、検挙件数、検挙人員 × count／人口10万人当たり
- nationality options: X/Y × cases/persons × exact/as-published × count／人口1,000人当たり
- regional formula: `numerator_value / denominator_value × 100,000`
- nationality formula: indicator contractに保持した`numerator_value / denominator_value`とdisplay multiplier
- terminology: project-derived valueは`公表統計由来の参考比率`。officialまたは正確な`犯罪率`とは呼ばない。
- compatibility: `statistical_compatibility=not_established`
- permanent caveats: annual flow vs point-in-time stock、numerator residency scope未確立、group差を因果・本質・個人riskへ読み替えない
- missing-data rule: 非公表・非接続を0で埋めず、refused rowとreasonを表示する
- small-number rule: raw値は隠さず、approved project heuristic対象をdefault rankingから除外する

東京と埼玉のdefault metricは、absolute countでは東京94,752、埼玉51,667だが、全住民10万人当たりでは東京668.3030046550995、埼玉704.6781232951446で順序が変わる。UI testは表示値を東京668.30、埼玉704.68として固定した。これは地域人口によるscale effectを確認する例であり、個人の犯罪発生確率を示さない。

Default nationality indicator `x_cleared_persons_exact`は18 calculated rowを持つ。そのうち`無国籍`と`イタリア`の2 rowをsmall-number warningによりdefault rankingから除外し、16 rowをranking対象とする。exactに接続できない6 rowは`crosswalk_not_exact`としてrefusedのまま表示する。

## TDD and independent review

Initial implementationではmodel／component testsを先に追加し、all-resident primary view、東京・埼玉normalization、source links、nationality secondary view、ranking exclusion、refusal、47-map joinをRED → GREENで実装した。

Fresh read-only reviewerは次の2 findingを報告した。

1. **High — cleared-person unit semantics**: primary count modeが`刑法犯検挙人員`も`件／件数`と表示していた。
2. **Medium — map hash closure**: map READMEはpinned SHA-256を宣言していたが、generatorがdigestを強制していなかった。

Fix前にregression testsを追加し、person semantics testが`expected 人 / received 件`、rendered UI testが`人員` button不在、tampered map testがgenerator exit 0、deterministic temp output testが未生成として失敗するREDを確認した。Fix後は以下を実装した。

- `ContextRow.numerator_metric`からcount unit／raw labelを導出し、`cleared_persons`を`人／人員`、case metricを`件／件数`とした。
- comparison card、count toggle、map readoutへ同じsemantic labelを渡した。
- map generatorでsource bytesをSHA-256照合し、mismatchではwrite前にthrowするようにした。
- canonical sourceからのgenerated moduleをformatter-compatibleかつbyte-deterministicにした。

同じfresh reviewerによるstrict read-only closure reviewは、両findingを**CLOSED**、closure scopeのnew finding 0と判定した。reviewer側でもfocused 22 testsとtypecheckがpassした。

## Verification evidence

| Gate | Result |
|---|---|
| frontend focused closure suite | 3 files / 22 tests passed |
| frontend full coverage suite | 3 files / 22 tests passed |
| frontend statements | 95.54% |
| frontend branches | 81.00% |
| frontend functions | 96.92% |
| frontend lines | 97.88% |
| TypeScript | `npm run typecheck` passed |
| lint | `npm run lint` passed |
| format | authored app/model/tests/scripts and generated map module passed `oxfmt --check` |
| map regeneration | pinned hash verified; generated module byte-identical |
| production build | `npm run build` passed; vinext reported `/` as unclassified informationally |
| local HTTP | running dev server returned HTTP 200 |
| Python full suite | 106 passed / 0 skipped |
| Python total coverage | 84.07% with branch measurement |
| independent closure | original High + Medium closed; new finding 0 in scope |

## Residual limits and TODO

1. **Publication lane**: GitHub Pages / `gh-pages`（推奨）かCI artifactかをuserが選択する。external deploymentは未実施。
2. **Reproducible publication sync**: compact exportから`web/public/data/`へのhash検証付きcopyとCI publishを実装する。
3. **Historical editions**: current UIはviewごとにcurrent one-year dataだけを表示する。historical editionsを個別review／pinした後にyear filterを追加する。
4. **Joint geography × nationality**: 公表されていない個別国籍 × 都道府県numeratorは今後も推計しない。
5. **Map semantics**: deformed SVGは選択と色分け用であり、actual geography／area／distanceを表さない。
6. **Visual QA**: Sites workflowの制約に従い、browserを使うresponsive visual QAは未実施。component tests、production build、local HTTPで機能面を検証した。
7. **M5 automation**: official catalog discovery、schedule、schema drift review、last-success／failure statusは未実装。
8. **Repository state**: current workspace rootはGit repositoryではないため、GitHub publication前にrepository初期化／remote policyを決める必要がある。

## Relevant paths

- visualization entry: `web/app/page.tsx`
- UI: `web/components/crime-atlas-dashboard.tsx`, `web/components/prefecture-map.tsx`
- data model: `web/lib/dashboard.ts`
- static input: `web/public/data/dashboard_export.json`
- map provenance: `web/assets/maps/README.md`, `web/assets/maps/LICENSE.cc0`
- map generator: `web/scripts/generate-japan-map-data.mjs`
- tests: `web/tests/dashboard-model.test.ts`, `web/tests/dashboard.test.tsx`, `web/tests/map-generation.test.ts`
- social metadata: `web/app/layout.tsx`, `web/public/og.png`
- upstream map: <https://github.com/lalamalink/japan-map-svg>
