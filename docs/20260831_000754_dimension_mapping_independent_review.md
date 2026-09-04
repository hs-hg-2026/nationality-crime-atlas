# Independent review — canonical dimension mapping

## Result

2026-08-31、実装に関与していないfresh reviewerがread-onlyでcurrent canonical mappingを監査した。blocking／high-severity findingは0件だった。reviewerはfileを変更していない。

## Scope

- `config/dimension_mappings.json`
- `src/nationality_crime_atlas/dimensions.py`
- `tests/test_dimensions.py`
- `data/processed/_mappings/latest.json`
- `data/processed/_mappings/20260830_214058_dimension_mapping/`
- `docs/20260830_214058_dimension_mapping_audit.md`

## Evidence checked

1. **Semantic status**: NPA `中国`／`韓国・朝鮮`、source region totalは`ambiguous`、`その他`／`国籍不明`は`unmatched`、`日本`はderived national aggregateへの`matched`であり、定義したcontractと一致した。
2. **Source scope**: `_reviewed_rule`がauthored ruleのreview済み`source_id`を強制し、未review sourceへのrule流用を停止する。対応するregression testも存在する。
3. **Raw context／provenance**: `source_context`にregion、row kind、subcategory、geography type、parent region、geography semanticsを保持する。summaryはcatalog/config pathとSHA-256を保持する。
4. **Output integrity**: staging directoryからtimestamp付きimmutable runへrenameし、その後`latest.json`をatomic replaceする。latest記載のsummary／mapping SHA-256は実fileと一致した。
5. **Docs consistency**: mapping 612件、matched 578／ambiguous 26／unmatched 8、source別件数、label/category crosswalk限定という記載がproduction summary／JSONLと一致した。

## Reviewer verification

- `.venv/bin/python -m pytest tests/test_dimensions.py -q`: 16 passed
- production mapping: 612 row、unique 612、source別件数はauditと一致

## Boundary

このreviewはcanonical label/category mappingの実装・生成物・記載の整合性を対象とする。mappingがnumerator／denominatorの統計的compatibilityを保証しないというproject boundaryは維持し、indicator contractは次工程で別途検証する。
