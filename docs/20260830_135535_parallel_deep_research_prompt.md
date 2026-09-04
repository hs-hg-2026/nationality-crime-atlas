# Parallel Deep Research prompt — official-source continuity, definitions, and acquisition routes

以下を ChatGPT Deep Research にそのまま貼り付けて実行してください。この調査は、すでに終えた広いsource auditを繰り返すのではなく、実装を止めている狭い論点を埋めるためのものです。

---

あなたは、日本の公的統計のprovenance、schema evolution、統計定義を検証するresearcherです。全国・都道府県別の外国人関連犯罪統計と在留外国人人口を可視化するopen-source projectのため、一次資料を中心にDeep Researchを実行してください。

## 1. 調査目的

2015年から調査実行日時点の最新公表年までを対象に、次の3系列について、継続取得可能性、年ごとのschema drift、用語定義、地理単位、安定した発見・download経路を確認してください。

1. 警察庁の全国・国籍／地域別犯罪統計（現行資料の表130・表131に相当する系列）
2. 警察庁／e-Statの都道府県等別・来日外国人犯罪統計（現行資料の表13に相当する系列）
3. 出入国在留管理庁／e-Statの在留外国人統計 表1（国籍・地域、在留資格、性別、年齢、都道府県別の系列）

目的は「正確な犯罪率」を作ることではありません。公表済みの異なる統計をsource pairごとに単純除算した場合の、再現可能な`公表統計由来の参考比率`を設計するため、何が同じで何が違うかを明示することです。

## 2. 確定済みのproject policy

以下は変更案を出さず、前提として扱ってください。

- 分子と分母の完全一致はproject milestoneにしない。
- indicatorごとにnumerator、denominator、formula、scale、source、period、geography、population scope、mismatch flagを表示する。
- projectが導出した値をofficialまたは正確な`犯罪率`とは呼ばない。
- 公表されていない`個別国籍 × 都道府県`の犯罪分子を推計・按分・補完しない。
- `認知件数`、`検挙件数`、`検挙人員`を混同しない。件数版と人員版は別indicator IDにする。
- 警察庁への照会や都道府県警資料の追加探索はenrichmentであり、MVPのblockerにしない。

## 3. 検証を開始するofficial URL

以下は探索の起点であり、記載内容や継続性を必ず実ページで再検証してください。project内のS02等は内部IDで、official IDではありません。

- S08候補: 警察庁 2024年詳細犯罪統計、表130  
  Landing: https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm  
  File候補: https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_130.xlsx
- S09候補: 警察庁 2024年詳細犯罪統計、表131  
  Landing: https://www.npa.go.jp/toukei/soubunkan/R06/R06hanzaitoukei.htm  
  File候補: https://www.npa.go.jp/toukei/soubunkan/R06/excel/R06_131.xlsx
- S02候補: e-Stat 2025年確定値、表13  
  Landing: https://www.e-stat.go.jp/stat-search/files?stat_infid=000040410682  
  File候補: https://www.e-stat.go.jp/stat-search/file-download?fileKind=0&statInfId=000040410682
- S14候補: e-Stat 在留外国人統計 2025年12月、表1  
  Landing: https://www.e-stat.go.jp/stat-search/files?layout=dataset&stat_infid=000040472265&toukei=00250012&tstat=000001018034  
  File候補: https://www.e-stat.go.jp/stat-search/file-download?fileKind=0&statInfId=000040472265
- 警察庁利用規約: https://www.npa.go.jp/rules/index.html
- e-Stat利用規約: https://www.e-stat.go.jp/terms-of-use

## 4. 調査する順番

### Q1. 年次continuityとschema drift

2015年から最新公表年まで、3系列それぞれについて年次matrixを作ってください。各年について最低限、次を確認してください。

