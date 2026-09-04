# logbook — nationality-crime-atlas

判断・気づき・失敗・トラブルシュート・試行錯誤の選別ログ（ハイライト層 / append-only）。
1 エントリ = **いつ / 何が / どう判断 / なぜ**（＋関連パス）。詳細成果物は `docs/` にリンク。

---

## 2026-08-29 project 開始
- **何が**: 都道府県別・国籍別の犯罪統計と在留人口の収集・可視化を開始。信頼できる情報源を検証し、全国・都道府県別・地域別の国籍別在留人口と犯罪統計を定期収集・更新して、人口当たりの比率をGitHub上で可視化する。
- **どう判断**: `$custom-init-project` で `code / analysis` の場を scaffold。
- **なぜ**: data collection、定期更新、可視化のコードとデータをこの repo 内で管理するため。

## 2026-08-29 living brief の叩き台作成
- **何が**: `docs/brief.md` に背景、目的、M0–M5、解釈レベルの現在地、想定成果を作成。READMEとworkflowからbriefへ接続した。
- **どう判断**: 現在地をM0「scope・指標定義」とし、`認知件数`・`検挙件数`・`検挙人員`、国籍区分、在留人口の範囲、地理・期間、rate単位を先に確定する。未回答の想定成果と自動化方式は「要確定」とした。
- **なぜ**: 分子と分母の母集団が一致しなければ人口当たりrateが誤解を生み、情報源の信頼性と比較可能性を追跡できないため。
- **関連パス**: `docs/brief.md`, `docs/workflow.md`, `README.md`, `README.ja.md`

## 2026-08-30 source availability audit 完了
- **何が**: 警察庁、e-Stat、出入国在留管理庁、既存研究・二次実装候補を監査し、`docs/20260830_085603_source_availability_audit.md` と raw trace を作成した。
- **どう判断**: `国籍・地域 × 都道府県` の在留人口は取得可能、全国の `国籍 × 罪種 × 検挙件数／検挙人員` は取得可能、都道府県の犯罪統計は全体または `来日外国人` aggregate までは取得可能と判定した。一方、routine official source の `国籍 × 都道府県` joint crime numerator は確認できなかったため、exact rate は no-go、count-only / provenance-first MVP は conditional go とした。
- **なぜ**: joint numerator を推計で埋めると provenance と解釈の両方が壊れ、`来日外国人` と `在留外国人` の母集団不一致を隠してしまうため。
- **関連パス**: `docs/20260830_085603_source_availability_audit.md`, `agent_logs/20260830_085603_source_audit/research_trace.md`, `docs/brief.md`, `docs/workflow.md`, `README.md`, `README.ja.md`

## 2026-08-30 independent review の未完了を明示
- **何が**: high-stakes claimをfresh reviewerで2回反証しようとしたが、どちらも指定したclaim-by-claim evidenceではなくproject要約を返した。1回目はread-only指示に反してcover documentsも更新した。
- **どう判断**: reviewer出力を独立検証として数えず、root processが差分を確認してaudit findingsと一致するdocument更新だけを保持した。主要URLの再open、代表fileのschema・SHA-256確認はroot検証済み、independent adversarial reviewは未完了とlabelする。
- **なぜ**: separate agentを起動した事実と、実際にload-bearing claimを反証できたことは同じではないため。
- **関連パス**: `docs/20260830_085603_source_availability_audit.md`, `agent_logs/20260830_085603_source_audit/research_trace.md`

## 2026-08-30 参考比率をsource pairごとに公開する方針へ変更
- **何が**: userから、国の組織間で別指標を数えている以上、整合する分子が得られること自体が不明であり、完全一致をproject goal・milestoneにするのは適切でないとの指摘があった。正確な犯罪率の整備は国・政治の問題として切り分け、「世の中に表示された公的dataを単純に割った場合どれくらいか」という一指標を示す方針が提示された。
- **どう判断**: M0 publication ruleを完了とした。numeratorがX/Y、denominatorがZ/Wの場合を別indicator IDとして定義し、分子・分母・算式・出典・期間・地理・母集団の不一致を毎回表示する。名称は`公表統計由来の参考比率`とし、officialまたは正確な`犯罪率`とは呼ばない。欠けた`個別国籍 × 都道府県`分子は推計しない。
- **なぜ**: 完全一致を待つと実現可能性が不明な政治・行政上のdata整備をprojectのblockerにしてしまう一方、source pairを明示した単純計算なら、限界を隠さず再現可能な情報を提供できるため。
- **次**: userは3 parser、正規化、count＋indicator MVP、警察庁照会trackを妥当と判断。M2の3 parser prototypeへ進める。
- **関連パス**: `docs/brief.md`, `docs/workflow.md`, `docs/20260830_085603_source_availability_audit.md`, `README.md`, `README.ja.md`

## 2026-08-30 M2 parser coreをtest-firstで実装・実source検証
- **何が**: ISA在留外国人統計表1、NPA表130／131、NPA表13の3 parser、normalized dataclass、source registry、SHA-256／magic-byte format detection、JSONL＋manifest CLIを実装した。最初にproduction moduleが存在しない状態でtest collection failureを確認し、schema/error/CLI/registry testを満たす実装へ進めた。
- **どう判断**: M2を「parser coreは検証済み、acquisitionとproduction quality gateは進行中」と区切る。sourceごとの具体的な列・rowを保持しつつ、表13の地理は意味を断定せず`police_reporting_area_unresolved`として出力する。legacy XLSとXLSXは拡張子ではなくmagic byteで区別する。
- **なぜ**: official workbookにはhidden data sheet、merged header、legacy XLS、年次schema driftがあり、download拡張子や表示sheetだけを信頼するとsilent failureになり得るため。完全一致しないsourceを無理に共通化せず、raw definitionとsource rowまで追跡可能にするため。
- **検証結果**: 17 test成功、skip 0、branch計測を有効にしたtotal coverage 88.06%。実sourceではISA表1 468,641 record（合計4,125,395、period end `2025-12-31`）、NPA表130 33 record、表131 30 record、表13 360 recordをparseした。CLI smoke testは表130から33 JSONL recordとhash／format／record countを含むmanifestを書き出した。
- **integrity evidence**: ISA XLSX SHA-256 `3a7c603c42927fc441ba0c062777223754d238df904bd15a034220dffd229a86`、NPA表130 XLSX `23ccb60d89c9b4bdaa898105753506a61d8354a0ae87b01598f6c97f4efd6a83`、NPA表13 legacy XLS `0404e10b0ab45b35f9be86c7b748bb039469cff2efc63584b2ac9660056b7323`。
- **次**: official catalog discovery、publication date／revision、immutable `data/raw/` snapshot、canonical mapping、全量row／duplicate／aggregate／schema drift gateを順に追加する。年次continuity・定義・表13 geography semanticsはfocused Deep Researchを並行実行できる形にした。
- **関連パス**: `src/nationality_crime_atlas/`, `tests/`, `config/sources.json`, `docs/brief.md`, `docs/workflow.md`, `docs/20260830_135535_parallel_deep_research_prompt.md`

