'use client';

import { useMemo, useState } from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ExternalLink,
  Info,
  Scale,
  ShieldAlert,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from 'recharts';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { PrefectureMap } from '@/components/prefecture-map';
import {
  buildClearancePopulationTrendViewModel,
  buildClearanceShareTrendViewModel,
  buildOffenseCompositionViewModel,
  buildSelectableNationalityViewModel,
  buildRegionalViewModel,
  CONTEXT_METRICS,
  type ClearanceShareMetric,
  type ClearancePopulationTrendViewModel,
  type ClearanceShareTrendViewModel,
  type ContextMetricId,
  type DashboardData,
  formatDashboardValue,
  type NationalityComparisonViewModel,
  NATIONALITY_CASES_COMPARISON_ID,
  NATIONALITY_PERSPECTIVES,
  type NationalityPerspectiveId,
  type OffenseCompositionEntity,
  type OffenseCompositionMetric,
  type OffenseCompositionOrder,
  type OffenseCompositionViewModel,
  type RegionalDatum,
  type RegionalViewModel,
  type ValueMode,
} from '@/lib/dashboard';

const chartConfig = {
  value: {
    label: '表示値',
    color: 'var(--chart-1)',
  },
} satisfies ChartConfig;

const clearanceShareChartConfig = {
  allForeignShare: {
    label: '外国人全体',
    color: 'var(--chart-1)',
  },
  visitingForeignShare: {
    label: '来日外国人',
    color: 'var(--chart-2)',
  },
  allForeignMinusVisitingShare: {
    label: '外国人全体−来日外国人（差分）',
    color: 'var(--chart-3)',
  },
} satisfies ChartConfig;

const japaneseClearanceShareChartConfig = {
  japaneseEtcResidualShare: {
    label: '日本人等（残差）',
    color: 'var(--chart-4)',
  },
} satisfies ChartConfig;

const clearancePopulationChartConfig = {
  referenceRatio: {
    label: '人口1,000人当たり',
    color: 'var(--chart-1)',
  },
  populationValue: {
    label: '参照人口',
    color: 'var(--chart-2)',
  },
} satisfies ChartConfig;

const PROJECT_README_URL =
  'https://github.com/hs-hg-2026/nationality-crime-atlas/blob/main/README.ja.md';
const INTERPRETATION_NOTE_URL =
  'https://github.com/hs-hg-2026/nationality-crime-atlas/blob/main/docs/interpretation_note.md';
const GITHUB_ISSUES_URL =
  'https://github.com/hs-hg-2026/nationality-crime-atlas/issues';
const GITHUB_NEW_ISSUE_URL = `${GITHUB_ISSUES_URL}/new/choose`;

const sourceDisplay: Record<
  string,
  { dataset: string; publisher: string; period: string }
> = {
  S02: {
    dataset: '来日外国人の地域別・検挙件数と検挙人員',
    publisher: '警察庁',
    period: '2025年（2024年との比較を含む）',
  },
  S08: {
    dataset: '外国人の国籍等別・検挙件数と検挙人員',
    publisher: '警察庁',
    period: '2015–2024年（2024年の詳細内訳を含む）',
  },
  S09: {
    dataset: '来日外国人の国籍等別・検挙件数と検挙人員',
    publisher: '警察庁',
    period: '2015–2024年（2024年の詳細内訳を含む）',
  },
  S14: {
    dataset: '在留外国人統計：国籍・地域別の在留外国人数',
    publisher: '出入国在留管理庁',
    period: '2025年12月31日時点',
  },
  S14_2024_12: {
    dataset: '在留外国人統計：国籍・地域別の在留外国人数',
    publisher: '出入国在留管理庁',
    period: '2024年12月31日時点',
  },
  S15: {
    dataset: '都道府県等別の刑法犯認知件数・検挙件数・検挙人員',
    publisher: '警察庁',
    period: '2015–2024年（2024年の都道府県別値を含む）',
  },
  S16: {
    dataset: '都道府県別の総人口',
    publisher: '警察庁（人口の原資料：総務省統計局）',
    period: '2024年10月1日時点',
  },
  S17: {
    dataset: '都道府県別の総人口と日本人人口',
    publisher: '総務省統計局',
    period: '2024年10月1日時点',
  },
};

function sourceDisplayFor(source: RegionalViewModel['sources'][number]) {
  const exact = sourceDisplay[source.id];
  if (exact) return exact;

  const annualJapanesePopulation = /^S17_(\d{4})$/.exec(source.id);
  if (annualJapanesePopulation) {
    return {
      dataset: '都道府県別の総人口と日本人人口',
      publisher: '総務省統計局',
      period: `${annualJapanesePopulation[1]}年10月1日時点`,
    };
  }
  if (source.id === 'S18') {
    return {
      dataset: '都道府県別の総人口と日本人人口（国勢調査間補間補正）',
      publisher: '総務省統計局',
      period: '2015–2020年10月1日時点',
    };
  }

  const annualForeignPopulation = /^S19_(\d{4})$/.exec(source.id);
  if (annualForeignPopulation) {
    return {
      dataset: '在留外国人統計：国籍・地域別の在留外国人数',
      publisher: '出入国在留管理庁',
      period: `${annualForeignPopulation[1]}年12月31日時点`,
    };
  }

  return {
    dataset: source.dataset,
    publisher: source.publisher,
    period: source.sourcePeriod,
  };
}

const refusalLabels: Record<string, string> = {
  geography_not_exact_prefecture_or_national:
    '都道府県または全国と一致する地域区分ではない',
  individual_nationality_prefecture_numerator_unpublished:
    '国籍等別かつ都道府県別の犯罪件数・人員が公表されていない',
  japanese_prefecture_numerator_unpublished:
    '日本国籍かつ都道府県別の犯罪件数・人員が公表されていない',
  crosswalk_not_exact: '犯罪統計と人口統計の国籍区分が一致しない',
  no_canonical_denominator_components: '対応する人口区分を確定できない',
  compatible_japanese_numerator_not_available:
    '同じ条件の日本国籍の犯罪件数・人員がない（推計しない）',
};

const interpretationLabels: Record<string, string> = {
  aggregate_nationality_numerator: '複数の国籍等をまとめた犯罪統計',
  all_foreign_vs_resident_population_mismatch:
    '犯罪統計の「全外国人」と在留外国人数は対象範囲が同じとは限らない',
  all_persons_minus_all_foreign_scope_assumption:
    '日本の値は全住民値から全外国人値を差し引いた参考値',
  annual_flow_vs_point_in_time_population:
    '1年間の犯罪件数と、特定日時点の人口を組み合わせている',
  annual_flow_vs_point_in_time_stock:
    '1年間の犯罪件数と、特定日時点の人口を組み合わせている',
  canonical_target_incomplete: '比較に必要な対応項目が一部そろわない',
  case_count_not_person_count: '事件の件数であり、人数ではない',
  clearance_can_include_prior_year_recognitions:
    '検挙件数には前年以前に認知された事件が含まれることがある',
  cleared_person_records_not_unique_risk_population:
    '検挙人員は、犯罪をする可能性を表す個人単位の追跡値ではない',
  criminal_code_scope_only: '刑法犯だけを対象としている',
  denominator_reference_dates_differ_across_rows:
    '人口の基準日が行によって異なる',
  japanese_numerator_derived_by_residual_subtraction:
    '日本の犯罪件数・人員は差し引きによる参考値',
  japanese_numerator_scope_not_available_for_selected_perspective:
    '選択中の条件に対応する日本の犯罪件数・人員がない',
  japanese_population_rounded_to_nearest_1000:
    '日本人人口は千人単位に丸められた公表値',
  japanese_values_derived_by_residual_subtraction:
    '日本の値は差し引きによる参考値',
  nationality_grouping_mismatch: '犯罪統計と人口統計の国籍区分が一致しない',
  no_equivalent_total_population_geography: '同じ地域区分の総人口がない',
  no_prefecture_nationality_numerator:
    '国籍等別かつ都道府県別の犯罪件数・人員がない',
  non_prefecture_published_geography: '公表地域が都道府県単位ではない',
  not_unresolved_case_cohort: '同じ事件を認知から検挙まで追跡した数字ではない',
  numerator_not_published: '犯罪件数・人員が公表されていない',
  numerator_residency_scope_not_established:
    '犯罪件数に数えられた人の居住地は確認できない',
  police_reporting_area_unresolved:
    '警察統計の地域が発生地・居住地のどちらか確認できない',
  police_reporting_area_vs_population_estimate_prefecture:
    '警察統計の地域と人口推計の都道府県を組み合わせている',
  police_reporting_area_vs_registered_residence:
    '警察統計の地域と在留外国人の届出住所は同じ定義ではない',
  primary_baseline_is_all_residents:
    '地域比較の基準人口は、日本人と外国人を合わせた全住民',
  published_nationality_is_sum_of_subcategories:
    '公表された複数の内訳を合計した国籍等区分',
  published_subcategories_aggregated_to_nationality:
    '公表された内訳を国籍等ごとに合計している',
  same_year_flow_difference:
    '同じ年の認知件数と検挙件数の差であり、事件を追跡した値ではない',
  small_denominator_base: '人口が少ないため、参考比率が大きく変動しやすい',
  sparse_entity_total_cleared_cases:
    '検挙件数が少ないため、構成比が大きく変動しやすい',
  sparse_entity_total_cleared_persons:
    '検挙人員が少ないため、構成比が大きく変動しやすい',
  sparse_numerator_count: '犯罪件数・人員が少なく、値が変動しやすい',
  total_population_rounded_to_nearest_1000:
    '総人口は千人単位に丸められた公表値',
  visitor_vs_resident_population_mismatch:
    '「来日外国人」の犯罪統計と在留外国人数は対象範囲が一致しない',
  all_foreign_scope_not_resident_foreigner_population:
    '「外国人全体」は在留外国人人口と同じ範囲ではない',
  denominator_includes_japanese_and_others:
    '分母は日本人等を含む全国の検挙総数',
  share_of_clearance_counts_not_population_rate:
    '検挙全体の構成比であり、人口当たりの犯罪率ではない',
  visiting_foreign_includes_nonresidents:
    '「来日外国人」には短期滞在者や不法滞在者等が含まれ得る',
};