- 統計年／基準日
- 公開日または更新日
- official landing URL
- official direct download URLまたはAPI/catalog discovery route
- e-Statの`statInfId`、統計表ID、dataset ID等のstable identifier
- 表番号、表題、sheet名
- file format（XLS、XLSX、CSV、DB等）
- 主要header、列位置、merged cells、hidden sheetなどparserに影響する構造
- 単位、欠損・秘匿記号、合計行、注記の位置
- 前年からの変更点
- URL命名規則が推測にすぎないか、official pageから辿れることを確認したか

すべての年のbinary fileを取得できない場合は、確認できた年、確認できなかった年、試したofficial discovery routeを区別してください。URL patternから存在を推定しただけの年を`verified`にしないでください。

### Q2. 用語と母集団のofficial definition

次の語について、警察庁・出入国在留管理庁・e-Statの一次資料にある定義、注記、対象外を調べてください。短い原文引用は1資料25語以内とし、原文URL、ページ／表／注番号を付けてください。

- `外国人`
- `来日外国人`
- `在留外国人`
- `総在留外国人`
- `検挙件数`
- `検挙人員`
- 国籍・地域区分（例: 中国に台湾・香港等を含む旨の注記が年によりどう変わるか）

定義が年次で変わった場合は、変更年と変更前後を示してください。definitionが明示されていない場合は、周辺資料からのinferenceと明記し、断定しないでください。

### Q3. 表13のgeography semantics

表13の都道府県・管区・方面等が、次のどれを表すかを一次資料で確定できるか調べてください。

- 犯罪の発生地
- 検挙した警察の管轄／処理地
- 被疑者の居住地
- その他の集計地理

表の見出しだけで推定せず、作成要領、統計用語解説、犯罪統計書の利用上の注意、metadata、関連する警察庁文書を探してください。確定できなければ`unresolved`とし、どこまで分かったか、表示時に安全な日本語／英語label、警察庁へ送る具体的な照会文を示してください。

### Q4. 安定した取得・更新経路

各系列について、年次更新pipelineが使える最も安定したofficial discovery routeを評価してください。

- e-Stat API、catalog、dataset landing、direct fileのどれをsource of truthにするか
- 警察庁landing pageからのlink discovery方法
- 公開schedule／更新頻度
- revision、差替え、正誤情報を検出する手掛かり
- HTTP metadata、filename、file hash、publication metadataのうち何を保存すべきか
- robots、利用規約、出典表記、加工表示の要件
- URLやschemaが変わったときのfailure-safeな検知方法

「direct URLを年だけ置換する」といった推測依存の方法と、official catalogから毎回発見する方法を区別してください。

### Q5. `国籍 × 都道府県`分子の限定的な追加探索

routine official sourceで個別国籍と都道府県を同時に持つ犯罪統計が本当に公表されている場合だけ、追加候補として示してください。対象は警察庁、e-Stat、法務省、都道府県警のofficial sourceに限定します。

- 全国47都道府県警を網羅したという主張は、実際に47件確認しない限りしない。
- 数県のsample調査なら、sample selectionと検索式を明記し、`sampled absence`と表現する。
- 報道、blog、集計siteは発見の手掛かりには使えるが、数値のground truthにはしない。
- joint dimensionが見つからなくても失敗ではない。探索範囲を限定したabsence claimとして報告する。

## 5. 評価するcandidate indicator

次のsource pairについて、値そのものを計算するのではなく、実装可能なindicator contractを設計してください。`cleared_cases`版と`cleared_persons`版は分けてください。

- X: S08相当の全国・国籍別外国人検挙数 ÷ S14相当の同国籍の在留外国人人口
- Y: S09相当の全国・国籍別来日外国人検挙数 ÷ S14相当の同国籍の在留外国人人口
- Z: S02相当の都道府県別来日外国人aggregate検挙数 ÷ S14相当の同都道府県の在留外国人総数

各contractに以下を含めてください。

- machine-readable indicator ID
- 誤解を招きにくい日本語名／英語名
- numerator metric、population scope、geography、period、source table
- denominator metric、population scope、geography、reference date、source table
- formulaとscale候補（1,000人当たり／10万人当たり等。推奨理由も記載）
- 必須mismatch flags
- UIに常時表示する短いcaveat
- 計算を拒否すべき条件