## 2026-08-30 Deep Research非依存のM2 offline pipelineを完成
- **何が**: 取得済みofficial artifactをimmutable raw snapshotへpromoteする`nca-snapshot`、source/version-specific baselineでnormalized JSONLをstream検証する`nca-validate`、snapshot → parse → validateをatomicに束ねる`nca-pipeline`をtest-firstで実装した。
- **どう判断**: source discovery／定義調査とoffline processingを分離した。rawは`source_id × timezone付きretrieved_at`で一意にし、同一hashはidempotent reuse、異なる内容はconflictで停止する。processedはartifact hash、normalized hash、quality profile hash、run manifestを再検証し、quality pass時だけ昇格する。quality profileは特定artifact versionのbaselineとし、新公表年で既存profileを上書きしない。
- **なぜ**: Deep Researchを待たずにprovenanceとfailure-safe publication gateを固められ、将来discovery routeや定義が変わってもregistry/profileの更新でpipeline本体を保てるため。silent schema drift、誤file、partial output、同じ日時への上書きをpublish前に止めるため。
- **検証結果**: 3回のcompile-time REDを経て、38 test成功、skip 0、branch計測を有効にしたtotal coverage 86.71%。実artifact統合runではS14 468,641、S08 33、S09 30、S02 360 recordがすべてduplicate 0／quality error 0でpassし、4 sourceとも2回目は`reused=True`。S14 20,690,146-byte XLSXと、`.xlsx`名だが実体がlegacy XLSのS02で元／snapshot SHA-256一致も確認した。
- **次**: Deep Research reportからstable discovery route、publication/revision metadata、定義、canonical mappingを反映し、automatic downloaderとformal production runへ進む。
- **関連パス**: `src/nationality_crime_atlas/snapshot.py`, `src/nationality_crime_atlas/quality.py`, `src/nationality_crime_atlas/pipeline.py`, `config/quality_profiles.json`, `tests/test_snapshot.py`, `tests/test_quality.py`, `tests/test_pipeline.py`, `docs/workflow.md`

## 2026-08-30 user-provided Deep Research 2本を比較・一次検証
- **何が**: inboxへ持ち込まれたClaude Opus 5版とChatGPT 5.6 sol版を比較し、現行binary identity、表番号・format transition、population／crime definition、Table 13 geography、same-year pairing、indicator scaleの主要主張を官庁の一次page・文書と取得済みbinaryで再確認した。
- **どう判断**: 実装材料は現行4 artifactのSHA-256までproject側と一致したChatGPT版を主に採用する。Claude版は高水準のcaveat整理に限定し、Table 13 geographyの断定、ZへのChina grouping影響、S02 format、scaleによる不安定性解消という主張は採用しない。Table 13は`police_reporting_area_unresolved`を維持する。X/Yは2024年表130/131 × 2024年末T1、Zは2025年表13 × 2025年末T1とする。canonical quotientとdisplay multiplierを分離し、exact crosswalkとas-published mismatch indicatorを別契約にする。
- **なぜ**: current numeratorと取得済みdenominatorは年が一致せず、表13の刑法犯・特別法犯を単一の地理semanticで説明する一次根拠も不足しているため。また、倍率変更は小分母の統計的不安定性を解消せず、user-approved方針では公表raw label間の不一致を隠さず参考値として示す必要があるため。
- **検証境界**: 現行4 binaryと代表年のofficial landing／metadataは検証済み。2015–2025の全candidate IDはreport-onlyまたは部分検証を含み、production registryへpinする際に年度ごとのbinary確認が必要。
- **次**: source registry v2、2024年末T1の取得・検証、canonical mapping／value status、indicator contract、current formal runの順に進める。
- **関連パス**: `docs/20260830_183123_deep_research_comparison.md`, `docs/brief.md`, `docs/workflow.md`, `README.md`, `README.ja.md`, `inbox/20260830_174918_compass_artifact_wf-1be02b71-814f-5876-bfed-82fb88a99ccb_text_markdown.md`, `inbox/20260830_181535_report.md`

## 2026-08-30 M2 current acquisition baselineを正式収集
- **何が**: source registryをseries／immutable edition分離のschema v2へ移行し、registered HTTPS URLからtemporary download → size／format／pinned SHA-256 → raw snapshot → parse／quality → processed promotionを行う`nca-acquire`と、raw manifest・processed quality/runをjoinするartifact catalogをtest-firstで実装した。2024年末T1を追加し、current 5 editionを正式収集した。
- **どう判断**: permanent download先は`data/raw/<series>/<edition>/<retrieved_timestamp>/`に一本化し、partial downloadはsystem temporary directoryから昇格させない。通常再実行は既存validated editionをnetworkなしでreuseし、`--refresh`でも同一hashならsnapshotを増やさない。異なるhashはsilent revisionとして受け入れず、新edition/revisionのreviewまで停止する。大容量`data/processed`はgitignoreし、compactな`_catalog/artifacts.{jsonl,csv}`だけをGit追跡可能にする。
- **なぜ**: 一時領域での検証だけでは「何を実際に収集したか」がprojectに残らず、定期実行で同一binaryを重複保存するとprovenanceと容量管理の両方が壊れるため。source plan、artifact receipt、全体inventoryを別レイヤーにすると、予定と実績を混同せず追跡できるため。
- **検証結果**: 47 test成功、skip 0、branch計測total coverage 85.06%。S08 33、S09 30、S02 360、S14_2024_12 444,173、S14 468,641 recordが全てduplicate 0／quality error 0。catalog 5 rowは全件`validated`。S08はnetworkなしの再実行とremote `--refresh`の双方で`reused=True`、raw snapshotは増加しなかった。
- **troubleshooting**: editable installはisolated buildでPython 3.9環境内の`pip`を見失ったため失敗した。`--no-build-isolation`へ切り替えて成功し、project commandにも同optionを固定した。
- **次**: canonical nationality／geography mappingとvalue status、次にindicator contract。official catalog discovery、schedule、historical backfillはその後。
- **関連パス**: `config/sources.json`, `config/quality_profiles.json`, `src/nationality_crime_atlas/acquisition.py`, `src/nationality_crime_atlas/catalog.py`, `data/raw/`, `data/processed/`, `data/processed/_catalog/artifacts.csv`, `docs/data_management.md`, `docs/workflow.md`

## 2026-08-30 M2 canonical dimension mapping baselineを確定
- **何が**: current 5 edition、913,237 normalized rowからdistinctな国籍・地域／geography labelを抽出し、ISA source codeをcanonical referenceとして`matched / ambiguous / unmatched`を生成する`nca-map-dimensions`をtest-firstで実装した。timestamp付きJSONL／CSV／summaryとhash付き`latest.json`を`data/processed/_mappings/`へ出力した。
- **どう判断**: mappingはlabel/category crosswalkに限定し、indicator compatibilityとは分離する。NPA `中国`はISAに同名labelがあっても「台湾、香港等を含む」というsource注記を優先してambiguousとし、`韓国・朝鮮`もISA 2 categoryへ分解せずambiguousにする。source region total、警察region、北海道方面を単一categoryへfuzzy変換せず、context別`その他`と`国籍不明`はunmatchedのまま保持する。
- **なぜ**: 文字列一致を統計的同値と誤認すると、ユーザーが求める「どの公表data同士を割った値か」というprovenanceを隠し、複合国籍categoryや警察統計上の地理区分を誤って人口分母へ接続するため。
- **検証結果**: 612 mappingの内訳はmatched 578／ambiguous 26／unmatched 8。ISA 2024の196 code/labelは2025でも全件不変で、2025にモナコ1 categoryが追加。S02の47都道府県は全件matched、population self-mappingのnon-matchedは0。mapping関連15 test、全62 test成功、skip 0、branch計測total coverage 85.71%。generated summary／mapping hashも`latest.json`と一致した。
- **次**: X/Y/Zを別IDで定義するindicator contractを実装し、period、population scope、flow/stock、geography semantics、nationality grouping mismatchをsource pairごとに固定する。mapping statusだけでratio計算を許可しない。
- **関連パス**: `config/dimension_mappings.json`, `src/nationality_crime_atlas/dimensions.py`, `src/nationality_crime_atlas/dimension_cli.py`, `tests/test_dimensions.py`, `data/processed/_mappings/20260830_213259_dimension_mapping/`, `docs/20260830_213259_dimension_mapping_audit.md`, `docs/workflow.md`