function interpretationLabel(code: string): string {
  return interpretationLabels[code] ?? refusalLabels[code] ?? code;
}

function InterpretationNote({ code }: { code: string }) {
  return (
    <span className="interpretation-note" title={`内部コード: ${code}`}>
      {interpretationLabel(code)}
    </span>
  );
}

function regionalFormulaLabel(view: RegionalViewModel): string {
  if (view.isSameYearGap) {
    return '（刑法犯認知件数 − 刑法犯検挙件数）÷ 刑法犯認知件数';
  }
  if (view.metricId === 'all_resident_recognized_cases') {
    return '刑法犯認知件数 ÷ 人口';
  }
  if (view.metricId === 'all_resident_cleared_cases') {
    return '刑法犯検挙件数 ÷ 人口';
  }
  return '刑法犯検挙人員 ÷ 人口';
}

type OffenseDisplayMode = 'heatmap' | 'stacked';

function formatOffenseShare(share: number): string {
  return `${(share * 100).toLocaleString('ja-JP', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

function offenseHeatmapColor(color: string, share: number | null): string {
  if (share === null) return 'var(--muted)';
  const strength = Math.round(10 + Math.min(1, share) * 55);
  return `color-mix(in srgb, ${color} ${strength}%, white)`;
}

function SourceList({ sources }: { sources: RegionalViewModel['sources'] }) {
  return (
    <div className="source-list">
      {sources.map((source) => {
        const display = sourceDisplayFor(source);
        return (
          <article key={source.id}>
            <div>
              <Badge variant="outline">{source.id}</Badge>
              <span>資料内の表：{source.sourceTable}</span>
            </div>
            <h3>{display.dataset}</h3>
            <p>{display.publisher}</p>
            <p>{display.period}</p>
            <div className="source-actions">
              <a
                href={source.landingUrl}
                target="_blank"
                rel="noreferrer"
                aria-label={`${source.id} 公表ページ`}
              >
                公表ページ <ExternalLink aria-hidden="true" />
              </a>
              <a
                href={source.downloadUrl}
                target="_blank"
                rel="noreferrer"
                aria-label={`${source.id} 元データ`}
              >
                元データ <ExternalLink aria-hidden="true" />
              </a>
            </div>
            <details className="source-record">
              <summary>取得記録を確認</summary>
              <p>取得日時：{source.retrievedAt}</p>
              <code className="source-hash">SHA-256 {source.sha256}</code>
            </details>
          </article>
        );
      })}
    </div>
  );
}

function ComparisonCard({
  datum,
  mode,
  unitLabel,
  rawCountLabel,
  denominatorLabel,
  testId,
}: {
  datum: RegionalDatum;
  mode: ValueMode;
  unitLabel: string;
  rawCountLabel: string;
  denominatorLabel: string;
  testId: string;
}) {
  return (
    <Card className="comparison-card" data-testid={testId}>
      <CardHeader>
        <CardDescription>{datum.name}</CardDescription>
        <CardTitle className="comparison-value">
          {formatDashboardValue(datum.value, mode)}
          <span>{unitLabel}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="comparison-meta">
        <span>
          {rawCountLabel} {datum.rawCount.toLocaleString('ja-JP')}
        </span>
        <span>
          {denominatorLabel} {datum.denominatorValue.toLocaleString('ja-JP')}
        </span>
      </CardContent>
    </Card>
  );
}

function NationalityOrderedPlot({
  view,
}: {
  view: NationalityComparisonViewModel;
}) {
  const maximum = Math.max(
    ...view.orderedRows.map((row) => row.referenceRatio ?? 0),
    0,
  );
  return (
    <Card
      className="nationality-order-card"
      data-testid="nationality-ordered-plot"
    >
      <CardHeader>
        <CardTitle>全{view.orderedRows.length}区分の参考比率</CardTitle>
        <CardDescription>
          参考比率の高い順に全区分を表示。日本の参考値は別色にし、未算出の行も残します。
        </CardDescription>
      </CardHeader>
      <CardContent className="nationality-order-list">
        {view.orderedRows.map((row, index) => {
          const width =
            row.referenceRatio === null || maximum === 0
              ? 0
              : (row.referenceRatio / maximum) * 100;
          return (
            <div
              className={`nationality-order-row${
                row.isJapaneseReference ? ' is-japanese-reference' : ''
              }`}
              data-testid="nationality-order-row"
              key={row.id}
            >
              <div className="nationality-order-label">
                <span className="nationality-order-rank">
                  {row.referenceRatio === null ? '—' : index + 1}
                </span>
                <span
                  data-testid={
                    row.isJapaneseReference
                      ? 'nationality-order-japanese'
                      : undefined
                  }
                >
                  {row.name}
                </span>
              </div>
              <div className="nationality-order-track" aria-hidden="true">
                {row.referenceRatio === null ? null : (
                  <span
                    className="nationality-order-bar"
                    style={{ width: `${width}%` }}
                  />
                )}
              </div>
              <strong className="nationality-order-value">
                {row.referenceRatio === null ? (
                  <span className="not-calculated">未算出</span>
                ) : (
                  <>
                    {formatDashboardValue(row.referenceRatio, 'ratio')}
                    <small> / 1,000人</small>
                  </>
                )}
              </strong>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function formatClearanceShare(value: number): string {
  return `${value.toLocaleString('ja-JP', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

function ClearanceShareTrend({
  view,
  metric,
  onMetricChange,
}: {
  view: ClearanceShareTrendViewModel;
  metric: ClearanceShareMetric;
  onMetricChange: (metric: ClearanceShareMetric) => void;
}) {
  return (
    <section
      id="clearance-share"
      className="clearance-share-section"
      aria-labelledby="clearance-share-heading"
      data-testid="clearance-share-trend-section"
    >
      <div className="section-heading-row">
        <div>
          <p className="section-kicker">全国の時系列</p>
          <h2 id="clearance-share-heading">検挙全体に占める区分別の割合</h2>
          <p className="intro-copy">
            日本人等を含む全国の刑法犯検挙総数を、日本人等の残差と外国人区分に分けて示します。値の幅が大きく異なるため、別々のy軸で表示します。
          </p>
        </div>
        <Badge variant="outline">
          {view.years[0]}–{view.years.at(-1)}年
        </Badge>
      </div>

      <div className="clearance-share-controls">
        <fieldset className="control-field">
          <legend>分子・分母の単位</legend>
          <div className="mode-buttons">
            <Button
              type="button"
              variant={metric === 'cleared_cases' ? 'default' : 'outline'}
              aria-pressed={metric === 'cleared_cases'}
              onClick={() => onMetricChange('cleared_cases')}
            >
              検挙件数
            </Button>
            <Button
              type="button"
              variant={metric === 'cleared_persons' ? 'default' : 'outline'}
              aria-pressed={metric === 'cleared_persons'}
              onClick={() => onMetricChange('cleared_persons')}
            >
              検挙人員
            </Button>
          </div>
        </fieldset>
        <div className="clearance-share-legend" aria-label="折れ線の凡例">
          <span className="all-foreign">外国人全体</span>
          <span className="visiting-foreign">来日外国人</span>
          <span className="foreign-residual">
            外国人全体−来日外国人（差分）
          </span>
        </div>
      </div>

      <Alert className="clearance-share-alert">
        <Info aria-hidden="true" />
        <AlertTitle>人口当たりの犯罪率ではありません</AlertTitle>
        <AlertDescription>
          {view.uiCaveat}
          <span className="method-contract">
            日本人等は全国総数から外国人全体を引いた残差で、日本人について直接公表された値ではありません。
          </span>
          <span className="method-contract">
            算式{' '}
            <code>
              外国人区分の{view.metricLabel} ÷ 全国の{view.metricLabel} × 100
            </code>
          </span>
        </AlertDescription>
      </Alert>

      <div className="clearance-share-grid">
        <div className="clearance-share-panel-grid">
          <Card className="clearance-share-chart-card">
            <CardHeader>
              <CardTitle>外国人3区分の{view.metricLabel}構成比</CardTitle>
              <CardDescription>
                差分には定着居住者だけでなく、在日米軍関係者や在留資格不明者も含まれ得るため、普段から住む外国人だけを表す値ではありません。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={clearanceShareChartConfig}
                className="clearance-share-chart"
                data-testid="clearance-share-chart"
                initialDimension={{ width: 760, height: 360 }}
              >
                <LineChart
                  accessibilityLayer
                  data={view.points}
                  margin={{ left: 4, right: 20, top: 12, bottom: 4 }}
                >
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis
                    dataKey="year"
                    axisLine={false}
                    tickLine={false}
                    tickMargin={8}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tickMargin={8}
                    tickFormatter={(value) => `${Number(value)}%`}
                    width={44}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        labelFormatter={(_, payload) =>
                          payload[0]?.payload?.year
                            ? `${payload[0].payload.year}年`
                            : ''
                        }
                        formatter={(value, name) => (
                          <>
                            <span>
                              {name === 'allForeignShare'
                                ? '外国人全体'
                                : name === 'visitingForeignShare'
                                  ? '来日外国人'
                                  : '外国人全体−来日外国人（差分）'}
                            </span>
                            <strong>
                              {formatClearanceShare(Number(value))}
                            </strong>
                          </>
                        )}
                      />
                    }
                  />
                  <Line
                    dataKey="allForeignShare"
                    name="allForeignShare"
                    type="monotone"
                    stroke="var(--color-allForeignShare)"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />
                  <Line
                    dataKey="visitingForeignShare"
                    name="visitingForeignShare"
                    type="monotone"
                    stroke="var(--color-visitingForeignShare)"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />
                  <Line
                    dataKey="allForeignMinusVisitingShare"
                    name="allForeignMinusVisitingShare"
                    type="monotone"
                    stroke="var(--color-allForeignMinusVisitingShare)"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>

          <Card className="clearance-share-chart-card">
            <CardHeader>
              <CardTitle>日本人等（残差）の{view.metricLabel}構成比</CardTitle>
              <CardDescription>
                <code>100% − 外国人全体の割合</code>
                。変化を読めるようにy軸は90–100%とし、外国人区分とは分けています。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={japaneseClearanceShareChartConfig}
                className="clearance-share-chart"
                data-testid="japanese-clearance-share-chart"
                initialDimension={{ width: 760, height: 360 }}
              >
                <LineChart
                  accessibilityLayer
                  data={view.points}
                  margin={{ left: 4, right: 20, top: 12, bottom: 4 }}
                >
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis
                    dataKey="year"
                    axisLine={false}
                    tickLine={false}
                    tickMargin={8}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tickMargin={8}
                    domain={[90, 100]}
                    tickFormatter={(value) => `${Number(value)}%`}
                    width={44}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        labelFormatter={(_, payload) =>
                          payload[0]?.payload?.year
                            ? `${payload[0].payload.year}年`
                            : ''
                        }
                        formatter={(value) => (
                          <>
                            <span>日本人等（残差）</span>
                            <strong>
                              {formatClearanceShare(Number(value))}
                            </strong>
                          </>
                        )}
                      />
                    }
                  />
                  <Line
                    dataKey="japaneseEtcResidualShare"
                    name="japaneseEtcResidualShare"
                    type="monotone"
                    stroke="var(--color-japaneseEtcResidualShare)"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>
        </div>

        <Card className="clearance-share-table-card">
          <CardHeader>
            <CardTitle>年ごとの実数と割合</CardTitle>
            <CardDescription>
              丸める前の公表値からこのサイトで単純に割り算します。
            </CardDescription>
          </CardHeader>
          <CardContent className="table-scroll">
            <table
              className="nationality-table clearance-share-table"
              data-testid="clearance-share-table"
            >
              <caption className="sr-only">
                全国の{view.metricLabel}に占める外国人区分の割合
              </caption>
              <thead>
                <tr>
                  <th scope="col">年</th>
                  <th scope="col">全国総数</th>
                  <th scope="col">日本人等（残差）</th>
                  <th scope="col">外国人全体</th>
                  <th scope="col">来日外国人</th>
                  <th scope="col">外国人全体−来日外国人（差分）</th>
                </tr>
              </thead>
              <tbody>
                {[...view.points].reverse().map((point) => (
                  <tr key={point.year}>
                    <th scope="row">{point.year}</th>
                    <td>
                      {point.allPersonsTotal.toLocaleString('ja-JP')}
                      <small>{view.unitLabel}</small>
                    </td>
                    <td>
                      {point.japaneseEtcResidualCount.toLocaleString('ja-JP')}
                      <small>{view.unitLabel}</small>{' '}
                      <strong>
                        {formatClearanceShare(point.japaneseEtcResidualShare)}
                      </strong>
                    </td>
                    <td>
                      {point.allForeignCount.toLocaleString('ja-JP')}
                      <small>{view.unitLabel}</small>{' '}
                      <strong>
                        {formatClearanceShare(point.allForeignShare)}
                      </strong>
                    </td>
                    <td>
                      {point.visitingForeignCount.toLocaleString('ja-JP')}
                      <small>{view.unitLabel}</small>{' '}
                      <strong>
                        {formatClearanceShare(point.visitingForeignShare)}
                      </strong>
                    </td>
                    <td>
                      {point.allForeignMinusVisitingCount.toLocaleString(
                        'ja-JP',
                      )}
                      <small>{view.unitLabel}</small>{' '}
                      <strong>
                        {formatClearanceShare(
                          point.allForeignMinusVisitingShare,
                        )}
                      </strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      <Card className="clearance-share-sources">
        <CardHeader>
          <BookOpen aria-hidden="true" />
          <CardTitle>この時系列の出典</CardTitle>
          <CardDescription>
            外国人全体、来日外国人、その差分、日本人等の残差、全国総数を、元の公表値まで辿れます。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SourceList sources={view.sources} />
        </CardContent>
      </Card>
    </section>
  );
}

function formatPopulationReferenceRatio(value: number | null): string {
  if (value === null) return '未算出';
  return value.toLocaleString('ja-JP', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatCompactPopulation(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(2)}億`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(1)}万`;
  return value.toLocaleString('ja-JP');
}

function ClearancePopulationPanel({
  panel,
  view,
  testId,
}: {
  panel: ClearancePopulationTrendViewModel['japanese'];
  view: ClearancePopulationTrendViewModel;
  testId: string;
}) {
  const isJapanese = panel.group === 'japanese_etc_residual';
  return (
    <Card className="clearance-population-panel" data-testid={testId}>
      <CardHeader>
        <CardTitle>{panel.label}</CardTitle>
        <CardDescription>
          {isJapanese
            ? '分子は日本人の直接公表値ではなく、全国総数から外国人全体を引いた残差です。分母は10月1日の日本人人口です。'
            : '分子は犯罪統計の「外国人全体」、分母は12月31日の在留外国人数で、対象範囲は一致しません。'}
        </CardDescription>
      </CardHeader>
      <CardContent className="clearance-population-panel-content">
        <div className="clearance-population-chart-block">
          <h3>{view.metricLabel}の人口1,000人当たり参考比率</h3>
          <ChartContainer
            config={clearancePopulationChartConfig}
            className="clearance-population-chart"
            data-testid="clearance-population-rate-chart"
            aria-label={`${panel.label}の${view.metricLabel}、人口1,000人当たり参考比率。y軸は${view.referenceRatioAxis.domain[0].toFixed(1)}から${view.referenceRatioAxis.domain[1].toFixed(1)}、目盛り間隔は${view.referenceRatioAxis.tickInterval.toFixed(1)}。`}
            initialDimension={{ width: 620, height: 260 }}
          >
            <LineChart
              accessibilityLayer
              data={panel.points}
              margin={{ left: 4, right: 18, top: 12, bottom: 4 }}
            >
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="year"
                axisLine={false}
                tickLine={false}
                tickMargin={8}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tickMargin={8}
                domain={view.referenceRatioAxis.domain}
                ticks={view.referenceRatioAxis.ticks}
                tickFormatter={(value) => Number(value).toFixed(1)}
                width={42}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, payload) =>
                      payload[0]?.payload?.year
                        ? `${payload[0].payload.year}年`
                        : ''
                    }
                    formatter={(value) => (
                      <>
                        <span>人口1,000人当たり</span>
                        <strong>
                          {formatPopulationReferenceRatio(Number(value))}
                        </strong>
                      </>
                    )}
                  />
                }
              />
              <Line
                dataKey="referenceRatio"
                name="referenceRatio"
                type="monotone"
                stroke="var(--color-referenceRatio)"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                connectNulls={false}
              />
            </LineChart>
          </ChartContainer>
        </div>

        <div className="clearance-population-chart-block">
          <h3>分母に使った参照人口</h3>
          <ChartContainer
            config={clearancePopulationChartConfig}
            className="clearance-population-chart"
            data-testid="clearance-population-count-chart"
            initialDimension={{ width: 620, height: 230 }}
          >
            <LineChart
              accessibilityLayer
              data={panel.points}
              margin={{ left: 4, right: 18, top: 12, bottom: 4 }}
            >
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="year"
                axisLine={false}
                tickLine={false}
                tickMargin={8}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tickMargin={8}
                tickFormatter={(value) =>
                  formatCompactPopulation(Number(value))
                }
                width={52}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, payload) =>
                      payload[0]?.payload?.year
                        ? `${payload[0].payload.year}年`
                        : ''
                    }
                    formatter={(value) => (
                      <>
                        <span>参照人口</span>
                        <strong>
                          {Number(value).toLocaleString('ja-JP')}人
                        </strong>
                      </>
                    )}
                  />
                }
              />
              <Line
                dataKey="populationValue"
                name="populationValue"
                type="monotone"
                stroke="var(--color-populationValue)"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                connectNulls={false}
              />
            </LineChart>
          </ChartContainer>
        </div>

        <div className="table-scroll">
          <table
            className="clearance-population-table"
            data-testid={`${panel.group === 'japanese_etc_residual' ? 'japanese' : 'foreign'}-clearance-population-table`}
          >
            <caption className="sr-only">
              {panel.label}の{view.metricLabel}
              と参照人口、人口1,000人当たり参考比率
            </caption>
            <thead>
              <tr>
                <th scope="col">年</th>
                <th scope="col">{view.metricLabel}</th>
                <th scope="col">参照人口</th>
                <th scope="col">参考比率</th>
              </tr>
            </thead>
            <tbody>
              {[...panel.points].reverse().map((point) => (
                <tr key={point.year}>
                  <th scope="row">{point.year}</th>
                  <td>
                    {point.numeratorValue.toLocaleString('ja-JP')}
                    <small>{view.unitLabel}</small>
                  </td>
                  <td>
                    {point.populationValue === null
                      ? '分母未登録'
                      : point.populationValue.toLocaleString('ja-JP')}
                    {point.populationValue !== null && <small>人</small>}
                    {point.populationReferenceDate && (
                      <small>{point.populationReferenceDate}時点</small>
                    )}
                  </td>
                  <td>
                    <strong>
                      {formatPopulationReferenceRatio(point.referenceRatio)}
                    </strong>
                    {point.referenceRatio !== null && (
                      <small>人口1,000人当たり</small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function ClearancePopulationTrend({
  view,
  metric,
  onMetricChange,
}: {
  view: ClearancePopulationTrendViewModel;
  metric: ClearanceShareMetric;
  onMetricChange: (metric: ClearanceShareMetric) => void;
}) {
  return (
    <section
      id="clearance-population"
      className="clearance-population-section"
      aria-labelledby="clearance-population-heading"
      data-testid="clearance-population-trend-section"
    >
      <div className="section-heading-row">
        <div>
          <p className="section-kicker">人口と検挙の時系列</p>
          <h2 id="clearance-population-heading">
            人口の変化と人口1,000人当たりの検挙
          </h2>
          <p className="intro-copy">
            検挙数の変化が、参照人口の増減と人口当たり参考比率のどちらに表れているかを、日本人等と外国人全体に分けて確認します。
          </p>
        </div>
        <Badge variant="outline">
          {view.years[0]}–{view.years.at(-1)}年
        </Badge>
      </div>

      <div className="clearance-population-controls">
        <fieldset className="control-field">
          <legend>分子</legend>
          <div className="mode-buttons">
            <Button
              type="button"
              variant={metric === 'cleared_cases' ? 'default' : 'outline'}
              aria-pressed={metric === 'cleared_cases'}
              onClick={() => onMetricChange('cleared_cases')}
            >
              検挙件数
            </Button>
            <Button
              type="button"
              variant={metric === 'cleared_persons' ? 'default' : 'outline'}
              aria-pressed={metric === 'cleared_persons'}
              onClick={() => onMetricChange('cleared_persons')}
            >
              検挙人員
            </Button>
          </div>
        </fieldset>
      </div>

      <Alert className="clearance-population-alert">
        <Info aria-hidden="true" />
        <AlertTitle>確率ではなく、公表統計由来の参考比率です</AlertTitle>
        <AlertDescription>{view.uiCaveat}</AlertDescription>
      </Alert>

      <div className="clearance-population-grid">
        <ClearancePopulationPanel
          panel={view.japanese}
          view={view}
          testId="japanese-clearance-population-panel"
        />
        <ClearancePopulationPanel
          panel={view.foreign}
          view={view}
          testId="foreign-clearance-population-panel"
        />
      </div>

      <Card className="clearance-population-sources">
        <CardHeader>
          <BookOpen aria-hidden="true" />
          <CardTitle>この参考比率の出典</CardTitle>
          <CardDescription>
            犯罪統計の分子と、年ごとの日本人人口・在留外国人数の分母を別々に辿れます。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <details>
            <summary>{view.sources.length}件の出典を表示</summary>
            <SourceList sources={view.sources} />
          </details>
        </CardContent>
      </Card>
    </section>
  );
}

function OffenseCompositionLegend({
  view,
}: {
  view: OffenseCompositionViewModel;
}) {
  return (
    <div className="offense-legend" aria-label="犯罪類型の凡例">
      {view.categories.map((category) => (
        <div key={category.id} data-testid="offense-category-legend">
          <i style={{ backgroundColor: category.color }} aria-hidden="true" />
          <span>{category.label}</span>
        </div>
      ))}
    </div>
  );
}

function OffenseHeatmap({ view }: { view: OffenseCompositionViewModel }) {
  return (
    <div className="table-scroll">
      <table
        className="offense-heatmap"
        data-testid="offense-composition-heatmap"
      >
        <caption className="sr-only">
          {view.metricLabel}に占める刑法犯上位6区分の構成比と実数
        </caption>
        <thead>
          <tr>
            <th scope="col">国籍等</th>
            <th scope="col">合計</th>
            {view.categories.map((category) => (
              <th scope="col" key={category.id}>
                {category.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {view.entities.map((entity) => (
            <tr
              key={entity.id}
              className={
                entity.isJapaneseReference ? 'japanese-reference-row' : ''
              }
              data-testid={
                entity.isJapaneseReference
                  ? 'offense-japanese-reference'
                  : undefined
              }
            >
              <th scope="row">
                {entity.name}
                {entity.isJapaneseReference ? (
                  <Badge variant="outline">残差参考値</Badge>
                ) : null}
              </th>
              <td className="offense-total-cell">
                {entity.total.toLocaleString('ja-JP')}
                <span>{view.unitLabel}</span>
              </td>
              {entity.cells.map((cell) => {
                const category = view.categories.find(
                  (candidate) => candidate.id === cell.offenseId,
                );
                if (!category) return null;
                return (
                  <td
                    key={cell.offenseId}
                    style={{
                      backgroundColor: offenseHeatmapColor(
                        category.color,
                        cell.share,
                      ),
                    }}
                    title={`${entity.name} / ${category.label}: ${
                      cell.share === null
                        ? '構成比算出不能'
                        : formatOffenseShare(cell.share)
                    }, ${cell.count.toLocaleString('ja-JP')}${view.unitLabel}`}
                  >
                    {cell.share === null ? (
                      <strong>—</strong>
                    ) : (
                      <strong>{formatOffenseShare(cell.share)}</strong>
                    )}
                    <span>
                      {cell.count.toLocaleString('ja-JP')}
                      {view.unitLabel}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OffenseStackedRow({
  entity,
  view,
}: {
  entity: OffenseCompositionEntity;
  view: OffenseCompositionViewModel;
}) {
  return (
    <article
      className={`offense-stacked-row ${
        entity.isJapaneseReference ? 'japanese-reference-row' : ''
      }`}
      data-testid="offense-stacked-row"
    >
      <div className="offense-stacked-label">
        <strong>{entity.name}</strong>
        <span>
          合計 {entity.total.toLocaleString('ja-JP')}
          {view.unitLabel}
        </span>
      </div>
      {entity.total === 0 ? (
        <div className="offense-stacked-unavailable">構成比算出不能</div>
      ) : (
        <figure
          className="offense-stacked-bar"
          aria-label={`${entity.name}の${view.metricLabel}構成`}
        >
          {entity.cells.map((cell) => {
            const category = view.categories.find(
              (candidate) => candidate.id === cell.offenseId,
            );
            if (!category || cell.share === null) return null;
            return (
              <i
                key={cell.offenseId}
                style={{
                  width: `${cell.share * 100}%`,
                  backgroundColor: category.color,
                }}
                title={`${category.label}: ${formatOffenseShare(
                  cell.share,
                )} / ${cell.count.toLocaleString('ja-JP')}${view.unitLabel}`}
              />
            );
          })}
        </figure>
      )}
    </article>
  );
}

function OffenseStacked({ view }: { view: OffenseCompositionViewModel }) {
  return (
    <div
      className="offense-stacked-list"
      data-testid="offense-composition-stacked"
    >
      {view.entities.map((entity) => (
        <OffenseStackedRow key={entity.id} entity={entity} view={view} />
      ))}
    </div>
  );
}

export function CrimeAtlasDashboard({
  dashboard,
}: {
  dashboard: DashboardData;
}) {
  const [metricId, setMetricId] = useState<ContextMetricId>(
    'all_resident_recognized_cases',
  );
  const [mode, setMode] = useState<ValueMode>('ratio');
  const [nationalityPerspectiveId, setNationalityPerspectiveId] =
    useState<NationalityPerspectiveId>(NATIONALITY_CASES_COMPARISON_ID);
  const [clearanceShareMetric, setClearanceShareMetric] =
    useState<ClearanceShareMetric>('cleared_cases');
  const [clearancePopulationMetric, setClearancePopulationMetric] =
    useState<ClearanceShareMetric>('cleared_cases');
  const [offenseMetric, setOffenseMetric] =
    useState<OffenseCompositionMetric>('cleared_persons');
  const [offenseOrder, setOffenseOrder] =
    useState<OffenseCompositionOrder>('cluster');
  const [offenseDisplay, setOffenseDisplay] =
    useState<OffenseDisplayMode>('heatmap');
  const view = useMemo(
    () => buildRegionalViewModel(dashboard, metricId, mode),
    [dashboard, metricId, mode],
  );
  const nationalityView = useMemo(
    () =>
      buildSelectableNationalityViewModel(
        dashboard,
        nationalityPerspectiveId,
        'ratio',
      ),
    [dashboard, nationalityPerspectiveId],
  );
  const clearanceShareView = useMemo(
    () => buildClearanceShareTrendViewModel(dashboard, clearanceShareMetric),
    [clearanceShareMetric, dashboard],
  );
  const clearancePopulationView = useMemo(
    () =>
      buildClearancePopulationTrendViewModel(
        dashboard,
        clearancePopulationMetric,
      ),
    [clearancePopulationMetric, dashboard],
  );
  const offenseView = useMemo(
    () =>
      buildOffenseCompositionViewModel(dashboard, offenseMetric, offenseOrder),
    [dashboard, offenseMetric, offenseOrder],
  );
  const chartRows = view.prefectures.slice(0, 10);
  const countLeader =
    view.tokyo.rawCount > view.saitama.rawCount ? view.tokyo : view.saitama;
  const ratioLeader =
    view.tokyo.referenceRatio > view.saitama.referenceRatio
      ? view.tokyo
      : view.saitama;
  const unavailableOffenseEntities = offenseView.entities.filter(
    (entity) => entity.total === 0,
  );

  return (
    <div className="atlas-shell">
      <header className="atlas-header">
        <div className="atlas-brand">
          <div className="atlas-mark" aria-hidden="true">
            <Scale />
          </div>
          <div>
            <p>公表統計を、出典と注意点とともに</p>
            <h1>全国犯罪統計地図</h1>
          </div>
        </div>
        <nav className="atlas-nav" aria-label="ページ内メニュー">
          <a href="#about">このサイトについて</a>
          <a href="#regional">地域全体</a>
          <a href="#nationality">国籍等別</a>
          <a href="#clearance-share">時系列</a>
          <a href="#clearance-population">人口と検挙</a>
          <a href="#offense">犯罪の種類</a>
        </nav>
        <Badge variant="outline" className="verified-badge">
          <CheckCircle2 data-icon="inline-start" />
          出典を確認済み
        </Badge>
      </header>

      <main className="atlas-main">
        <section
          id="about"
          className="site-about"
          aria-labelledby="about-heading"
        >
          <div className="site-about-lead">
            <p className="section-kicker">はじめに</p>
            <h2 id="about-heading">このサイトについて</h2>
            <div className="site-about-copy">
              <p>
                犯罪に関する公的な情報は、複数の機関や資料に分散しており、必要な数値へたどり着き、比較できる形に整理することは容易ではありません。
              </p>
              <p>
                このサイトは、それらの公表情報を収集・整理し、犯罪統計と人口統計を可視化する試作サイトです。数値の出典や定義の違い、算出できない項目も省略せず示します。
              </p>
              <p>
                このサイトは数値を確認・比較するためのものであり、数値の良し悪しの評価、原因の推定、集団や個人に対する価値判断は行いません。
              </p>
            </div>
          </div>
          <div className="site-about-grid">
            <article>
              <h3>まず地域全体を見る</h3>
              <p>
                日本人と外国人を合わせた地域全体について、犯罪件数の実数と人口当たりの参考比率を比較します。
              </p>
              <a href="#regional">地域全体の表示へ</a>
            </article>
            <article>
              <h3>次に国籍等別を見る</h3>
              <p>
                全国の公表値を、日本を含む全区分の参考比率順、時系列、犯罪の種類という複数の見方で確認できます。
              </p>
              <a href="#nationality">国籍等別の表示へ</a>
            </article>
            <article>
              <h3>この数字だけでは分からないこと</h3>
              <p>
                個人が犯罪をする可能性、犯罪の原因、国籍等別かつ都道府県別の値は判断できません。異なる統計を割った値は参考値です。
              </p>
              <a
                href={INTERPRETATION_NOTE_URL}
                target="_blank"
                rel="noreferrer"
              >
                数字の読み方を確認 <ExternalLink aria-hidden="true" />
              </a>
            </article>
          </div>
          <div className="about-links">
            <a href={PROJECT_README_URL} target="_blank" rel="noreferrer">
              プロジェクトの詳しい説明を読む <ExternalLink aria-hidden="true" />
            </a>
            <span>認知件数＝警察が犯罪として把握した件数</span>
            <span>検挙件数＝警察が検挙した事件の件数</span>
            <span>検挙人員＝警察が検挙した人の数</span>
          </div>
        </section>

        <section
          id="regional"
          className="intro-grid"
          aria-labelledby="regional-heading"
        >
          <div>
            <p className="section-kicker">地域全体</p>
            <h2 id="regional-heading">
              {view.isSameYearGap
                ? '認知件数と検挙件数の同年差'
                : '国籍で分けない、地域全体の状況'}
            </h2>
            <p className="intro-copy">
              {view.isSameYearGap
                ? '同じ年・同じ警察統計上の地域について、刑法犯認知件数から検挙件数を引いた差と、認知件数に占める割合を表示します。これは未解決事件を直接数えたものではありません。'
                : '分母の総人口は、日本国籍の住民と外国籍の住民を含みます。地域の犯罪件数そのものと、人口規模をそろえた参考比率を見比べられます。'}
            </p>
          </div>
          <div className="snapshot-meta">
            <CalendarDays aria-hidden="true" />
            <span>
              犯罪統計 {view.year}年 /{' '}
              {view.isSameYearGap
                ? '認知・検挙とも同じ年の件数'
                : `人口 ${view.referenceDate}`}
            </span>
          </div>
        </section>

        <Alert className="method-alert">
          <Info aria-hidden="true" />
          <AlertTitle>
            {view.isSameYearGap
              ? '「未解決率」ではありません'
              : '公表統計由来の参考比率です'}
          </AlertTitle>
          <AlertDescription>
            {view.isSameYearGap ? (
              <>
                検挙件数には、前年以前に認知された事件が含まれることがあります。そのため、同じ事件を認知から検挙まで追跡した数字ではありません。
              </>
            ) : (
              <>
                公的機関が算出した正式な犯罪率ではありません。1年間の犯罪件数と、その年の10月1日時点の人口を組み合わせた参考値です。犯罪件数に数えられた人の居住地は確認できません。
              </>
            )}
            <span className="method-contract">
              算式{' '}
              <code>
                {regionalFormulaLabel(view)} ×{' '}
                {view.displayMultiplier.toLocaleString('ja-JP')}
              </code>
              {' ／ '}分子と分母が同じ対象を数えているかは確認できていません
            </span>
          </AlertDescription>
        </Alert>

        <section className="control-deck" aria-label="表示条件">
          <label className="control-field">
            <span>指標</span>
            <NativeSelect
              aria-label="指標"
              value={metricId}
              onChange={(event) =>
                setMetricId(event.target.value as ContextMetricId)
              }
              className="w-full"
            >
              {CONTEXT_METRICS.map((metric) => (
                <NativeSelectOption key={metric.id} value={metric.id}>
                  {metric.label}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </label>
          <fieldset className="control-field">
            <legend>表示</legend>
            <div className="mode-buttons">
              <Button
                type="button"
                variant={mode === 'ratio' ? 'default' : 'outline'}
                aria-pressed={mode === 'ratio'}
                onClick={() => setMode('ratio')}
              >
                {view.isSameYearGap ? '同年差分率' : '人口当たり'}
              </Button>
              <Button
                type="button"
                variant={mode === 'count' ? 'default' : 'outline'}
                aria-pressed={mode === 'count'}
                onClick={() => setMode('count')}
              >
                {view.rawCountLabel}
              </Button>
            </div>
          </fieldset>
          <div className="national-stat">
            <span>全国</span>
            <strong>{formatDashboardValue(view.national.value, mode)}</strong>
            <small>{view.unitLabel}</small>
          </div>
        </section>

        <section
          className="comparison-section"
          aria-labelledby="comparison-heading"
        >
          <div className="section-heading-row">
            <div>
              <p className="section-kicker">地域比較の例</p>
              <h2 id="comparison-heading">
                {view.isSameYearGap
                  ? '同年差分の件数と割合を比較'
                  : '人口規模をそろえて比較'}
              </h2>
            </div>
            <Badge variant="secondary">{view.metricLabel}</Badge>
          </div>

          <div className="comparison-grid">
            <ComparisonCard
              datum={view.tokyo}
              mode={mode}
              unitLabel={view.unitLabel}
              rawCountLabel={view.rawCountLabel}
              denominatorLabel={view.denominatorLabel}
              testId="tokyo-comparison"
            />
            <div className="comparison-readout">
              <div>
                <ArrowUpRight aria-hidden="true" />
                <span>{view.isSameYearGap ? '同年差分件数' : '実数'}</span>
                <strong>{countLeader.name}が多い</strong>
              </div>
              <div>
                <ArrowDownRight aria-hidden="true" />
                <span>{view.isSameYearGap ? '同年差分率' : '人口当たり'}</span>
                <strong>{ratioLeader.name}が高い</strong>
              </div>
              <p>
                {view.isSameYearGap
                  ? '検挙件数には前年以前に認知された事件が含まれるため、未解決事件数の地域順位ではありません。'
                  : '順序が変わる場合、見えている差の一部は地域人口の大きさです。'}
              </p>
            </div>
            <ComparisonCard
              datum={view.saitama}
              mode={mode}
              unitLabel={view.unitLabel}
              rawCountLabel={view.rawCountLabel}
              denominatorLabel={view.denominatorLabel}
              testId="saitama-comparison"
            />
          </div>
        </section>

        <PrefectureMap
          prefectures={view.prefectures}
          mode={mode}
          unitLabel={view.unitLabel}
          ratioUnitLabel={view.ratioUnitLabel}
          rawCountLabel={view.rawCountLabel}
          denominatorLabel={view.denominatorLabel}
          ratioDetailLabel={view.ratioDetailLabel}
        />

        <div className="content-grid">
          <Card className="ranking-card">
            <CardHeader>
              <div>
                <p className="section-kicker">都道府県の比較</p>
                <CardTitle>{view.metricLabel}</CardTitle>
                <CardDescription>
                  {view.isSameYearGap
                    ? mode === 'ratio'
                      ? '同年差分率'
                      : '同年差分件数'
                    : mode === 'ratio'
                      ? '人口当たり'
                      : '実数'}
                  の大きい10都道府県（全47都道府県は地図に表示）
                </CardDescription>
              </div>
              <Badge variant="outline">{view.unitLabel}</Badge>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={chartConfig}
                className="ranking-chart"
                initialDimension={{ width: 700, height: 420 }}
              >
                <BarChart
                  accessibilityLayer
                  data={chartRows}
                  layout="vertical"
                  margin={{ left: 8, right: 28, top: 8, bottom: 8 }}
                >
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) =>
                      Number(value).toLocaleString('ja-JP')
                    }
                  />
                  <YAxis
                    dataKey="name"
                    type="category"
                    axisLine={false}
                    tickLine={false}
                    width={62}
                  />
                  <ChartTooltip
                    cursor={{ fill: 'var(--muted)' }}
                    content={
                      <ChartTooltipContent
                        hideLabel
                        formatter={(value, _name, item) => (
                          <div className="tooltip-row">
                            <span>{item.payload.name}</span>
                            <strong>
                              {formatDashboardValue(Number(value), mode)}{' '}
                              {view.unitLabel}
                            </strong>
                          </div>
                        )}
                      />
                    }
                  />
                  <Bar
                    dataKey="value"
                    fill="var(--color-value)"
                    radius={[0, 5, 5, 0]}
                  />
                </BarChart>
              </ChartContainer>
              <ol className="accessible-ranking">
                {chartRows.map((row, index) => (
                  <li key={row.id}>
                    <span>
                      {index + 1}. {row.name}
                    </span>
                    <strong>
                      {formatDashboardValue(row.value, mode)} {view.unitLabel}
                    </strong>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          <aside className="evidence-column">
            <Card>
              <CardHeader>
                <BookOpen aria-hidden="true" />
                <CardTitle>この表示の出典</CardTitle>
                <CardDescription>
                  {view.isSameYearGap
                    ? '認知件数と検挙件数は同じS15へ辿れます。'
                    : '分子と分母を別々に辿れます。'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SourceList sources={view.sources} />
              </CardContent>
            </Card>

            <Card className="refusal-card">
              <CardHeader>
                <ShieldAlert aria-hidden="true" />
                <CardTitle>作らなかった値</CardTitle>
                <CardDescription>
                  非公表・非接続を0や推計値で埋めません。
                </CardDescription>
              </CardHeader>
              <CardContent>
                <strong className="refusal-count">
                  {view.refusedCount}区分は未算出
                </strong>
                <ul>
                  {view.refusalReasons.map(({ reason, count }) => (
                    <li key={reason}>
                      <span>{refusalLabels[reason] ?? reason}</span>
                      <Badge variant="secondary">{count}</Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </aside>
        </div>

        <section
          id="nationality"
          className="nationality-section"
          aria-labelledby="nationality-heading"
          data-testid="nationality-comparison-section"
        >
          <div className="section-heading-row">
            <div>
              <p className="section-kicker">国籍等別の全国値</p>
              <h2 id="nationality-heading">日本を含む国籍等別の全国比較</h2>
              <p className="intro-copy">
                分子・対象範囲を切り替え、全国単位の公表値を比較します。高い側だけに絞らず、算出できない行を含む
                {nationalityView.rows.length}
                区分すべてを表示します。対応する日本国籍分子がない観点でも日本を消さず、未算出とします。個別国籍
                ×
                都道府県の分子は公表されていません。地域別に推計・按分はしません。
              </p>
            </div>
            <Badge variant="outline">{nationalityView.year} / 日本全国</Badge>
          </div>

          <div className="nationality-controls">
            <label className="control-field nationality-perspective-control">
              <span>分子・対象範囲</span>
              <NativeSelect
                aria-label="国籍等別の分子・対象範囲"
                value={nationalityPerspectiveId}
                onChange={(event) =>
                  setNationalityPerspectiveId(
                    event.target.value as NationalityPerspectiveId,
                  )
                }
                className="w-full"
              >
                {NATIONALITY_PERSPECTIVES.map((perspective) => (
                  <NativeSelectOption
                    key={perspective.id}
                    value={perspective.id}
                  >
                    {perspective.label}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <div className="definition-strip">
              <span>現在の対象範囲</span>
              <strong>{nationalityView.scopeLabel}</strong>
            </div>
            <div className="definition-strip">
              <span>参考比率の式</span>
              <strong>
                {nationalityView.numeratorLabel} ÷ 人口 ×{' '}
                {nationalityView.displayMultiplier}
              </strong>
            </div>
          </div>

          <Alert className="nationality-alert">
            <ShieldAlert aria-hidden="true" />
            <AlertTitle>値は隠さず、属性の評価には使いません</AlertTitle>
            <AlertDescription>
              犯罪統計と人口統計は同じ人を追跡したものではなく、対象範囲や基準日が異なる場合があります。参考比率の高い順という並びは数値の大小だけを示し、集団の本質や、個人が犯罪をする可能性の判断ではありません。未算出の行も0とせず残します。分母基準日は
              {nationalityView.referenceDates.join(' / ')} です。
            </AlertDescription>
          </Alert>

          <NationalityOrderedPlot view={nationalityView} />

          <div className="nationality-grid">
            <Card className="nationality-table-card">
              <CardHeader>
                <div>
                  <CardTitle>全{nationalityView.rows.length}区分</CardTitle>
                  <CardDescription>
                    元データの掲載順で、算出値・注意点・未算出の理由・出典を省略せず表示します。
                  </CardDescription>
                </div>
                <Badge variant="secondary">実数と参考比率を併記</Badge>
              </CardHeader>
              <CardContent className="table-scroll">
                <table
                  className="nationality-table nationality-full-table"
                  data-testid="nationality-comparison-table"
                >
                  <caption className="sr-only">
                    {nationalityView.metricLabel}の全
                    {nationalityView.rows.length}国籍等区分
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">国籍等（公表表記）</th>
                      <th scope="col">{nationalityView.numeratorLabel}</th>
                      <th scope="col">分母人口</th>
                      <th scope="col">参考比率</th>
                      <th scope="col">出典番号</th>
                      <th scope="col">注記</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nationalityView.rows.map((row) => (
                      <tr
                        key={row.id}
                        data-testid={
                          row.isJapaneseReference
                            ? 'nationality-japanese-reference'
                            : undefined
                        }
                        className={
                          row.isJapaneseReference
                            ? 'japanese-reference-row'
                            : ''
                        }
                      >
                        <td>
                          <span className="nationality-label">{row.name}</span>
                          {row.isJapaneseReference ? (
                            <Badge variant="outline">
                              {row.calculationStatus === 'calculated'
                                ? '残差参考値'
                                : '未算出'}
                            </Badge>
                          ) : null}
                        </td>
                        <td>{row.numerator?.toLocaleString('ja-JP') ?? '—'}</td>
                        <td>
                          {row.denominator?.toLocaleString('ja-JP') ?? '—'}
                        </td>
                        <td>
                          {row.referenceRatio === null ? (
                            <span className="not-calculated">未算出</span>
                          ) : (
                            <>
                              {formatDashboardValue(
                                row.referenceRatio,
                                'ratio',
                              )}
                              <span> / 1,000人</span>
                            </>
                          )}
                        </td>
                        <td>
                          <code>
                            {row.numeratorSourceIds.join(' + ') || '—'} /{' '}
                            {row.denominatorSourceId ?? '—'}
                          </code>
                        </td>
                        <td className="nationality-notes">
                          {row.calculationStatus === 'refused' ? (
                            <InterpretationNote
                              code={row.refusalReason ?? ''}
                            />
                          ) : row.warningCodes.length > 0 ? (
                            row.warningCodes.map((code) => (
                              <InterpretationNote key={code} code={code} />
                            ))
                          ) : row.isJapaneseReference ? (
                            <span>
                              全国の全住民値から全外国人値を差し引いた参考値
                            </span>
                          ) : (
                            <span>—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            <aside className="nationality-evidence">
              <Card className="warning-card">
                <CardHeader>
                  <CardTitle>注意が必要な値も表示</CardTitle>
                  <CardDescription>
                    人口や犯罪件数・人員が少ない場合も隠さず、注意点を同じ行に表示します。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <strong>
                    {
                      nationalityView.calculatedRows.filter(
                        (row) => row.warningCodes.length > 0,
                      ).length
                    }{' '}
                    区分に注意表示／算出済み
                    {nationalityView.calculatedRows.length}区分
                  </strong>
                  <ul>
                    {nationalityView.warningCodes.map((code) => (
                      <li key={code}>
                        <InterpretationNote code={code} />
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card className="refusal-card">
                <CardHeader>
                  <CardTitle>作らなかった値</CardTitle>
                  <CardDescription>
                    対応する犯罪件数・人員や人口を用意できない区分は推計しません。実数が公表されている場合は左表に残します。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <strong className="refusal-count">
                    {nationalityView.refusedCount}区分は未算出
                  </strong>
                  <ul>
                    {nationalityView.refusalReasons.map(({ reason, count }) => (
                      <li key={reason}>
                        <span>{refusalLabels[reason] ?? reason}</span>
                        <Badge variant="secondary">{count}</Badge>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <BookOpen aria-hidden="true" />
                  <CardTitle>この表示の出典</CardTitle>
                  <CardDescription>
                    犯罪分子と人口分母を別々に辿れます。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <SourceList sources={nationalityView.sources} />
                </CardContent>
              </Card>
            </aside>
          </div>

          <div className="mismatch-strip" aria-label="定義上の不一致">
            <span>比較時に残る定義の違い</span>
            <div>
              {nationalityView.mismatchCodes.map((code) => (
                <InterpretationNote key={code} code={code} />
              ))}
            </div>
          </div>
        </section>

        <ClearanceShareTrend
          view={clearanceShareView}
          metric={clearanceShareMetric}
          onMetricChange={setClearanceShareMetric}
        />

        <ClearancePopulationTrend
          view={clearancePopulationView}
          metric={clearancePopulationMetric}
          onMetricChange={setClearancePopulationMetric}
        />

        <section
          id="offense"
          className="offense-section"
          aria-labelledby="offense-heading"
          data-testid="offense-composition-section"
        >
          <div className="section-heading-row">
            <div>
              <p className="section-kicker">犯罪の種類</p>
              <h2 id="offense-heading">日本を含む国籍等別・犯罪類型の構成</h2>
              <p className="intro-copy">
                各国籍等の刑法犯検挙総数を100%として、相互排他的な上位6区分の内訳を表示します。日本を含む
                {offenseView.entities.length}
                区分を省略せず、構成比と公表値・差し引きによる参考値を同じ表で確認できます。構成比は犯罪の多寡を示す人口当たり比率ではありません。
              </p>
            </div>
            <Badge variant="outline">
              {offenseView.year} / {offenseView.entities.length}区分 ×{' '}
              {offenseView.categories.length}類型
            </Badge>
          </div>

          <div className="offense-controls" aria-label="犯罪類型表示条件">
            <fieldset className="control-field">
              <legend>分子</legend>
              <div className="mode-buttons">
                <Button
                  type="button"
                  variant={
                    offenseMetric === 'cleared_persons' ? 'default' : 'outline'
                  }
                  aria-pressed={offenseMetric === 'cleared_persons'}
                  onClick={() => setOffenseMetric('cleared_persons')}
                >
                  検挙人員
                </Button>
                <Button
                  type="button"
                  variant={
                    offenseMetric === 'cleared_cases' ? 'default' : 'outline'
                  }
                  aria-pressed={offenseMetric === 'cleared_cases'}
                  onClick={() => setOffenseMetric('cleared_cases')}
                >
                  検挙件数
                </Button>
              </div>
            </fieldset>
            <fieldset className="control-field">
              <legend>並び順</legend>
              <div className="mode-buttons">
                <Button
                  type="button"
                  variant={offenseOrder === 'cluster' ? 'default' : 'outline'}
                  aria-pressed={offenseOrder === 'cluster'}
                  onClick={() => setOffenseOrder('cluster')}
                >
                  似た構成を近くする順
                </Button>
                <Button
                  type="button"
                  variant={offenseOrder === 'source' ? 'default' : 'outline'}
                  aria-pressed={offenseOrder === 'source'}
                  onClick={() => setOffenseOrder('source')}
                >
                  元データの掲載順
                </Button>
              </div>
            </fieldset>
            <fieldset className="control-field">
              <legend>可視化</legend>
              <div className="mode-buttons">
                <Button
                  type="button"
                  variant={offenseDisplay === 'heatmap' ? 'default' : 'outline'}
                  aria-pressed={offenseDisplay === 'heatmap'}
                  onClick={() => setOffenseDisplay('heatmap')}
                >
                  色の濃淡で比較
                </Button>
                <Button
                  type="button"
                  variant={offenseDisplay === 'stacked' ? 'default' : 'outline'}
                  aria-pressed={offenseDisplay === 'stacked'}
                  onClick={() => setOffenseDisplay('stacked')}
                >
                  100%積み上げ棒
                </Button>
              </div>
            </fieldset>
          </div>

          <OffenseCompositionLegend view={offenseView} />

          <Alert className="offense-alert">
            <Info aria-hidden="true" />
            <AlertTitle>公式区分と、このサイト上の整理を分けます</AlertTitle>
            <AlertDescription>
              凶悪犯は警察庁の公式区分です。残る5区分を軽犯罪とは定義しません。似た構成が近くなるよう機械的に並べていますが、属性の本質や因果、優劣、危険度を示す順位ではありません。合計
              {offenseView.smallNumberTotalThreshold}
              未満の区分には、値が変動しやすいという注意を表示します。
              <details className="method-details">
                <summary>並べ方の詳しい方法</summary>
                <p>
                  6区分の構成比について、Jensen–Shannon距離で類似度を測り、平均連結法による階層クラスタリングで順序を決めています。
                </p>
              </details>
            </AlertDescription>
          </Alert>

          {unavailableOffenseEntities.map((entity) => (
            <p className="offense-unavailable-note" key={entity.id}>
              {entity.name}: {offenseView.metricLabel}
              構成は算出不能（{offenseView.metricLabel}
              総数0）。0%とは表示しません。
            </p>
          ))}

          <Card className="offense-visual-card">
            <CardHeader>
              <div>
                <CardTitle>
                  {offenseView.metricLabel}の類型構成・
                  {offenseOrder === 'cluster'
                    ? '似た構成を近くする順'
                    : '元データの掲載順'}
                </CardTitle>
                <CardDescription>
                  各マスに構成比と実数を併記します。色の種類は犯罪類型、濃さは構成比を示します。
                </CardDescription>
              </div>
              <Badge variant="secondary">
                {offenseDisplay === 'heatmap'
                  ? '色の濃淡で比較'
                  : '100%積み上げ棒'}
              </Badge>
            </CardHeader>
            <CardContent>
              {offenseDisplay === 'heatmap' ? (
                <OffenseHeatmap view={offenseView} />
              ) : (
                <OffenseStacked view={offenseView} />
              )}
            </CardContent>
          </Card>

          <div className="offense-evidence-grid">
            <Card>
              <CardHeader>
                <BookOpen aria-hidden="true" />
                <CardTitle>この表示の出典</CardTitle>
                <CardDescription>
                  S08の外国人公表値とS15の全人値を辿れます。
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SourceList sources={offenseView.sources} />
              </CardContent>
            </Card>
            <Card className="warning-card">
              <CardHeader>
                <ShieldAlert aria-hidden="true" />
                <CardTitle>読み方の境界</CardTitle>
                <CardDescription>
                  構成比は検挙件数・検挙人員の内訳です。犯罪の多さ、集団の本質や原因、個人が犯罪をする可能性を示すものではありません。
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="offense-method-note">
                  日本は、S15の全住民値からS08の全外国人値を差し引いた参考値です。似た構成を近くする表示は探索のためのもので、優劣・危険度の順位ではありません。
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      <footer className="atlas-footer">
        <section
          className="footer-feedback"
          aria-labelledby="footer-feedback-title"
        >
          <div className="footer-feedback-copy">
            <h2 id="footer-feedback-title">可視化の提案・不具合報告</h2>
            <p>
              見たい比較や図の提案、表示上の不具合をGitHub
              Issuesで受け付けています。投稿にはGitHubアカウントが必要です。
            </p>
            <p className="footer-feedback-notice">
              投稿内容はGitHub上で公開されます。個人情報や個別事件を特定できる情報は書き込まないでください。
            </p>
          </div>
          <nav className="footer-feedback-actions" aria-label="GitHub Issues">
            <a
              className="footer-issue-link footer-issue-link-primary"
              href={GITHUB_NEW_ISSUE_URL}
              target="_blank"
              rel="noreferrer"
            >
              要望・不具合を送る（GitHub Issues）
              <ExternalLink aria-hidden="true" />
            </a>
            <a
              className="footer-issue-link footer-issue-link-secondary"
              href={GITHUB_ISSUES_URL}
              target="_blank"
              rel="noreferrer"
            >
              寄せられた内容を見る
              <ExternalLink aria-hidden="true" />
            </a>
          </nav>
        </section>
        <div className="footer-meta">
          <span>公表値をその定義差とともに表示</span>
          <span>表示データ作成日時 {dashboard.generated_at}</span>
        </div>
      </footer>
    </div>
  );
}
