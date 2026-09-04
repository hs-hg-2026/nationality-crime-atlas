# 日本人を含む全国籍comparison — fresh independent review

- review時点: 2026-09-03
- reviewer: current comparisonの実装に関与していないread-only reviewer
- scope: comparison contract／generator、compact export schema v3、published bundle、web model／UI、tests、living documentation
- outcome: scoped finding 0件（Blocking 0 / High 0 / Medium 0 / Low 0）

最初に新規spawnしたreviewerはservice usage limitで実行不能だった。その後、旧all-resident UIのclosureだけを担当しcurrent comparisonには関与していないidle reviewerへ、新しいread-only turnとして同じadversarial auditを依頼した。reviewerはfileを変更していない。

## 確認された事項

1. **日本人residual**
   - S15 all-person刑法犯検挙人員: 191,826
   - S08 all-foreign刑法犯検挙人員: 10,464
   - residual: 181,362
   - S17日本人人口: 120,296,000
   - display ratio: 1.507631176431469 / 1,000人
   - contract pin、構成値、derivation method、source ID、mismatch flagがproductとpublic bundleで一致
2. **complete set**
   - 26 row = 22 calculated + 4 refused
   - 日本人rowは1件だけで、全26 rowに含まれる
3. **symmetric display**
   - high 5／low 5は同じ22 calculated rowからsortして各5件を選択
   - small-number warning rowも除外されず、warningとともに表示
4. **interpretation guard**
   - contractとUIの双方でofficial crime rate、因果、groupの本質、個人riskではないと明示
   - 日本はresidual referenceでありnormative baselineではない
5. **publication boundary**
   - compact schema v3、source linkage、record／definition count、promotion pointer、dashboard hash、private-path gateを確認
   - `web/public/data/dashboard_export.json`とcurrent compact bundleはbyte-identical
   - SHA-256 `b0f950baa23aac85e44d644b4609ec0bd70d0567d307bfaf013377d85e4ee060`

## Reviewer側のread-only verification

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q` → 116 passed
- `CI=1 npm test -- --reporter=dot` → 56 passed
- `CI=1 npm run typecheck` → pass
- `CI=1 npm run verify:data` → pass
- `CI=1 npm run verify:pages -- --directory dist/client --base-path /nationality-crime-atlas --site-url https://hs-hg-2026.github.io/nationality-crime-atlas` → pass、32 files

## Residual risk / scope外で判明したdesign issue

- reviewerはlocal built artifactを検証し、live GitHub Pages URLは未検証。
- read-only制約のためfresh production buildは再実行していない。root側では同じPages条件でbuild済み。
- reviewはcurrent固定metric `刑法犯検挙人員`のcorrectnessを対象とした。その後userが、旧nationality UIにあったnumerator selectorがcurrent UIでは消えていることを発見した。これはreviewed fixed-metric productの算術findingではないが、以前の`総数・検挙人員`6.4837 / 1,000人とcurrent`刑法犯・検挙人員`2.6468 / 1,000人（Vietnam）を選択比較できないproduct-design regressionである。release前にselector復旧方針を決める。

## Evidence paths

- `config/nationality_comparison_contract.json`
- `src/nationality_crime_atlas/nationality_comparison.py`
- `tests/test_nationality_comparison.py`
- `src/nationality_crime_atlas/compact_export.py`
- `web/lib/dashboard.ts`
- `web/components/crime-atlas-dashboard.tsx`
- `web/tests/dashboard-model.test.ts`
- `web/tests/dashboard.test.tsx`
- `web/scripts/sync-dashboard-export.mjs`
- `web/public/data/dashboard_export.json`
- `output/compact_export/20260903_075440_compact_export/dashboard_export.json`