## 2026-08-30 authored mapping ruleをreview済みsourceへscope
- **何が**: initial mapping reviewで、raw labelだけをkeyにしたruleは将来別sourceの同名labelにもNPA固有注記を誤適用し得ると判明した。
- **どう判断**: alias、composite、unmatched、region ruleにreview済み`source_ids`を必須化した。現行は`S08`／`S09`だけを許可し、未reviewの新source IDではexact-label fallbackをせず`SchemaError`で停止する。
- **なぜ**: current mappingが正しくても、将来editionへsilentに意味を持ち越すとsource-specific provenanceとschema drift reviewが壊れるため。
- **検証結果**: 未review `S99`の`中国`で停止するRED→GREEN testを追加。production mappingをimmutableな新runとして再生成し、判定数はmatched 578／ambiguous 26／unmatched 8で不変。全63 test成功、skip 0、total coverage 85.71%。
- **関連パス**: `config/dimension_mappings.json`, `src/nationality_crime_atlas/dimensions.py`, `tests/test_dimensions.py`, `data/processed/_mappings/20260830_214058_dimension_mapping/`, `docs/20260830_214058_dimension_mapping_audit.md`

## 2026-08-31 canonical mappingのfresh independent review完了
- **何が**: 実装に関与していないfresh reviewerが、mapping rule、engine、test、latest production run、audit documentをread-onlyでadversarial reviewした。
- **どう判断**: blocking／high-severity findingは0件。semantic status、source-specific scoping、raw context／provenance、atomic output、docsとproduction outputの一致が独立に確認されたため、canonical mapping subphaseを完了とする。
- **なぜ**: 国籍categoryと犯罪統計の誤接続はhigh-stakesであり、実装者自身の確認だけでなく独立した反証確認が必要なため。
- **検証結果**: reviewer側でもmapping test 16件が成功し、production mapping 612 row／unique 612、matched 578／ambiguous 26／unmatched 8、source別件数を再確認した。
- **関連パス**: `docs/20260831_000754_dimension_mapping_independent_review.md`, `docs/20260830_214058_dimension_mapping_audit.md`, `data/processed/_mappings/20260830_214058_dimension_mapping/`

## 2026-08-31 indicator contract v2とfirst validated data productを確定
- **何が**: 途中実装されていたindicator contract／generatorを要件と実データに照らして監査し、scope drift、duplicate、期待row数、exact mapping completeness、strict period、source provenanceの不足をRED testで再現した。contract schema v2とoutput schema v2へ更新し、current same-year dataから290 indicator recordを生成した。
- **どう判断**: 6 conceptual case（X/Y/Z × cases/persons）を、X/Yの`exact`／`as_published_mismatch`を分けた10 publication contractとして管理する。`calculation_status`と`statistical_compatibility=not_established`を分離し、計算できてもofficialまたは正確な`犯罪率`とは呼ばない。人口1,000人当たりはdata factではないため`display_scale_status=provisional`とし、canonical quotientを別fieldで保持する。
- **なぜ**: mappingの文字列対応だけで統計的compatibilityを推定せず、母集団、flow/stock、地理semantic、国籍groupingの不一致を残したまま、公表dataの単純除算を再現・監査できる形にするため。edition-specific expected row gateにより、47都道府県の欠落やsource scope driftをsilentに公開しないため。
- **検証結果**: authoritative runは250 calculated／40 refused。Zは47都道府県×cases/personsの94件を計算。formula不一致0、refused rowへの値残存0、invalid exact calculation 0。full suite 73 test、skip 0、branch計測total coverage 84.40%。JSONL／CSV／summary hashは`latest.json`と一致した。
- **troubleshooting**: 最初の`20260831_084201_indicators`は新fieldを持つのにoutput schema versionが旧`1`のままだった。RED testで検出してversion `2`へ修正し、`20260831_084358_indicators`を再生成してlatestへ切り替えた。pre-fix runは公開対象にしない。
- **次**: denominator 1,000人未満等のsmall-denominator flag基準、因果・個人riskとして解釈しない常設note、primary UI policy／scaleを決める。current dataでcandidate threshold 1,000人未満に該当する具体例は`無国籍` denominator 468。generated `_indicators/`はgitignore対象なので、M4でGitHub公開用compact exportまたはCI build方式を確定する。
- **関連パス**: `config/indicator_contracts.json`, `src/nationality_crime_atlas/indicators.py`, `tests/test_indicators.py`, `data/processed/_indicators/20260831_084358_indicators/`, `docs/20260831_084358_indicator_contract_and_run_audit.md`, `docs/workflow.md`

## 2026-08-31 processed indicator inputの事後改変gateを追加
- **何が**: final integrity reviewで、artifact catalogはraw SHA-256をpinしている一方、indicator generatorがvalidated後の`normalized.jsonl`をprocessed runのhashへ再照合せず読んでいることが判明した。また、negative population cellが正のaggregateに紛れる余地があった。
- **どう判断**: indicator生成前に各required sourceの`normalized.jsonl`を`run.json.normalized_sha256`へ再照合し、`quality_passed=true`とsource IDも確認する。normalized hashをindicator summaryの`source_artifacts`へ追加し、negative population cellはaggregate前に停止する。
- **なぜ**: raw artifactが正しくてもprocessed inputがvalidation後に変われば、公開比率のprovenanceと再現性が壊れるため。aggregate denominatorが正なら個別negative cellを許す、というsilent failureを避けるため。
- **検証結果**: hash mismatchとnegative population cellのRED→GREEN testを追加し、indicator 12 test／full suite 75 testが成功、skip 0、branch計測total coverage 84.36%。authoritative runを`20260831_085216_indicators`として再生成し、250 calculated／40 refusedは不変。JSONL／CSV／summary hashはlatestと一致した。
- **関連パス**: `src/nationality_crime_atlas/indicators.py`, `tests/test_indicators.py`, `data/processed/_indicators/20260831_085216_indicators/`, `docs/20260831_085216_indicator_contract_and_run_audit.md`

## 2026-08-31 processed indicator inputを独立contract hashでもpin
- **何が**: fresh reviewで、indicator generatorのprocessed-input照合が`normalized.jsonl`と同じprocessed directoryの`run.json`だけに依存し、両方をcoordinated editした場合は検知できないことが判明した。
- **どう判断**: `config/indicator_contracts.json`へrequired 5 sourceの`processed_input_pins`を追加し、実file／processed run manifest／version-controlled contract pinのSHA-256三者一致をhard gateにした。sibling file二つを同時に変えてもcontract pinとの差で停止するRED→GREEN testを追加した。
- **なぜ**: validation済みprocessed inputのidentityを、同一run directoryの自己申告だけでなくreview可能なauthored contractへ固定し、公開data productの再現性とtamper evidenceを強めるため。
- **検証結果**: authoritative runを`20260831_085815_indicators`として再生成し、250 calculated／40 refusedは不変。独立再集計でinput hash不一致0、250 rowのformula不一致0、atomic T1 denominator不一致0、refused value leak 0、Z prefecture ID 47件を確認した。full suite 76 test、skip 0、branch計測total coverage 84.37%。
- **troubleshooting**: 最初の独立denominator auditでZの94 rowだけ不一致と出たが、audit scriptがoutputの`entity_dimension="geography"`を`"prefecture"`と誤認してnationality aggregateを参照したことが原因だった。分岐を実schemaに合わせて再実行し、不一致0を確認したためproduct defectではない。
- **関連パス**: `config/indicator_contracts.json`, `src/nationality_crime_atlas/indicators.py`, `tests/test_indicators.py`, `data/processed/_indicators/20260831_085815_indicators/`, `docs/20260831_085815_indicator_contract_and_run_audit.md`