少なくとも次のmismatchを検討してください: annual flow vs point-in-time stock、visitor/non-resident inclusion、nationality category mismatch、China/Taiwan/Hong Kong grouping、national vs prefectural geography、police geography semantics unresolved、aggregate nationality numerator、small denominator、suppressed/missing value、period lag。

## 6. 調査方法とevidence rule

- 15〜30件程度の、実際に開いたrelevant sourceを使ってください。
- official primary sourceを最優先し、学術資料は定義・方法上の補助に限定してください。
- 検索結果snippetだけで結論を出さず、key URLを開いて本文、metadata、download linkを確認してください。
- binary fileを取得できたか、landing pageのみ確認したかを分けて記録してください。
- 事実、sourceに基づくinference、researcherの提案を明示的に分けてください。
- 最新・現行という表現には、調査実行日と確認した対象期間を必ず付けてください。
- `見つからない`は、検索対象、検索式、期間、確認siteを示すscoped claimにしてください。
- 同じinstitution内の複数pageを数だけ増やす目的で列挙せず、主張を支えるsourceだけを採用してください。
- citationは該当文の直後に置き、search result pageではなく根拠pageへ直接linkしてください。
- source間で矛盾した場合は、両方を示してどちらを採用したか、または未解決かを説明してください。

## 7. 必須deliverables

日本語のMarkdown reportとして、次の順で出力してください。

1. **Executive summary** — 確定事項、未解決事項、実装への影響を各5項目以内
2. **Verified source registry** — publisher、official title、table、period、stable ID、landing URL、download/API route、format、dimensions、definition note、license、access verification date
3. **2015–latest schema evolution matrix** — 系列別・年別。未確認cellは空欄ではなく`not verified`または`not published`を区別
4. **Definition and geography findings** — official factとinferenceを分離
5. **Indicator registry X/Y/Z** — cases/personsを別IDで記載し、formulaとmismatch flagsを完全に示す
6. **Acquisition/update recommendation** — source discovery → download → hash/provenance → parse → validation → publish gate
7. **Evidence gaps and exact questions** — 警察庁／出入国在留管理庁に送れる具体的な照会文
8. **Prioritized next actions** — 実装順のTODOを最大10件、各項目に`blocker / non-blocker`、期待成果、依存関係を付ける
9. **Source list** — title、publisher、URL、accessed date、何を裏付けるか
10. **Machine-readable appendix** — 以下の2つをvalid JSON code blockで出力
    - `sources` array: `source_id`, `publisher`, `dataset`, `table`, `period`, `stable_ids`, `landing_url`, `download_url`, `format`, `dimensions`, `definitions`, `license_url`, `verified_at`, `verification_level`
    - `indicators` array: `indicator_id`, `label_ja`, `label_en`, `numerator`, `denominator`, `formula`, `scale`, `mismatch_flags`, `refuse_if`, `ui_caveat`

## 8. Completion criteria

次を満たした場合にのみ完了としてください。

- 3系列すべてにverified source registry entryがある。
- 2015年から最新まで、各年のverification statusが明示されている。
- 表13のgeography semanticsが、確定またはevidence付きの`unresolved`として整理されている。
- X/Y/Zのcases/persons contractが別々に定義されている。
- project-derived ratioをofficial crime rateと表現していない。
- 推計や欠損補完を行っていない。
- 重要な主張にdirect citationがある。

report先頭に調査実行日時とknowledge cutoffではなく`web verification cutoff`を記載してください。長い調査過程ではなく、検証可能な最終reportを返してください。

---

ChatGPTで実行した場合は、reportをMarkdownとしてexportし、このprojectへ持ち込む際は `inbox/YYYYMMDD_HHMMSS_deep_research_schema_definitions/report.md` に配置してください。`inbox/`投入後はproject側でread-onlyの提供物としてtriageします。
