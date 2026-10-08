# 2025年の国籍等別比較・来日外国人の犯罪構成を追加

## 実装範囲

ユーザー合意：既存2024年版を残し、公表済み2025年値を対象範囲の違いが分かる別表示で追加。欠落はゼロにせず、資料ごとの分子・分母とその割り算を参考比率として表示する。

- 比較：初期表示2025年、2024年へ切替可能。従来26区分＋ペルー・ネパール・カンボジア・ミャンマーの30区分。件数／人員、外国人全体／来日外国人を選択。120行中52算出／68未算出。
- 犯罪構成：来日外国人5国籍（ベトナム・中国・タイ・ブラジル・カンボジア）＋別枠の来日外国人総数、6区分、件数／人員。12算出行、日本は対象外として2未算出行。
- 数値付き2色ヒートマップ（青0%→橙100%）、100%積み上げ棒、全実数・出典座標を用意。5国籍のJensen–Shannon距離・平均連結法で階層クラスタリング。総数・日本は混ぜない。
- 2024年の全26区分構成と2020〜2024年の国籍時系列を保持。2025年の不一致点を時系列へ黙って接続しない。
- 「来日外国人」は平易な定義と[警察庁の用語の解説（4）](https://www.npa.go.jp/toukei/keiji35/new_hanzai07.htm)へのリンクを常設。旅行者だけでも在留外国人全体でもない。

## 出典と計算

| 入力 | 役割 |
|---|---|
| S21 表3-3-1 | 全国総数・外国人全体・来日外国人の検挙値 |
| S22 表3-3-3 | 掲載国籍等の検挙件数13区分／人員12区分 |
| S19_2025 表1 | 2025年12月31日の国籍・地域別在留人口 |
| S27 表49-1 | 2025年10月1日の日本人人口原数値。不詳を加えず補完版S29へ置換しない |
| S30 図表3-13 | 来日外国人5国籍×6包括罪種＋総数 |

S21・S22：[警察庁原本](https://www.npa.go.jp/toukei/seianki/R07/r07_3.xlsx)。S30：[公式一覧](https://www.npa.go.jp/publications/statistics/kikakubunseki/)、[CP932 CSV原本](https://www.npa.go.jp/publications/statistics/kikakubunseki/r7toukeisotai0313.csv)。全入力の原本URL・版・hashは登録／catalogと公開JSONにも保持。

S30は新規系列・版として取得。原本hash`097bf7096ce5f393645f658a9801b9f83374f07f08bdac9706f1391c8edb28c6`、2,890 bytes。39論理CSV行・23列のlayoutを検証。子罪種を重複加算せず親7区分を84行に正規化した。source_rowは物理改行数でなく論理CSV行、人員は同列の件数行＋1。小さい公式原本を`data/testdata/subset/npa_2025/r7toukeisotai0313.csv`に保持。

日本の参考値：件数S21 N4 301,055−N5 22,917＝278,138、人員N7 200,663−N8 11,354＝189,309。分母S27 `b49_01` AE11 117,405,318人。1,000人当たり2.369040898件／1.612439736人。不詳AF11 2,105,452人は除外。前年の千人単位人口推計からの資料変更を常設。

中国の分子は台湾・香港等除外、在留人口930,428人は香港14,477人を内数に含む。自動差引きで一致を作らず注意を表示。韓国・朝鮮の人口は407,341＋22,201＝429,542人。crosswalkは対応の規則であり互換性の証明ではない。

独立レビューで米国・英国の原本表記違いを検出。「アメリカ」の人口対応を「米国」69,787人、「イギリス」を「英国」22,428人へ修正した。曖昧一致は使わない。

S22は2016〜2025年のいずれかで件数300以上／人員150以上となった国籍等だけの掲載。2025年単年の閾値とは呼ばず、低い側を網羅した全国籍順位ではないことを常設。S30でタイ人員103人が得られても、S22の欠落を同一資料の公表値として黙って補わない。

## 再現・公開手順

```bash
.venv/bin/nca-acquire --source-id S30
.venv/bin/nca-build-nationality-2025
cd web
npm run sync:nationality-2025
npm run verify:data
```

新CLI登録には必要に応じ`.venv/bin/python -m pip install --no-build-isolation -e '.[dev]'`でeditable installを更新。

`config/nationality_2025_contract.json`でraw／normalizedの独立hashを固定。実ファイル・run.json・contractの三者を確認してから生成。timestamp productは`output/nationality_2025/`、latest pointerはunique temporary file＋flush/fsync＋atomic replace。

公開copyは独立の`web/public/data/nationality_2025.json`。既存schema-v9 dashboardへ異なる対象範囲を混ぜず、旧hash`491a1f28b0e8de1650ac813417c19ad60b4c8750c461bac079192f22e740f595`を保持。追加copyの公開pinは`config/publication/nationality_2025/latest.json`。sync／verifyと最終Pages artifactでhash、数式、未算出、出典、input pins、私有パス非露出を検査。

## 検証と現在地

- Python：249 tests成功、coverage83.43%。テスト先行でRED→checkpoint→GREENを確認。
- 独立レビュー：原本の比較用154成分と構成用72セル、12通りの6区分合計、日本残差、不詳除外、中国の対象差を照合。米国・英国修正後に52算出／68未算出を再確認。
- ブラウザ：localhost:3000で2025年初期表示、人員189,309／117,405,318＝1.61、2024年切替、犯罪構成2色凡例を確認。
- Web全体：159 tests成功。typecheck・lint・format・静的build・最終Pages artifact検証も成功。通常sandboxでは事前描画用のlocalhost listenがEPERMとなったため、承認済みの実行環境でbuildを再実行して確認した。外部公開はしていない。
- ローカル実装のみ。push・tag・release・公開サイト更新はこの作業では行わない。

実行ログ：`agent_logs/20261008_092000_nationality_2025/`。完全な2025年26区分相当の構成、2025年国籍値の連続時系列化、用語集全体、Issue定型は別課題。