## 2026-08-31 indicator processed-input pinのfresh independent review完了
- **何が**: 先行reviewで指摘されたself-referentialなprocessed-input integrity checkに対するfixを、実装に関与していないfresh reviewerがread-onlyで再検証した。
- **どう判断**: blocking／high／medium findingは0件で、先行Medium findingをclosedとする。5 required sourceのpin、missing-pin gate、coordinated-edit regression test、current runとdocsの整合を独立に確認できた。
- **なぜ**: 犯罪統計と人口を結ぶdata productはhigh-stakesであり、実装者側のRED→GREENと数値auditだけでなく、指摘者によるfix再確認が必要なため。
- **検証結果**: reviewer側でもindicator 13 test、full 76 test、coverage 84.37%をpass。5 sourceの`file == run.json == contract pin`、290 record／250 calculated／40 refused、refused-value leak 0、Z prefecture 47件を確認した。
- **残る境界**: contract pin自体を意図的に変更する主体はruntimeでは防がない。pin更新を新edition／parser／quality changeと一緒にreviewするgovernanceで担保する。
- **関連パス**: `docs/20260831_090540_indicator_independent_review.md`, `docs/20260831_085815_indicator_contract_and_run_audit.md`, `config/indicator_contracts.json`, `AGENTS.md`

## 2026-08-31 small-number thresholdをdenominator／numerator別にsensitivity audit
- **何が**: small-denominator warningの候補を決めるため、latest indicator outputを対象にdenominator 7 threshold（100–50,000）とnumerator 5 threshold（1–50）を再現可能に比較するanalyzer／CLIをtest-firstで実装した。
- **どう判断**: thresholdはまだpublication policyへ昇格させず、`policy_status=sensitivity_only`とした。affected calculated record数と、exact／as-publishedやmetric viewの重複を除いたunique observation数を併記する。厚労省、NCHS／CDC、ONSの一次資料を比較し、fixed denominator cutoffだけをofficial ruleとして流用しない。
- **なぜ**: small-number問題はdenominatorだけでなくevent count、1件単位の離散性、推定modelに依存するため。本projectはnumerator／denominatorの母集団compatibilityが未確立で、CIやBayesian smoothingを入れると存在しないrisk modelを暗黙に仮定するため。
- **結果**: denominator `<500`／`<1,000`／`<2,000`はすべて`無国籍`468人の1 observation（8 record）のみ、`<5,000`で`イラン`4,399人が追加。numerator `<20`は12 unique observation／20 record。dual warning unionは20 / 250 calculated record。
- **提案**: denominator `<1,000`を`small_denominator_base`、numerator `<20`を`sparse_numerator_count`として別々に表示し、suppressionせずraw count/baseを併記、default rankingから除外する。official reliability thresholdとは呼ばず、user approval後にcanonical contractへ実装する。
- **検証結果**: focused 4 test、full suite 80 test成功、skip 0、branch計測coverage 84.27%。独立set-based再集計で12 threshold summary、119 sensitivity record、input／output hashが一致した。
- **関連パス**: `config/small_number_sensitivity.json`, `src/nationality_crime_atlas/small_numbers.py`, `src/nationality_crime_atlas/small_number_cli.py`, `tests/test_small_numbers.py`, `data/processed/_indicator_sensitivity/20260831_205122_small_number_sensitivity/`, `docs/20260831_205122_small_number_sensitivity_audit.md`

## 2026-08-31 small-number warning policyを適用し、sensitivity input provenanceを固定
- **何が**: 承認されたproject heuristicとしてdenominator `<1,000`とnumerator `<20`を別warningにし、canonical indicatorへrow-level flagとdefault ranking除外hintを追加した。常設interpretation noteも作成した。続くfresh reviewで、初回sensitivity runがmutableなindicator `latest.json`のpath／hashだけを記録していたMedium findingを検出した。
- **どう判断**: warningは値をsuppressionせず、raw numerator／denominatorと一緒に表示する。flagged rowはdefault rankingとtop／bottom calloutから外すがfilter閲覧は残す。sensitivity analyzerは参照したpointer payloadを各immutable run内の`indicator_input_manifest.json`へ複製し、summaryとsensitivity pointerの双方からhash固定する。
- **なぜ**: thresholdはofficial crime-statistics reliability ruleではなくproject UI guardであるため、元dataを隠さず、解釈上の強調だけを制御する必要がある。また外部の`latest.json`が次runへ移動すると、過去runが何を解決したかをhashだけでは復元できないため。
- **検証結果**: indicator 290 rowは250 calculated／40 refused。strict predicateの独立再計算はsmall denominator 8、sparse numerator 20、union 20で保存flagと全件一致し、誤flag・refused flag・ranking mismatchはいずれも0。warning field 5個を除くと旧canonical runの290 rowと完全一致した。provenance fixはREDでmanifest不在を再現し、GREENでfocused 5 test成功。修正版sensitivity runは119 record、旧runと12 threshold summaryが一致。full suite 82 test、skip 0、branch計測coverage 84.33%。post-fix fresh reviewは元のMedium findingをclosedとし、残存finding 0だった。
- **次**: M4のprimary UI policy（exact / as-published、count / ratio、display scale）とGitHub公開用compact exportを確定する。
- **関連パス**: `config/indicator_contracts.json`, `src/nationality_crime_atlas/indicators.py`, `src/nationality_crime_atlas/small_numbers.py`, `tests/test_indicators.py`, `tests/test_small_numbers.py`, `data/processed/_indicators/20260831_215800_indicators/`, `data/processed/_indicator_sensitivity/20260831_225300_small_number_sensitivity/`, `docs/20260831_215800_indicator_warning_policy_audit.md`, `docs/20260831_225300_small_number_sensitivity_provenance_reaudit.md`, `docs/interpretation_note.md`

