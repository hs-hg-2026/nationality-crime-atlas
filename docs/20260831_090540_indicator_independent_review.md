# Indicator baseline independent review

- Review date: 2026-08-31 (Asia/Tokyo)
- Scope: processed-input independent pin fix and current indicator production run
- Reviewer role: implementationに関与していないfresh read-only reviewer
- Result: **blocking / high / medium finding 0。先行reviewのMedium findingはclosed**

## Reviewed question

先行reviewでは、`normalized.jsonl`のintegrity checkが同じprocessed run directory内の`run.json.normalized_sha256`だけに依存していた。そのため両fileをcoordinated editすると検知できない、というMedium findingがあった。

follow-up reviewでは次を反証対象にした。

1. coordinated editが現在は停止するか。
2. required sourceすべてに独立pinがあるか。
3. missing pin、hash mismatch、または別source経由のbypassが残っていないか。
4. current runのhash、record count、documentationが一致するか。
5. relevant testとfull suiteがfresh processでも成功するか。

## Findings

blocking、high、medium findingはなかった。先行Mediumはclosedと判定された。

- generatorはcontractから`processed_input_pins`を読み、lowercase SHA-256形式を検証する。
- required sourceのpin欠落を停止する。
- input実体は、sibling `run.json.normalized_sha256`とcontract pinの双方へ一致しなければならない。
- regression testは`normalized.jsonl`とsibling `run.json`を同時に変更し、それでも未変更contract pinとの差で`IntegrityError`になることを確認する。
- production contractはS02、S08、S09、S14、S14_2024_12のexact setを持つ。
- current `latest.json`、production summary、live output hash、embedded pin、docsは`20260831_085815_indicators`に一致する。

## Independent commands / results

- `.venv/bin/python -m pytest tests/test_indicators.py` → 13 passed
- `.venv/bin/python -m pytest` → 76 passed
- `.venv/bin/python -m pytest --cov=nationality_crime_atlas --cov-report=term-missing` → 76 passed、84.37% coverage
- 5 sourceすべてで`normalized file hash == run.json hash == contract pin`
- current run: 290 record、250 calculated、40 refused
- refused-value leak: 0
- Z unique prefecture ID: 47

## Residual governance boundary

このfixは、validation後にprocessed inputとsibling manifestだけをcoordinated editするgapを閉じる。contract pin自体を意図的に書き換えられる主体まではruntimeで防がない。新editionまたはnormalized representationの変更時は、pin変更をsource／parser／quality changeと一緒にreviewすることがgovernance boundaryである。

## Evidence paths

- `config/indicator_contracts.json`
- `src/nationality_crime_atlas/indicators.py`
- `tests/test_indicators.py`
- `data/processed/_indicators/20260831_085815_indicators/`
- `docs/20260831_085815_indicator_contract_and_run_audit.md`
