# All-resident context / compact export independent re-audit

## 結論

**検証済み — scoped open finding 0。**

全住民regional-context productと、それをnationality indicator productと一緒に可視化層へ渡すcompact exportについて、実装者側のRED → GREEN、production dataでの再生成・機械検査、生成に関与していないfresh reviewerのread-only再監査を完了した。

current authoritative products:

- nationality indicators: `data/processed/_indicators/20260901_133239_indicators/`
- all-resident context: `data/processed/_all_resident_context/20260901_225500_all_resident_context/`
- compact export: `output/compact_export/20260901_232700_compact_export/`

## Review boundary

対象:

- `config/all_resident_context_contracts.json`
- `src/nationality_crime_atlas/all_resident_context.py`
- `tests/test_all_resident_context.py`
- `src/nationality_crime_atlas/compact_export.py`
- `src/nationality_crime_atlas/compact_export_cli.py`
- `tests/test_compact_export.py`
- 上記current runのJSONL／JSON／pointerと、そこから参照されるsource run

対象外:

- visualization UI本体
- GitHub publication lane
- current compact bundleが参照しないproducer／historical edition全体の再監査

## Review process integrity

最初に依頼した2つのreview taskはread-only監査の指示に反し、それぞれall-resident productとcompact exportの実装を行った。そのため、それらをindependent reviewの根拠には採用していない。以後は実装に関与していない別reviewerへ、編集・生成を禁止したread-only adversarial reviewを依頼した。

このstrict reviewerは、all-resident contextの初回監査、fix後のclosure確認、compact exportの初回監査、fix後のclosure確認を行った。最終compact closure reviewは一度usage limitで中断したが、翌日に同じscope・hashで再実行して完了した。

## All-resident context findings and closure

initial reviewで確認されたfinding:

1. **Blocking**: catalogに同一`source_id`の複数revisionがあると、contract pinで選別する前にduplicateとして停止した。
2. **High**: annual crime flowと10月1日時点人口stockの差、および分子のresidency scopeが確立していない点が必須warningではなかった。
3. **Medium**: root `latest.json`が固定temporary filenameを使い、concurrent writerに弱かった。
4. **Medium**: production geometryを固定するregression testがなかった。

対応:

- 同一`source_id`候補はauthored `normalized_sha256` pinでexactly one revisionを選ぶ。0件または複数一致なら停止する。
- contract schema v2へ以下を必須化した。
  - `numerator_period_type=annual_flow`
  - `numerator_residency_scope=not_established`
  - `denominator_period_type=point_in_time_stock`
  - `annual_flow_vs_point_in_time_population`
  - `numerator_residency_scope_not_established`
- `latest.json`はsame-directoryのunique temporary fileへ書き、`flush`／`fsync`後に`replace`する。
- production geometry相当fixtureで、S15 60 row、S16 48 row、output 186 row、144 calculated／42 refused、refusal split、全国人口の丸め差 -1,000、東京／埼玉anchorを固定した。

current run `20260901_225500_all_resident_context`:

- 186 records: 144 calculated / 42 refused
- record SHA-256: `d85a2f815cc5fa285b7570da48213e5f5feab5c5fc7e1d73f483550f79eb4582`
- summary SHA-256: `c60a66b2136c9cda76a5b70139d6be7fadabe80cabc747ff618492f684e35437`
- 旧runから数値fieldの変化なし。caveat／context metadataのみを強化した。
- 144 calculated rowすべてが上記2 warningを持つ。

fresh reviewerはBlocking／High／Medium／Lowの全findingをclosedと判定した。

## Compact export findings and closure

initial reviewで確認されたfinding:

1. **High**: compactionで`indicator_id`／`context_id`まで除去され、rowからdefinitionへjoinできなかった。
2. **High**: source fileをparseした後にpathを再hashしており、入力更新時に異なるbyteを混ぜるTOCTOU gapがあった。
3. **Medium**: root `latest.json`が固定temporary filenameを使い、`fsync`もなかった。
4. **Low**: source summaryのhashは確認していたが、record count／status count／schemaとrecordsのsemantic reconciliationがなかった。
5. **self-audit**: 公開source panelに必要なpublisher／official URL等がなく、将来absolute local pathを公開bundleへ漏らす余地があった。

