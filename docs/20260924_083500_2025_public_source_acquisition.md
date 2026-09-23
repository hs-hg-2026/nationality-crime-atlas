# 2025年公開済みsource取得記録

## 結論

2026年9月24日時点で公開済みの2025年資料を取得し、immutable raw snapshot、normalized processed data、public catalogを作成した。すべてpinned SHA-256、source固有のquality profile、anchor数値に合格した。

この段階では取得とnormalizationまでであり、公開dashboardの2025年表示にはまだ接続していない。既存の2020–2024年の定義やcontractは上書きしていない。

## 取得したsource

| ID | 内容 | normalized行数 | raw SHA-256 |
|---|---|---:|---|
| S20 | 全住民の都道府県別刑法犯認知件数・検挙件数・検挙人員 | 48 | `9d0f25831974f262711021879672646b2cb33418a8c2b03df4d810c2d6a40b07` |
| S21 | 全体・外国人全体・来日外国人の全国刑法犯検挙値 | 3 | `853bf42f0467389afd4e4f532c09c3fb7bb1f7bf4a05a7dc9911f9b6b20d1b1b` |
| S22 | 公表基準で選択された国籍等別の検挙件数・検挙人員 | 50 | `853bf42f0467389afd4e4f532c09c3fb7bb1f7bf4a05a7dc9911f9b6b20d1b1b` |
| S23 | 来日外国人の罪種・手口別刑法犯検挙値 | 28 | `853bf42f0467389afd4e4f532c09c3fb7bb1f7bf4a05a7dc9911f9b6b20d1b1b` |
| S24 | 2025年国勢調査の総人口速報値 | 48 | `ac68e74efb74e2cd4b9cce64c85fa3ece508ae018205c121af76a37b8373758b` |
| S25 | 2025年10月1日の外国人口推計参考値 | 48 | `192fadf6cfdfc2cb321b0e6a5b63e20971c3891a59a1c80e022890be480cec14` |

S21、S22、S23は同じofficial workbook `r07_3.xlsx`を、異なる表とschemaのreview boundaryに分けてnormalizationした。

## 定義上の境界

- S22は全国籍の完全表ではない。検挙件数は2016–2025年に300件以上の年がある国・地域、検挙人員は150人以上の年がある国・地域だけが掲載される。
- 件数と人員で掲載国が異なるため、metric-long形式で保存し、未掲載値を0にしない。
- 2025年の「中国」は、source注記に従い台湾・香港等を含まない定義として記録した。旧表との単純接続はしない。
- S23は来日外国人の全国集計であり、外国人全体や国籍等×罪種の表ではない。
- S24は速報値、S25は「推計」と明記された参考表である。2026年9月29日予定の確定値と同一視しない。

## 次のaction

1. 2026年9月29日以降に国勢調査「人口等基本集計」をrecheckする。
2. 確定値を新editionとして取得し、S24・S25を上書きしない。
3. S20・S21と確定人口のcompatibility review後に、2025年の地域別・全国scope別data productを生成する。
4. S22は既存の26区分時系列へ直接appendせず、公表対象限定と定義変更をUIで表せる別panelまたはboundaryをdesignする。
5. 警察庁「令和7年の犯罪」詳細版を月1回monitorする。

## 検証

- Python test: 186 passed
- Total coverage: 82.63%
- 6 sourceすべてquality gate passed
- 同一commandの再実行で6 sourceすべて`reused: true`
- raw artifactは`data/raw/<series>/<edition>/<retrieved_timestamp>/`にimmutable snapshotとして保存
- normalized dataは`data/processed/`に生成し、compact catalogのみGit追跡対象