## 2026-09-01 日本国籍ではなく全住民をprimary regional baselineに確定
- **何が**: userが、国籍へのレッテル貼りや定量的根拠のない印象操作を避け、数字を正しく集め公正に比較・可視化して事実ベースの対策につなげたいというproject背景を明示した。警察庁表3／144と統計局人口推計を一次・binary確認し、all-person prefecture crime S15とOctober 1 total population S16を追加した。
- **どう判断**: primary comparatorは`日本国籍`ではなく、日本に居住する全住民とする。nationality viewはsecondary。S15 / S16の同年pairは`descriptive regional context`として利用可能だが、official crime rateや個人の犯罪発生確率とは呼ばない。存在しない`個別国籍 × 都道府県`分子、日本国籍prefecture分子は推計しない。national total − all-foreign residualもdirect日本国籍値としてはpublishしない。
- **なぜ**: 特定nationalityをdefault referenceにするとnormative framingになり得る一方、全住民contextなら地域全体の差とnationality表示を分離できるため。2024年実dataでも東京都は埼玉県より認知件数のabsolute countが多いが、全住民10万人当たり認知件数では順序が逆になり、metric／denominatorの明示が不可欠と確認できたため。
- **検証結果**: S15 60 row、S16 48 row、duplicate／quality error 0。47 prefecture label set一致、S15 prefecture sumはnational 3 metricへ一致、S16の1,000-person差はsource丸めどおり。mappingは720（matched 674／ambiguous 38／unmatched 8）。再生成indicator 290 rowはprevious canonical JSONLとbyte-identical。full suite 91 test、skip 0、branch coverage 84.59%。
- **次**: S15 / S16をpinした`all_resident_regional_context` contract／generator → refusal rules → compact export → 全住民contextをdefaultとするvisualization MVPの順に進める。
- **関連パス**: `src/nationality_crime_atlas/npa_all_residents.py`, `tests/test_npa_all_residents.py`, `config/sources.json`, `config/quality_profiles.json`, `data/raw/npa-all-persons-prefecture-crime/S15/`, `data/raw/npa-total-population-prefecture/S16/`, `data/processed/_mappings/20260901_133220_dimension_mapping/`, `data/processed/_indicators/20260901_133239_indicators/`, `docs/20260901_133313_all_resident_baseline_audit.md`, `docs/interpretation_note.md`

## 2026-09-01 全住民regional-context productを実装
- **何が**: S15 / S16専用の`all_resident_context` generator、CLI、contract configを追加し、`data/processed/_all_resident_context/20260901_153100_all_resident_context/`を生成した。README／workflow／brief／data managementにも現在地を反映した。
- **どう判断**: nationality indicatorとは別productに分離し、全国＋47都道府県の認知件数／検挙件数／検挙人員を計算する。警察region／subregion 12 rowはjoin不能なpublished geographyとして、日本国籍prefecture分子・個別nationality × prefecture分子は非公表request scopeとして、同じrunにmachine-readable refusalを残す。
- **なぜ**: 全住民contextはprimary UIの土台だが、nationality productとは別のrefusal境界とdisplay scaleを持つため。同じrunの中で calculated と refused を併記すると、「ない data を推計していない」ことを downstream に伝えやすいため。
- **検証結果**: `regional_context_records.jsonl`は186 row、144 calculated／42 refused。3 metricすべてで全国＋47 prefectureを計算し、numerator difference 0、denominator difference -1,000をsummaryへ固定した。東京の認知件数はabsolute countで埼玉より多いが、人口10万人当たりでは東京668.30、埼玉704.68。new test 4件を含むfull suiteは95 test成功、skip 0、branch計測total coverage 84.22%。
- **troubleshooting**: `compileall`による追加確認はmacOS側のPython cache directoryへ`.pyc`を書こうとしてsandbox権限で失敗した。pytest経由の実行検証と実データrunで代替し、生成物自体は正常と判断した。
- **次**: compact exportの形式を決め、M4のprimary UIを全住民contextから始める。count / per-population、exact / as-published、source noteの切り替えを同一画面で扱う。
- **関連パス**: `src/nationality_crime_atlas/all_resident_context.py`, `src/nationality_crime_atlas/all_resident_context_cli.py`, `config/all_resident_context_contracts.json`, `tests/test_all_resident_context.py`, `data/processed/_all_resident_context/20260901_153100_all_resident_context/`, `docs/20260901_153000_all_resident_context_product_audit.md`, `README.md`, `README.ja.md`, `docs/workflow.md`, `docs/brief.md`, `docs/data_management.md`

## 2026-09-01 compact dashboard exportを実装
- **何が**: `compact_export.py`、`compact_export_cli.py`、`nca-build-compact-export`を追加し、`output/compact_export/20260901_181500_compact_export/`を生成した。indicator productとall-resident context productを、future UIが直接読める1つのbundleへまとめた。
- **どう判断**: UIは`data/processed/*`のmutable `latest.json` pointerを直接読むべきではないため、resolved latest manifestそのものをhash付きでsummaryへ同梱する。record単位で繰り返されるlabel、formula、display metadataはdefinition層へ持ち上げ、rowには変動する情報だけを残す。
- **なぜ**: M4の可視化実装を始める前に、source identityと表示用schemaを固定したpublic-facing inputが必要だったため。all-resident primary viewとnationality secondary viewを同じbundleで供給できると、UIでの切り替えも安全に作れるため。
- **検証結果**: REDでは`tests/test_compact_export.py`がmodule未実装で3件失敗した。GREENでcompact export fixture test 3件成功、current dataから`290 + 186` rowの実bundle生成成功。full suiteは98 test成功、skip 0、branch計測total coverage 84.24%。
- **次**: `output/compact_export/`をGitHub-visibleなartifact laneまたはCI publicationへ接続し、そのbundleを読むvisualization MVPを作る。
- **関連パス**: `src/nationality_crime_atlas/compact_export.py`, `src/nationality_crime_atlas/compact_export_cli.py`, `tests/test_compact_export.py`, `output/compact_export/20260901_181500_compact_export/`, `docs/20260901_211700_compact_export_audit.md`, `README.md`, `README.ja.md`, `docs/workflow.md`, `docs/brief.md`, `docs/data_management.md`

## 2026-09-02 all-resident／compactの独立再監査を完了
- **何が**: 最初の2 review taskがread-only指示に反してproductを実装したため、それらをindependent reviewとして不採用にした。実装に関与していないstrict reviewerがall-resident contextとcompact exportをadversarialに監査し、見つかったfindingをRED → GREENで修正後、同じreviewerがread-onlyでclosureを確認した。
- **どう判断**: all-residentでは複数revisionをcontract pinで一意選択し、annual flow対10月1日時点stockとnumerator residency scope未確立を必須warningにした。compact schema v2ではrow IDを保持し、同じsource bytesからparse/hashし、summaryとrecordsを照合し、public source metadataだけをwhitelistし、root pointerをunique temp + `flush` + `fsync` + `replace`で公開する。
- **なぜ**: 可視化前のpublic-facing data boundaryで、definition joinの切断、provenance drift、concurrent pointer破損、private path露出、重要caveat脱落を防ぐ必要があるため。reviewを実装者の自己確認と分離するため。
- **検証結果**: current all-resident run `20260901_225500_all_resident_context`は186 row（144 calculated／42 refused）で旧runから数値変更0。current compact run `20260901_232700_compact_export`はschema v2、290 + 186 row、10 + 3 definitions、public source 7件、missing definition link 0、local absolute path 0。focused compact test 6件、full suite 106件が成功し、coverage 84.07%。fresh reviewerは旧findingをすべてclosedとし、scope内open finding 0だった。
- **残る境界**: 同一`generated_at`を使う2 writerのexact collision専用test、visualization UI、GitHub publication laneは未完了。
- **次**: current compact bundleを入力にlocal visualization MVPを作り、data／warning／refusal／source導線を実dataで検証した後、publication laneを決める。
- **関連パス**: `config/all_resident_context_contracts.json`, `src/nationality_crime_atlas/all_resident_context.py`, `tests/test_all_resident_context.py`, `src/nationality_crime_atlas/compact_export.py`, `tests/test_compact_export.py`, `data/processed/_all_resident_context/20260901_225500_all_resident_context/`, `output/compact_export/20260901_232700_compact_export/`, `docs/20260902_073831_all_resident_and_compact_independent_reaudit.md`

