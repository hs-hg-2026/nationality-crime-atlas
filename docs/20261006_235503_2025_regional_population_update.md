# 2025年 地域別地図・人口当たり検挙時系列の更新

## 結論・公開状態

2025年の全国＋47都道府県の地図と、2015〜2025年の人口1,000人当たり検挙参考比率をローカルで実装した。件数／人員を切り替え、日本人等の算術残差と外国人全体を別panelで示す。今回はpush・releaseを行っていない。公開中のv0.4.0は先行した全国検挙構成比の更新のみ。

国籍等別26区分の全国比較、2020〜2024年時系列、犯罪種類の構成は従来版を維持する。来日外国人だけの補足資料で外国人全体や日本人等を置換しない。[犯罪構成の補足候補](./20261006_232924_2025_offense_composition_options.md)は別計画。

## 入力・出典の対応

| 資料 | 用途 | 対象・単位 |
|---|---|---|
| S20 警察庁「令和7年の刑法犯に関する統計資料」表1-5-1 | 地域別の認知件数・検挙件数・検挙人員 | 2025年の全国＋47都道府県、件／人 |
| S26 国勢調査 表1-1 | 地域別の総人口分母 | 2025-10-01、原数値、人単位、日本人・外国人の別の不詳も含む |
| S21 警察庁 同資料表3-3-1 | 全国総数・外国人全体の検挙分子 | 件数N4/N5、人員N7/N8、2025年 |
| S27 国勢調査 表49-1 | 日本人等残差の人口分母 | b49_01!AE11、日本人人口原数値117,405,318人 |
| S19_2025 在留外国人統計 第1表 | 外国人全体の人口分母 | 25-12-01m!E5、2025-12-31、4,125,395人 |
| S29 国勢調査 不詳補完参考表49-1 | 原数値との区別確認のみ | 日本人人口119,131,935人。今回は分母に使わない |

