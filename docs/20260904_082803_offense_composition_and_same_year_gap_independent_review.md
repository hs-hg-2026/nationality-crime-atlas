# 犯罪類型構成・認知−検挙同年差分 independent review

- Review date: 2026-09-04
- Reviewer: 実装に関与していないfresh reviewer agent
- Mode: read-only、adversarial
- Scope: commits `e09f0f1..a392486`、current publication bundle、frontend、tests、living docs
- 結果: **Blocking 0 / High 0 / Medium 0 / Low 0。scope内open findingなし。**

## Review questions

1. 26 nationality category × 6犯罪類型の算術、share、zero-total、日本のS15−S08 residualが正しいか。
2. Jensen–Shannon distance（base 2）＋average linkageが正しくdeterministicで、危険度順位へ誤読させないか。
3. 認知−検挙同年差分がsigned valueを保ち、認知0でratioをrefuseし、strict未解決cohortと主張していないか。
4. input pin、source provenance、compact schema v5、publication SHA-256、private-path非露出が閉じているか。
5. nationality perspective切替時に、compatibleな日本人分子がなくても日本rowを消さずrefusal表示するか。
6. UI unit／copy／testとliving docsがdata productに一致するか。

## Findings

該当なし。Blocking、High、Medium、Lowの全severityでopen findingはなかった。

## Independent evidence

### Offense composition

- public bundleから独立再計算し、26 entityすべてがexactly 6 categoryを持つことを確認した。
- nonzero totalの各entityについてshare sumは1。唯一のcleared-cases zero-total entity `npa:S08:row-52`（`国籍不明`）は`refused_zero_total`で、偽の0%を生成していない。
- 日本の各類型はS15全人値−S08全外国人値に一致し、totalは検挙人員181,362、検挙件数268,412。
- published share vectorからclusterを再計算し、cleared persons／cleared casesの双方でgenerated summaryとcompact definitionのorderへexactly一致した。
- codeとcontractは`凶悪犯`だけを`official_high_severity_category`とし、UIは残り5区分を`軽犯罪`と呼ばず、clusterを優劣・危険度順位としない。

### Same-year recognition-clearance gap

- public bundleの62 derived rowを独立再計算し、60 calculated／2 refusedと完全一致した。
- anchorも一致: 日本450,406／61.0571807%、東京60,791／64.1580125%、埼玉34,976／67.6950471%。
- implementationはsigned `recognized_cases - cleared_cases`を保持し、negativeをclampせず、recognized=0ではpercentageをrefuseする。
- `not_unresolved_case_cohort`、`clearance_can_include_prior_year_recognitions`、`same_year_flow_difference`と常設UI caveatにより、未解決cohortという誤認を防いでいる。

### Primary-source semantics

reviewerは警察庁 [令和6年警察白書・凡例](https://www.npa.go.jp/hakusyo/r06/honbun/html/aah000000.html)を2026-09-04に再確認した。検挙率の分子には前年以前に認知した事件の検挙が含まれ得るため、100%を超える場合がある。この一次定義は、同年差分をstrict未解決件数／率としない実装判断を支持する。

### Provenance / publication

- public bundle SHA-256: `102e2f6d589675a4fb45eac239212ff3f160048f5c0479bea62416da67ecb002`
- `config/publication/compact_export/latest.json`、`web/public/data/dashboard_export.manifest.json`、実JSONが一致。
- public JSONに`/Users/`、`/private/`、`file://`、Windows local pathは検出されなかった。
- compact exportはsource bundle hash、definition/source linkage、public field whitelistを検証する。

### Selector / docs

- Japanese-inclusive viewでは日本をcalculated rowとして保持する。
- compatibleな日本人numeratorがない公表perspectiveでは、`japanese_numerator_scope_not_available_for_selected_perspective`のsynthetic refusalを表示し、日本をdropしない。
- README英日、workflow、brief、data management、interpretation note、implementation auditの件数・hash・semanticはpublic bundleと一致した。

## Reviewer-executed tests

- `.venv/bin/python -m pytest tests/test_compact_export.py tests/test_offense_composition.py`: 13 passed
- `npm --prefix web test -- --run tests/dashboard-model.test.ts tests/dashboard.test.tsx tests/publication-data.test.ts`: 49 passed

reviewerはfull suite、typecheck／lint／build、live browserを再実行していない。これらはroot verificationで別途実施済みであり、本reviewではresidual verification gapとして明示する。

## Closure

scope内open findingは0。implementation auditとroot full-suite／browser verificationを合わせ、犯罪類型構成と認知−検挙同年差分のfresh independent review gateをclosedとする。