## 2026-09-02 local visualization MVPを実装し、独立review findingをclosed
- **何が**: current compact exportとbyte-identicalなstatic bundleを読む`web/` dashboardを実装した。全住民primary view、47都道府県map、count／人口当たり、東京・埼玉normalization、全国国籍別secondary view、source／warning／refusal導線を追加した。fresh read-only reviewは`検挙人員`のcount unit誤表示をHigh、map SVGのpinned hash未強制をMediumとして検出した。
- **どう判断**: UI defaultは全住民の認知件数を人口10万人当たりとし、nationality viewは全国集計だけをsecondaryに置く。person metricは`人／人員`、case metricは`件／件数`をsource semanticsから導出する。map generatorはCC0 SVGのchecked-in SHA-256不一致時にwrite前停止する。外部公開はpublication lane決定まで行わない。
- **なぜ**: 地域人口によるscale effectと国籍表示を分離し、非公表のjoint numeratorを作らず、表示labelとprovenanceもdata correctness gateに含めるため。documented pinだけではasset driftを防げないため、runtime gateとtamper testが必要だった。
- **検証結果**: regression RED後、frontend 22 test、branch coverage 81.00%、typecheck／lint／format／production build、local HTTP 200をpass。Python 106 test、coverage 84.07%。compact source／UI copyはSHA-256 `1617a13037899e862def08b9bab37c5facc711d6d195812d1faf8fa8d39395bc`でbyte-identical、private path match 0。same reviewerがHigh／Mediumを両方closedし、closure scopeのnew finding 0と判定した。
- **次**: GitHub Pages / `gh-pages`（推奨）かCI artifactかをuserが選択し、hash検証付きbundle syncとCI publicationを接続する。その後にhistorical edition／year filter、M5 discovery／scheduleへ進む。
- **関連パス**: `web/app/`, `web/components/crime-atlas-dashboard.tsx`, `web/components/prefecture-map.tsx`, `web/lib/dashboard.ts`, `web/scripts/generate-japan-map-data.mjs`, `web/tests/`, `docs/20260902_200948_visualization_mvp_audit.md`, `README.md`, `README.ja.md`, `docs/workflow.md`, `docs/brief.md`, `docs/data_management.md`

## 2026-09-03 日本人を欠落させない全国籍比較へ改訂
- **何が**: userから、primaryを全住民にする方針は維持しつつ、secondaryな国籍別表示から日本人が欠落すると比較のlandmarkがなく、top 10だけでは高い側へ恣意的に注目させるとの指摘を受けた。S17日本人人口を正式取得し、S15全体検挙人員 − S08全外国人検挙人員で日本人残差を作るproduct、compact export schema v3、日本を含むUIをtest-firstで実装した。
- **どう判断**: 日本人はnormativeな基準ではなく、全国籍比較の1 categoryとして人口1,000人当たりの同軸へ含める。direct公表値ではないため`日本（残差による参考値）`とし、`191,826 − 10,464 = 181,362`、分母120,296,000人、S08／S15／S17、reference date差、丸め、scope assumptionを表示する。同じ22 calculated rowから高い側5件／低い側5件を対称に示し、26 row全部と4 refusalを併記する。small-number rowも隠さずwarning付きで含め、価値判断は加えない。
- **なぜ**: 全住民regional contextと全国籍comparisonは役割が異なり、前者をprimaryにしても後者から日本を除く理由にはならないため。また高い側だけの切り出しは、数値を公正に見せるproject目的と衝突するため。
- **検証結果**: comparisonは26 row（22 calculated／4 refused）、日本は人口1,000人当たり1.507631。compact exportは186 + 26 + 290 row、schema v3、source 8件、dashboard SHA-256 `b0f950baa23aac85e44d644b4609ec0bd70d0567d307bfaf013377d85e4ee060`。Python 116 test、web 54 test、typecheck／lint／format／data hash／production buildをpassした。Browser skillでdesktop／390 px mobileを確認し、side-table warning列のclipを発見・修正して再目視した。
- **troubleshooting**: current S08 parser outputと旧indicator contract pinの不一致により、最初のproduction compact exportは安全に停止した。S08 identityを実processed artifactへ合わせ、exact pin regression testを追加して再生成した。またcatalog CSVのplatform依存CRLFをLFへ固定した。
- **次**: new comparison productとUIをfresh reviewerがread-onlyで監査し、findingをclosedする。review完了後、userの明示があればlocal commitをpushしてGitHub Pages deployed URLを実地確認する。historical trackでは時系列、small-denominator volatility、再現性、category／schema driftを扱う。
- **関連パス**: `config/nationality_comparison_contract.json`, `src/nationality_crime_atlas/nationality_comparison.py`, `data/processed/_nationality_comparison/20260903_074525_nationality_comparison/`, `output/compact_export/20260903_075440_compact_export/`, `web/public/data/dashboard_export.json`, `web/lib/dashboard.ts`, `web/components/crime-atlas-dashboard.tsx`, `docs/20260903_082238_japanese_nationality_comparison_and_ui_audit.md`, `README.md`, `README.ja.md`, `docs/workflow.md`, `docs/interpretation_note.md`

## 2026-09-03 GitHub Pages最終artifactのprivate-path false positiveを修正
- **何が**: `/nationality-crime-atlas` base pathでproduction build／prepareした32-file Pages artifactを検証すると、private local-path gateが停止した。match位置を調べると、実pathではなくvinext bundle内のescaped Unicode regex `\\u200B\\...`を不完全なUNC rootとして誤認していた。
- **どう判断**: gateを削除せず、UNC判定には`server + share`の完全な形を要求する。escaped Unicode fragmentを受理するRED testと、完全なUNC pathを引き続き拒否するtestを追加した。
- **なぜ**: false positiveのためにverified artifactを公開不能にせず、同時にbuild環境のpath漏洩検知を維持するため。
- **検証結果**: focused Pages test 8件、full web suite 56件、typecheck／lint／formatをpass。実32-file artifactはbase path、absolute OG URL、required files、symlink禁止、private path、dashboard SHA-256 `b0f950baa23aac85e44d644b4609ec0bd70d0567d307bfaf013377d85e4ee060`をpassした。sandbox内buildはprerender socketの`listen EPERM`で失敗し、同一buildを許可されたsandbox外で再実行して1 static route成功を確認した。
- **関連パス**: `web/scripts/sync-dashboard-export.mjs`, `web/scripts/verify-pages-artifact.mjs`, `web/tests/pages-artifact.test.ts`, `.github/workflows/pages.yml`, `docs/20260903_082238_japanese_nationality_comparison_and_ui_audit.md`

## 2026-09-03 Vietnamの表示差からnumerator scope変更を確認
- **何が**: userが、Vietnamの参考比率が旧画面の約7 / 1,000人からnew画面の約2 / 1,000人へ下がったように見えると指摘した。source rowを再照合すると、同じ2024年・同じ人口634,361人に対し、旧defaultはS08`総数・検挙人員`4,113人、新comparisonはS08`刑法犯・計・検挙人員`1,679人を使っていた。
- **どう判断**: `6.4837 → 2.6468`は時系列の減少ではなくmetric scope変更であり、増減として比較できない。new comparisonが刑法犯を使うのは、日本人残差のminuendであるS15 all-person値が刑法犯検挙人員だからで、S08側も同scopeにする必要があるため。計算は整合するが、旧UIとのtransition説明は不足している。
- **なぜ**: labelが同じ`検挙人員`を含んでも、source columnの`総数`と`刑法犯・計`ではnumeratorが異なる。ここを明示しなければ、実際には同一年の定義差をtrendと誤読させるため。
- **次**: current刑法犯比較にscope-change注記を常設するか、旧総数metricを日本=`refused`としてsupplementaryに残すか、UI変更前に方針を決める。historical viewではmetric ID／definitionが変わる区間を連続線で結ばない。
- **関連パス**: `data/processed/npa-all-foreign-nationality-crime/S08/20260830_201712_s08/normalized.jsonl`, `web/public/data/dashboard_export.json`, `src/nationality_crime_atlas/npa_nationality.py`, `docs/20260903_082238_japanese_nationality_comparison_and_ui_audit.md`