警察庁資料は[2025年の図表索引](https://www.npa.go.jp/toukei/seianki/R07/r07.zuhyosakuin.htm)、人口資料は公開bundleの各sourceのlanding/download URLへ辿れる。登録版・raw・manifestは上書きしていない。新規取得ではなく、既に取得・検証していた公表物から生成した。

## 算式・2025年の全国値

| 区分 | 検挙件数 | 検挙人員 | 分母人口 | 件数／1,000人 | 人員／1,000人 |
|---|---:|---:|---:|---:|---:|
| 日本人等（全国総数−外国人全体の残差） | 301,055−22,917=278,138 | 200,663−11,354=189,309 | 117,405,318 | 2.37 | 1.61 |
| 外国人全体 | 22,917 | 11,354 | 4,125,395 | 5.56 | 2.75 |

日本人等は日本国籍の直接公表値ではない。外国人全体の犯罪分子と在留外国人人口の分母も同じ対象ではない。犯罪確率・公的な犯罪率とは呼ばない。

2025年の日本人人口は国勢調査の**原数値**であり、日本人・外国人の別が不詳の2,105,452人（AF11）を含まない。前年までの人口推計（千人単位）との資料変更を常設注意文とrow metadataに残した。前年との差には資料・集計方法の違いも含まれるため、そのまま人口や参考比率の変化と解釈しない。地域別総人口S26は不詳を含む点も常設説明する。

人口当たり比率の2panelは同じy軸上限、0始まり、1.0間隔を維持した。外国人の2015年人口分母が未登録の2行は未算出のまま残す。

## 生成物・再開手順

| 生成物 | 今回の場所 | 件数 |
|---|---|---|
| 地域用dimension mapping | `data/processed/_regional_mappings/20261006_234014_dimension_mapping/` | 340行、matchedはlabel対応のみ |
| 全住民地域データ | `data/processed/_all_resident_context/20261006_234017_all_resident_context/` | 150行、算出144／未算出6 |
| 人口当たり時系列 | `data/processed/_clearance_population_trend/20261006_234233_clearance_population_trend/` | 44行、算出42／未算出2 |
| compact export | `output/compact_export/20261006_235016_compact_export/` | 地域200行（同年差50行含む）、出典33件 |
| 公開用copy | `web/public/data/dashboard_export.json` とmanifest | schema v9、compactとbyte一致 |
| VCS再開用pointer | `config/publication/compact_export/latest.json` と同run directory | summaryとbundle hashを保持。bundle本体は`web/public/data/` |

公開copyのSHA-256: `491a1f28b0e8de1650ac813417c19ad60b4c8750c461bac079192f22e740f595`。

```bash
.venv/bin/nca-map-dimensions --source-id S14_2024_12 --source-id S20 --source-id S26 --output-root data/processed/_regional_mappings
.venv/bin/nca-build-all-resident-context
.venv/bin/nca-build-clearance-population-trend
.venv/bin/nca-build-compact-export
cd web
npm run sync:data
npm run verify:data
npm run dev
```

global mapping pointerは変更せず、review済みsourceだけの地域用pointerを追加した。catalog全件のmappingは、新しいnormalized record typeの対応が未整備で停止する。未reviewの表を黙ってskipしたり、fuzzy mappingしたりせず、対象を明示して再生成する。latest pointerはunique temporary file＋flush/fsync＋atomic replaceに変更した。

## 検証結果

- Python全230テスト成功、coverage 83.05%。2025年の原数値／補完値拒否、分子セル・出典・必須注意flag・算式・人口scopeのfailure testを含む。
- Web全151テスト成功、statement coverage 88.20%、branch coverage 84.28%。2025年の公開検査・画面表示・件数／人員切り替え・共有y軸を確認。
- 型検査・lint・format・公開bundle hash検査成功。通常のsandbox buildは一時ポートのlisten権限で停止し、承認済みのsandbox外buildで成功。Pages用base path `/nationality-crime-atlas`・公開URLで再buildし、公開物33ファイルとbundle hash検査も成功。初回は通常local設定のbuildにPages公開URL検査を当ててOGP URL不一致で停止したため、CIと同じ環境設定で再検証した。
- 独立review: raw 6資料のhash、S20/S26 normalized実file・run・contract三者pin、S21の件数／人員セル、S27原数値とS29補完値の区別を確認。
- 全国＋47都道府県×3指標144行、派生同年差48行をrawセルから照合し不一致0。総人口の全国値は47都道府県の合計と一致。
- 2015〜2024年人口時系列40行は、変更前commit `7621d62` の公開JSONと全field完全一致。国籍比較26行・国籍時系列260行・犯罪構成156行・検挙割合66行も完全不変。
- 独立reviewで指摘されたUIの10年固定の第2検査を修正。localhostの実ブラウザーでも2025年の地図、2015〜2025年表示、原数値・不詳除外・資料変更注意文を確認。人員へ切り替え、189,309人／11,354人と参考比率1.61／2.75、両panel共通0〜5・1.0間隔の軸を確認。
- 成功した最終実行ログは`agent_logs/20261006_235503_2025_regional_population_update/`に保存（ローカル専用）。

## ユーザー提供の取得経路と将来計画

ユーザー提示の `statInfId=000040410682` は既存S02と同じ公表物（犯罪統計資料・年末確定値）。既存parserは表13を使っており、表12の国籍等別重要犯罪／重要窃盗犯は補足候補。これだけで既存26区分×6類型の外国人全体の内訳を更新できるわけではない。

[警察庁の犯罪統計一覧](https://www.npa.go.jp/publications/statistics/sousa/statistics.html)は平成14年（2002年）からの犯罪統計資料を掲載すると明記していることをURLアクセスで確認した。ただし各年の表番号・対象範囲・訂正版の照合は未実施。「年間の犯罪」詳細版と同じ表を持つとは仮定しない。

[e-Stat API利用ガイド](https://www.e-stat.go.jp/api/api-info/api-guide)では、ユーザー登録とアプリケーションID取得が必要。[公式FAQ](https://www.e-stat.go.jp/api/api-dev/faq)ではAPI対象はデータベース形式の統計とされ、ファイル公開のExcel／CSVすべてをAPIで取得できるとは限らない。API未申請の現時点では直接ファイル取得を継続する。

今後の順序：

1. このローカル更新の確認後、ユーザー指示によりpush・release・公開画面確認。
2. 既存26区分の2025年犯罪構成更新と、対象限定の補足表示を別計画として選択する。
3. 過去年版の表・定義・改訂と、API対象DB表の有無を一覧化する。
4. APIが必要になった時点でユーザーがIDを取得。取得用環境変数に置き、Git・公開frontend・URLログには残さない。
5. API採用時もquery・表ID・取得日時・metadata・pagination・raw応答hashを記録し、現在のimmutable保存／検証／改訂review境界を維持する。自動更新とscheduleは別実装。