対応:

- compact export schemaをv2へ上げ、全rowに`indicator_id`／`context_id`を残す。
- JSON／JSONLは1回だけbytesとして読み、同じbytesからhashとparse結果を作る。source metadata作成時にpathを再hashしない。
- root pointerをunique temporary file + `flush` + `fsync` + `replace`で公開する。
- source summaryのschema、record count、status count、empty input、exact duplicateをrecordsと照合する。
- `sources`にpublisher、dataset、table、period、landing URL、download URL、revision、retrieval time、artifact／normalized SHA-256等のpublic fieldだけをwhitelistする。
- recordsが参照するsource IDがpublic source metadataに存在することを検証する。
- absolute local pathや`raw_relpath`／`processed_relpath`をpublic bundleへ含めない。

current run `20260901_232700_compact_export`:

- schema v2
- nationality indicator: 290 rows / 10 definitions
- all-resident context: 186 rows / 3 definitions
- public sources: 7
- missing row-to-definition links: 0
- 144 calculated all-resident rowsすべてで、annual-flow／point-in-time-stockとnumerator residency scope unknownのwarningを保持
- 両warningを持つall-resident rowsは180件。残る6件は非公表numerator requestのrefusalで、別のrefusal flagを持つ。
- `/Users/`、`/private/`、`CloudStorage`等のlocal absolute path: 0
- dashboard SHA-256: `1617a13037899e862def08b9bab37c5facc711d6d195812d1faf8fa8d39395bc`
- summary SHA-256: `b2e506a2f75fa27ad3673f0c9a3e9d34da9cf4b982a0a3ec689f4b81a9e59940`
- root `latest.json`の両hashと実file: 一致
- source latest／summary／recordsの記録hashと実file: すべて一致

fresh reviewerは旧4 findingをすべてclosedとし、追加のBlocking／High／Medium／Low findingは0件と判定した。

## Verification evidence

### Automated tests

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_compact_export.py -q
6 passed

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest --cov=nationality_crime_atlas --cov-report=term-missing
106 passed, 0 skipped
total coverage 84.07% (branch measurement enabled)
```

### Reviewed implementation hashes

| File | SHA-256 |
|---|---|
| `config/all_resident_context_contracts.json` | `d82f55e1dd95dda8c175e241e24ed23e5117ef0d77873c8f7afc5c9f0e52947a` |
| `src/nationality_crime_atlas/all_resident_context.py` | `4e2d2b5a8a0f3ef1df555d9eae21a372a9ae1596ee4730df93b3d4a8b2974c63` |
| `tests/test_all_resident_context.py` | `e39ace74518aec5a1962b0bb2db459363a12e3a97fc75dff70e2b39984bebef9` |
| `src/nationality_crime_atlas/compact_export.py` | `ecbc2f7400ae8e4f43d563763cf00f5df6aea07b476e422529017f68acb614ff` |
| `src/nationality_crime_atlas/compact_export_cli.py` | `a9649a0db5c4d9f5ed566bffbb26332480ac905d6817e102cf0c38c0fb01b3a4` |
| `tests/test_compact_export.py` | `db1b616be9695aae4dbdc1e480143fe7d5c5ce9fce206edac017d13fce8a430d` |

## Residual risk / next boundary

- distinct timestampのconcurrent publicationはdeterministic test済み。同一`generated_at`のwriter衝突は安全に片方が失敗する設計だが、そのexact collision専用testは未追加。
- current bundleはlocal generated artifactであり、GitHub Pages／CI artifact等のpublication laneは未確定。
- visualization MVPは未実装。このre-auditはUIの誤表示やinteractionを保証しない。

したがって次の実行順は、current compact bundleを入力にしたlocal visualization MVP → UI data/interpretation検証 → publication lane確定 → GitHub公開である。