## 2026-09-03 日本人を含む固定metric comparisonのfresh review完了
- **何が**: current comparisonの実装に関与していないreviewerが、contract／generator、compact schema v3、published bundle、web model／UI、tests、living docsをread-onlyでadversarialに監査した。最初のnew reviewer spawnはservice usage limitで失敗したため、current comparisonに関与していない旧closure reviewerへnew turnを依頼した。
- **どう判断**: 日本人residual、26 row completeness、高低対称性、warning／refusal、normative／official-rate誤認防止、source／hash／private-path gateのscopeではBlocking／High／Medium／Lowすべて0件。review後にuserが見つけたnumerator selector消失は、固定metricのcorrectnessとは別のproduct-design regressionとしてrelease前TODOにする。
- **検証結果**: reviewer側でPython 116 test、web 56 test、typecheck、`verify:data`、32-file `verify:pages`をpass。public bundleとcompact bundleのSHA-256は`b0f950baa23aac85e44d644b4609ec0bd70d0567d307bfaf013377d85e4ee060`で一致した。
- **関連パス**: `docs/20260903_182500_japanese_nationality_comparison_independent_review.md`, `docs/20260903_082238_japanese_nationality_comparison_and_ui_audit.md`, `docs/workflow.md`, `README.md`, `README.ja.md`

## 2026-09-04 犯罪類型構成と認知−検挙同年差分を実装・独立review完了
- **何が**: user feedbackを受け、nationality perspective selectorを復旧してcompatibleな日本人分子がないviewでもexplicit refusalを残した。日本を含む26 category × 6犯罪類型の検挙人員／検挙件数構成をheatmap・100%積み上げ・階層clusterで表示し、全住民regional contextへ認知−検挙の符号付き同年差分件数／割合を追加した。compact exportはschema v5へ更新した。
- **どう判断**: 日本は類型ごとにもS15全人値−S08全外国人値の残差参考値とする。`凶悪犯`以外をproject独自に軽犯罪とは分類せず、Jensen–Shannon distance（base 2）＋average linkageのclusterは類似構成の探索順に限定する。同年差分は前年以前の認知事件を含み得る当年検挙flowとの差なので、strictな未解決件数／率とは呼ばず、negativeをclampせず、認知0の割合をrefuseする。
- **なぜ**: 高い／低い比率だけでなく、どの犯罪類型で構成されるかを全categoryで比較したいという要望と、認知件数に対する検挙の残差を知りたいという要望を、犯罪量・危険度・未解決cohortという誤読を作らず可視化するため。
- **検証結果**: offense productは156 cell（26 × 6）、日本totalは検挙人員181,362／検挙件数268,412。同年差分は62 row（60 calculated／2 refused）で、日本450,406／61.0572%、東京60,791／64.1580%、埼玉34,976／67.6950%。browserでcount modeのmap detailが同年差分率を`件`と表示するbugを発見し、RED test後に`%`へ修正した。Python 128 test、coverage 83.45%、web 68 test、branch coverage 84.14%、typecheck／lint／format／data hash／production build、desktop／390 px mobile確認をpass。fresh reviewerは構成比、日本残差、cluster順、差分62 row、selector、source/hashを独立再計算し、focused Python 13／web 49 testをpass、全severity 0、scope内open finding 0と判定した。
- **次**: userがpublicationを明示した場合だけreview済みcommitをpushし、GitHub Pages deployed URLを実地確認する。機能面の次trackは複数年backfillと、small-number volatility・category/schema driftを伴う時系列表示。
- **関連パス**: `config/offense_composition_contract.json`, `src/nationality_crime_atlas/offense_composition.py`, `src/nationality_crime_atlas/compact_export.py`, `data/processed/_offense_composition/20260903_222026_offense_composition/`, `output/compact_export/20260903_231549_compact_export/`, `web/public/data/dashboard_export.json`, `web/lib/dashboard.ts`, `web/components/crime-atlas-dashboard.tsx`, `docs/20260904_082028_offense_composition_and_same_year_gap_audit.md`, `docs/20260904_082803_offense_composition_and_same_year_gap_independent_review.md`

## 2026-09-04 一般読者向けの日本語案内とREADME導線を追加
- **何が**: userから、画面に`cohort`、`nationality-neutral`、`context`などの英語が混ざって読みにくく、サイトの目的やREADMEも見えないとの指摘を受けた。冒頭に目的・3つの見方・分からないこと・用語説明を追加し、ページ内メニュー、日本語README、数字の読み方へ接続した。出典名、注意、未算出理由、地図・犯罪種類表示も日本語へ改めた。
- **どう判断**: 単なる翻訳ではなく、数値を見る前に目的と解釈の境界を理解できる情報階層へ変更した。provenanceや内部warning codeは削除せず、取得hashは折りたたみ、内部codeはtitle属性へ残した。リンク先で同じ読みづらさが再発しないよう`README.ja.md`も自然な日本語へ全面改訂した。
- **なぜ**: このprojectの中心は数字を隠さず公正に比較することだが、目的と限界が先に読めなければ、正しい数値でも誤読を招くため。内部実装の語彙を一般読者へそのまま露出する必要はないため。
- **検証結果**: 旧画面で新要件7件のREDを確認後、dashboard test 10件、web全体69件をGREEN化。branch coverage 84.34%、typecheck／lint／format／data hash検証をpass。production buildはsandbox内socket制限だけで失敗し、許可環境で同一buildを再実行してstatic 1 route成功。Chromeの1440 px／500 px幅で冒頭の情報階層を目視確認した。
- **次**: publicationが明示された場合のみpushし、GitHub Pages上でリンクとresponsive表示を再確認する。機能面は複数年backfill／時系列表示が次track。
- **関連パス**: `web/components/crime-atlas-dashboard.tsx`, `web/components/prefecture-map.tsx`, `web/lib/dashboard.ts`, `web/app/globals.css`, `README.md`, `README.ja.md`, `docs/workflow.md`, `docs/brief.md`, `docs/20260904_214807_plain_japanese_information_architecture_audit.md`

## 2026-09-04 サイトの目的文を「情報の分散→収集・可視化→判断範囲」の順へ改訂
- **何が**: userから、冒頭の「国籍についての印象や決めつけではなく」という書き出しでは目的が分かりにくいとの指摘を受けた。公的情報が複数機関・資料に分散していて整理が容易でないという背景、収集・整理・可視化する目的、価値判断を行わない範囲の3段落へ置き換えた。
- **どう判断**: 開発動機ではなく、このサイトが解く情報アクセス上の問題と実際に行う処理を先に示す。責任回避的な「範囲外」ではなく、「良し悪しの評価・原因の推定・集団や個人への価値判断は行わない」と具体的に記載した。
- **なぜ**: 実際のsource discoveryと定義整理には相当な作業が必要であり、分散した公表情報を一か所で辿れるようにすること自体が、このprojectの明確な提供価値だから。
- **検証結果**: 新しい3要素を要求し旧文言を禁止するcomponent testでREDを確認後、表示を実装してfocused 10 testをGREEN化した。README英語版・日本語版にも同じ背景・目的・判断範囲を反映した。
- **関連パス**: `web/components/crime-atlas-dashboard.tsx`, `web/tests/dashboard.test.tsx`, `README.md`, `README.ja.md`, `docs/20260904_222409_README.md`, `docs/20260904_222409_README.ja.md`

## 2026-09-04 目的文改訂の全品質 gate と表示確認
- **何が**: 冒頭3段落への改訂後に、frontend全体と実際の表示を再検証した。
- **検証結果**: 69 testsとtypecheck／lint／format／public data hash検証がpass。statement coverage 90.63%、branch coverage 84.34%。production buildはsandboxのlocalhost socket制限でのみ失敗し、同一commandを許可環境で再実行して1 static routeのprerender成功を確認した。Chromeの1440 px幅と500 px幅で、3段落の順序・折り返し・後続cardとの間隔に問題がないことを目視確認した。
- **関連パス**: `web/components/crime-atlas-dashboard.tsx`, `web/app/globals.css`, `web/tests/dashboard.test.tsx`

## 2026-09-05 公開前のcommit identity修正とCI timeout対応
- **何が**: 初回publication時にcommitのAuthor／Committerが端末由来identityになっていることが判明した。GitHub側のrepositoryをいったん削除し、localの46 commitをGitHub accountのprivacy identityへ書き換えた。削除前のActionsではpublication bundle testがCIの既定5秒を超えた。
- **どう判断**: 個人mailはcommitに使わず、GitHub noreply identityをrepository local configに固定した。CI timeoutは全testではなく、1.4 MBのpublication bundleを2回同期検証する対象testだけ15秒とした。
- **なぜ**: 公開履歴から端末情報と個人mailを排除しつつ、commitをGitHub accountへ帰属させるため。I/O-heavy testの正常処理とCIの性能ばらつきを混同しないため。
- **検証結果**: rewrite前後で46個のtree、commit日時、messageがすべて一致。到達可能なidentity nameはGitHub loginのみ、email欄はGitHub noreplyのみで、commit messageと全世代のfile内容に端末由来identityの残存はない。source file内のemail形式はCC0地図作者のprovenanceのみ。69 tests、coverage、typecheck／lint／format／data hash／map determinism、Pages用production build、32-file artifact検証がpass。
- **関連パス**: `web/tests/publication-data.test.ts`, `web/assets/maps/LICENSE.cc0`, `web/assets/maps/deformed-japan-prefecture-map.svg`, `agent_logs/20260905_000854_pre_identity_rewrite/pre_identity_rewrite.bundle`

## 2026-09-05 公開履歴をclean root commitへ限定
- **何が**: 再publication前のauditで、現在の画面・test／docsに以前のpublication target URLが残っていることを発見し、現在のGitHub accountとPages URLへ統一した。
- **どう判断**: multi-commit historyをそのまま公開すると過去treeから不要なpublication metadataを辿れるため、公開branchはprivacy audit後の現在treeだ1個のclean root commitから開始する。完全な開発履歴はgitignore済みlocal bundleだけに保存する。
- **なぜ**: 公開履歴の再現性よりprivacyとpublication provenanceの明確さを優先するというuserの意図に沿うため。
- **検証結果**: 正しい2つのdocumentation linkを要求するtestでREDを確認後、画面・Pages fixture・publication config／docsを更新し、影響す27 testsをGREEN化した。README英語版・日本語版とworkflowの現在地もpublication工程へ更新した。
- **関連パス**: `web/components/crime-atlas-dashboard.tsx`, `web/tests/dashboard.test.tsx`, `web/tests/pages-artifact.test.ts`, `web/tests/publication-config.test.ts`, `README.md`, `README.ja.md`, `docs/workflow.md`

## 2026-09-05 clean checkoutでのVite hosting config欠落を修正
- **何が**: 再作成後のGitHub Actionsでfrontend testはpassしたが、typecheckがVite hosting configを解決できず失敗した。localにはfileがあったが、directory全体のignoreによりclean checkoutに含まれていなかった。
- **どう判断**: Viteがdirect importする`hosting.json`だけを追跡し、同じdirectoryの他fileはignoreする。追跡する値は`d1: null`と`r2: null`だけで、secretやdeployment IDは含めない。
- **なぜ**: localに偶然存在するignored fileへbuildが依存すると、GitHub Actionsや新規cloneで再現できないため。
- **検証結果**: GitHub Actionsのtypecheck failureをREDとし、対象fileのtracked化とlocal typecheckのGREENを確認。さらに`git archive HEAD`から作ったclean checkout相当環境でtypecheckを実行し、passを確認した。
- **関連パス**: `web/.gitignore`, `web/.openai/hosting.json`, `web/vite.config.ts`, `.github/workflows/pages.yml`

## 2026-09-05 privacy-clean repository再作成とGitHub Pages公開完了
- **何が**: 公開repositoryをclean root commitから再作成し、GitHub Pagesをworkflow方式で有効化した。最初のworkflowはPages有効化とのraceで停止し、再実行ではclean checkoutにだけ現れるhosting config欠落を検出・修正した。修正後のGitHub Actions run `33890484400`はbuild／deployとも成功した。
- **どう判断**: commitのAuthor／CommitterはGitHub accountのprivacy identityだけに限定し、公開履歴には現在の成果物だけを置く。Viteに必要な非secretのbinding形だけを追跡する。さらに、pinned Pages actionの公式input定義を確認し、未対応の`include-hidden-files`指定をRED／GREEN test付きで削除した。CC0 map作者の連絡先はlicense provenanceとして保持する。
- **なぜ**: repository履歴、clean checkout、CI artifact、live siteのすべてで個人情報を露出せず、別環境でも同じ公開物を再現できる状態にするため。unsupported inputの警告を放置すると、将来のaction変更時に本当の異常を見落としやすいため。
- **検証結果**: GitHub上でpublic設定、clean root、GitHub accountだけのcommit帰属を確認した。公開対象の禁止private markerは0件。GitHub Actionsでdata verification、map determinism、69 web tests、typecheck、lint、format、production build、Pages artifact検証、deployがpassした。公開URLはHTTP 200で、Chrome表示、正しいdocumentation link、公開data SHA-256 `102e2f6d589675a4fb45eac239212ff3f160048f5c0479bea62416da67ecb002`の一致を確認した。unsupported input削除はfocused test 10件でGREENを確認し、本entryを含む最終runでも再検証する。
- **関連パス**: `.github/workflows/pages.yml`, `web/.openai/hosting.json`, `web/tests/publication-config.test.ts`, `README.md`, `README.ja.md`, `docs/workflow.md`

## 2026-09-05 local Pages artifact検証のbase path指定漏れ
- **何が**: GitHub Pagesと同条件のproduction build後、最初のlocal artifact整形がroot直下の`_next`欠落として停止した。
- **どう判断／なぜ**: buildは`/nationality-crime-atlas/_next`を正しく生成しており、実装やartifactの破損ではなかった。整形commandだけにCIと同じ`NEXT_PUBLIC_BASE_PATH`を渡していなかったため、環境条件を揃えて再実行した。
- **検証結果**: 32 files、base path `/nationality-crime-atlas`、dashboard SHA-256 `102e2f6d589675a4fb45eac239212ff3f160048f5c0479bea62416da67ecb002`を含むPages artifact検証がpassした。
- **関連パス**: `web/scripts/prepare-pages-artifact.mjs`, `web/scripts/verify-pages-artifact.mjs`, `.github/workflows/pages.yml`
