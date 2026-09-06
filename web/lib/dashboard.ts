export const SAME_YEAR_GAP_CONTEXT_ID =
  'all_resident_same_year_recognition_clearance_gap' as const;

export const CONTEXT_METRICS = [
  {
    id: 'all_resident_recognized_cases',
    label: '刑法犯認知件数',
  },
  {
    id: 'all_resident_cleared_cases',
    label: '刑法犯検挙件数',
  },
  {
    id: 'all_resident_cleared_persons',
    label: '刑法犯検挙人員',
  },
  {
    id: SAME_YEAR_GAP_CONTEXT_ID,
    label: '認知件数と検挙件数の同年差（未解決数ではない）',
  },
] as const;

export const NATIONALITY_METRICS = [
  {
    id: 'x_cleared_persons_exact',
    label: '全外国人・検挙人員（同国籍人口）',
  },
  {
    id: 'x_cleared_cases_exact',
    label: '全外国人・検挙件数（同国籍人口）',
  },
  {
    id: 'y_cleared_persons_exact',
    label: '来日外国人・検挙人員（同国籍人口）',
  },
  {
    id: 'y_cleared_cases_exact',
    label: '来日外国人・検挙件数（同国籍人口）',
  },
  {
    id: 'x_cleared_persons_as_published_mismatch',
    label: '全外国人・検挙人員（公表区分ベース）',
  },
  {
    id: 'x_cleared_cases_as_published_mismatch',
    label: '全外国人・検挙件数（公表区分ベース）',
  },
  {
    id: 'y_cleared_persons_as_published_mismatch',
    label: '来日外国人・検挙人員（公表区分ベース）',
  },
  {
    id: 'y_cleared_cases_as_published_mismatch',
    label: '来日外国人・検挙件数（公表区分ベース）',
  },
] as const;

export const NATIONALITY_COMPARISON_ID =
  'nationality_criminal_code_cleared_persons' as const;

export const NATIONALITY_CASES_COMPARISON_ID =
  'nationality_criminal_code_cleared_cases' as const;

export const OFFENSE_COMPOSITION_ID =
  'nationality_criminal_code_offense_composition' as const;

export const CLEARANCE_SHARE_TREND_ID =
  'national_criminal_code_clearance_foreign_share' as const;

const CLEARANCE_SHARE_LABEL_JA =
  '全国の刑法犯検挙（日本人等を含む）に占める外国人区分の割合';
const CLEARANCE_SHARE_INTERPRETATION_POLICY =
  'share_of_clearances_not_population_risk';
const CLEARANCE_SHARE_UI_CAVEAT =
  '分母は日本人等を含む全国の刑法犯検挙総数、分子は警察庁の「外国人」「来日外国人」区分、または両者の算術差分である。検挙全体に占める構成比であり、人口当たりの犯罪率、犯罪の発生率、個人のriskを示さない。「来日外国人」は定着居住者、在日米軍関係者、在留資格不明者を除く区分で、短期滞在者だけを指さない。差分にも定着居住者以外が含まれるため、普段から住む外国人だけを表す値ではない。';
const CLEARANCE_SHARE_SCOPE_CONTRACTS = {
  all_foreign: {
    label: '外国人全体',
    numeratorSourceId: 'S08',
    numeratorSourceIds: ['S08'],
    derivationMethod: 'direct_published_counts_division',
    requiredFlags: [
      'all_foreign_scope_not_resident_foreigner_population',
      'denominator_includes_japanese_and_others',
      'share_of_clearance_counts_not_population_rate',
    ],
  },
  visiting_foreign: {
    label: '来日外国人',
    numeratorSourceId: 'S09',
    numeratorSourceIds: ['S09'],
    derivationMethod: 'direct_published_counts_division',
    requiredFlags: [
      'denominator_includes_japanese_and_others',
      'share_of_clearance_counts_not_population_rate',
      'visiting_foreign_includes_nonresidents',
    ],
  },
  all_foreign_minus_visiting_foreign: {
    label: '外国人全体−来日外国人（差分）',
    numeratorSourceId: 'S08',
    numeratorSourceIds: ['S08', 'S09'],
    derivationMethod: 'arithmetic_residual_all_foreign_minus_visiting_foreign',
    requiredFlags: [
      'arithmetic_residual_not_directly_published',
      'denominator_includes_japanese_and_others',
      'residual_includes_settled_residents_us_forces_and_unknown_status',
      'residual_not_equivalent_to_usual_residents',
      'share_of_clearance_counts_not_population_rate',
    ],
  },
} as const;

type ClearanceShareScope = keyof typeof CLEARANCE_SHARE_SCOPE_CONTRACTS;

export const NATIONALITY_PERSPECTIVES = [
  {
    id: NATIONALITY_COMPARISON_ID,
    label: '刑法犯の検挙人員（日本を含む）',
  },
  {
    id: NATIONALITY_CASES_COMPARISON_ID,
    label: '刑法犯の検挙件数（日本を含む）',
  },
  {
    id: 'x_cleared_persons_exact',
    label: '全外国人の検挙人員（同じ国籍区分で人口と対応）',
  },
  {
    id: 'x_cleared_cases_exact',
    label: '全外国人の検挙件数（同じ国籍区分で人口と対応）',
  },
  {
    id: 'y_cleared_persons_exact',
    label: '来日外国人の検挙人員（同じ国籍区分で人口と対応）',
  },
  {
    id: 'y_cleared_cases_exact',
    label: '来日外国人の検挙件数（同じ国籍区分で人口と対応）',
  },
  {
    id: 'x_cleared_persons_as_published_mismatch',
    label: '全外国人の検挙人員（公表された国籍区分のまま）',
  },
  {
    id: 'x_cleared_cases_as_published_mismatch',
    label: '全外国人の検挙件数（公表された国籍区分のまま）',
  },
  {
    id: 'y_cleared_persons_as_published_mismatch',
    label: '来日外国人の検挙人員（公表された国籍区分のまま）',
  },
  {
    id: 'y_cleared_cases_as_published_mismatch',
    label: '来日外国人の検挙件数（公表された国籍区分のまま）',
  },
] as const;

export type ContextMetricId = (typeof CONTEXT_METRICS)[number]['id'];
export type NationalityMetricId = (typeof NATIONALITY_METRICS)[number]['id'];
export type NationalityPerspectiveId =
  (typeof NATIONALITY_PERSPECTIVES)[number]['id'];
export type ValueMode = 'ratio' | 'count';
export type OffenseCompositionMetric = 'cleared_persons' | 'cleared_cases';
export type OffenseCompositionOrder = 'cluster' | 'source';
export type ClearanceShareMetric = 'cleared_cases' | 'cleared_persons';

const COMPARISON_SIDE_SIZE = 5;

type JsonObject = Record<string, unknown>;

interface ContextDefinition {
  label_ja: string;
  canonical_formula: string;
  display_multiplier: number;
  display_unit_label_ja: string;
  statistical_compatibility: 'not_established';
  display_kind?: 'same_year_recognition_clearance_gap';
  interpretation_policy?: 'same_year_flow_difference_not_cohort_unresolved';
  ui_caveat?: string;
}

interface IndicatorDefinition {
  label_ja: string;
  canonical_formula: string;
  crosswalk_policy: 'exact' | 'as_published_mismatch';
  display_multiplier: number;
  display_unit_label_ja: string;
  default_ranking_behavior: 'exclude_flagged';
  statistical_compatibility: 'not_established';
  ui_caveat: string;
}

interface NationalityComparisonDefinition {
  label_ja: string;
  canonical_formula: string;
  display_multiplier: number;
  display_unit_label_ja: string;
  default_display_behavior: 'include_all_with_warnings';
  interpretation_policy: 'observed_values_without_intrinsic_group_inference';
  statistical_compatibility: 'not_established';
  ui_caveat: string;
}

interface OffenseClusteringDefinition {
  distance: 'jensen_shannon';
  log_base: 2;
  linkage: 'average';
  input: 'within_entity_composition_share';
  order: string[];
  not_clustered_zero_total_entity_ids: string[];
}

interface OffenseCompositionDefinition {
  label_ja: string;
  label_en: string;
  interpretation_policy: 'patterns_without_intrinsic_group_inference';
  ui_caveat: string;
  category_ids: string[];
  small_number_total_threshold: number;
  clustering: Record<OffenseCompositionMetric, OffenseClusteringDefinition>;
}

interface OffenseCategoryDefinition {
  label_ja: string;
  display_order: number;
  color: string;
  official_severity_role:
    | 'official_high_severity_category'
    | 'not_a_project_severity_classification';
}

interface ClearanceShareDefinition {
  label_ja: string;
  label_en: string;
  interpretation_policy: 'share_of_clearances_not_population_risk';
  ui_caveat: string;
  display_multiplier: 100;
  display_unit_label_ja: '%';
}

interface ContextRow {
  context_id: string;
  geography_label: string;
  geography_id: string;
  geography_type: string;
  numerator_metric: string;
  numerator_source_id: string | null;
  denominator_source_id: string | null;
  numerator_value: number | null;
  denominator_value: number | null;
  display_value: number | null;
  recognized_cases_value?: number | null;
  cleared_cases_value?: number | null;
  calculation_status: 'calculated' | 'refused';
  refusal_reason: string | null;
  mismatch_flags: string[];
  year: number;
  reference_date: string;
}

interface NationalityIndicatorRow {
  indicator_id: string;
  geography_label: string;
  numerator_source_id: string | null;
  denominator_source_id: string | null;
  numerator_metric: string;
  numerator_value: number | null;
  denominator_value: number | null;
  display_value: number | null;
  calculation_status: 'calculated' | 'refused';
  refusal_reason: string | null;
  mismatch_flags: string[];
  small_number_warning_flags: string[];
  default_ranking_excluded: boolean;
  published_label: string;
  numerator_context?: {
    region?: string | null;
    subcategory?: string | null;
    population_scope?: string | null;
    offense_scope?: string | null;
  };
  year: number;
  period_end: string;
}

interface NationalityComparisonRow {
  comparison_id: string;
  entity_id: string;
  published_label: string;
  display_label: string;
  source_order: number;
  is_japanese_reference: boolean;
  year: number;
  denominator_reference_date: string;
  numerator_source_ids: string[];
  denominator_source_id: string;
  numerator_value: number | null;
  denominator_value: number | null;
  display_value: number | null;
  calculation_status: 'calculated' | 'refused';
  refusal_reason: string | null;
  mismatch_flags: string[];
  small_number_warning_flags: string[];
  display_included: boolean;
  derivation_method: string;
  derivation_formula: string;
}

interface OffenseCompositionRow {
  composition_id: string;
  entity_id: string;
  published_label: string;
  display_label: string;
  source_order: number;
  entity_kind: string;
  is_japanese_reference: boolean;
  offense_id: string;
  year: number;
  cleared_cases: number;
  cleared_persons: number;
  criminal_code_cleared_cases_total: number;
  criminal_code_cleared_persons_total: number;
  cleared_cases_share: number | null;
  cleared_persons_share: number | null;
  cleared_cases_share_status: 'calculated' | 'refused_zero_total';
  cleared_persons_share_status: 'calculated' | 'refused_zero_total';
  calculation_status: 'calculated' | 'refused';
  refusal_reason: string | null;
  derivation_method: string;
  derivation_formula: string;
  numerator_source_ids: string[];
  mismatch_flags: string[];
  small_number_warning_flags: string[];
  display_included: boolean;
}

interface ClearanceShareSourceComponent {
  source_id: string;
  role: string;
  metric: ClearanceShareMetric;
  value: number;
  source_table: string;
  source_sheet: string;
  source_row: number;
  source_column: number;
}

interface ClearanceShareRow {
  trend_id: string;
  year: number;
  foreign_scope: ClearanceShareScope;
  foreign_scope_label_ja: string;
  metric: ClearanceShareMetric;
  metric_label_ja: string;
  numerator_value: number;
  denominator_value: number;
  quotient: number;
  display_value: number;
  calculation_status: 'calculated';
  refusal_reason: null;
  numerator_source_id: string;
  numerator_source_ids: string[];
  denominator_source_id: string;
  derivation_method: string;
  derivation_formula: string;
  source_components: ClearanceShareSourceComponent[];
  mismatch_flags: string[];
}

interface PublicSource {
  dataset: string;
  publisher: string;
  source_table: string;
  source_period: string;
  landing_url: string;
  download_url: string;
  retrieved_at: string;
  revision: string;
  sha256: string;
}

export interface DashboardData {
  compact_export_schema_version: 7;
  generated_at: string;
  definitions: {
    context_ids: Record<string, ContextDefinition>;
    indicator_ids: Record<string, IndicatorDefinition>;
    nationality_comparison_ids: Record<string, NationalityComparisonDefinition>;
    offense_composition_ids: Record<string, OffenseCompositionDefinition>;
    offense_category_ids: Record<string, OffenseCategoryDefinition>;
    clearance_share_ids: Record<string, ClearanceShareDefinition>;
  };
  records: {
    all_resident_context: ContextRow[];
    nationality_indicators: NationalityIndicatorRow[];
    nationality_comparison: NationalityComparisonRow[];
    offense_composition: OffenseCompositionRow[];
    clearance_share_trends: ClearanceShareRow[];
  };
  sources: Record<string, PublicSource>;
}

interface DashboardSource {
  id: string;
  publisher: string;
  dataset: string;
  sourceTable: string;
  sourcePeriod: string;
  retrievedAt: string;
  landingUrl: string;
  downloadUrl: string;
  sha256: string;
}

export interface RegionalDatum {
  id: string;
  name: string;
  value: number;
  rawCount: number;
  denominatorValue: number;
  referenceRatio: number;
}

export interface RegionalViewModel {
  metricId: ContextMetricId;
  metricLabel: string;
  mode: ValueMode;
  unitLabel: string;
  ratioUnitLabel: string;
  rawCountLabel: string;
  denominatorLabel: string;
  ratioDetailLabel: string;
  isSameYearGap: boolean;
  uiCaveat: string;
  year: number;
  referenceDate: string;
  formula: string;
  displayMultiplier: number;
  statisticalCompatibility: 'not_established';
  prefectures: RegionalDatum[];
  national: RegionalDatum;
  tokyo: RegionalDatum;
  saitama: RegionalDatum;
  refusedCount: number;
  refusalReasons: Array<{ reason: string; count: number }>;
  warningCodes: string[];
  sources: DashboardSource[];
}

export interface NationalityDatum {
  name: string;
  value: number;
  numerator: number;
  denominator: number;
  referenceRatio: number;
  warningCodes: string[];
}

export interface NationalityViewModel {
  metricId: NationalityMetricId;
  metricLabel: string;
  mode: ValueMode;
  unitLabel: string;
  year: number;
  periodEnd: string;
  geographyLabel: string;
  uiCaveat: string;
  formula: string;
  crosswalkPolicy: 'exact' | 'as_published_mismatch';
  rankingRows: NationalityDatum[];
  excludedRows: NationalityDatum[];
  refusedCount: number;
  refusalReasons: Array<{ reason: string; count: number }>;
  warningCodes: string[];
  mismatchCodes: string[];
  sources: DashboardSource[];
}

export interface NationalityComparisonDatum {
  id: string;
  name: string;
  publishedLabel: string;
  sourceOrder: number;
  isJapaneseReference: boolean;
  year: number;
  value: number | null;
  numerator: number | null;
  denominator: number | null;
  referenceRatio: number | null;
  calculationStatus: 'calculated' | 'refused';
  refusalReason: string | null;
  warningCodes: string[];
  mismatchCodes: string[];
  derivationMethod: string;
  derivationFormula: string;
  numeratorSourceIds: string[];
  denominatorSourceId: string | null;
}

export interface NationalityComparisonViewModel {
  comparisonId: string;
  perspectiveId: NationalityPerspectiveId;
  perspectiveLabel: string;
  perspectiveKind: 'japanese_inclusive_comparison' | 'published_indicator';
  metricLabel: string;
  mode: ValueMode;
  unitLabel: string;
  numeratorLabel: '検挙人員' | '検挙件数';
  rawUnitLabel: '人' | '件';
  scopeLabel: string;
  geographyLabel: string;
  year: number;
  referenceDates: string[];
  formula: string;
  displayMultiplier: number;
  statisticalCompatibility: 'not_established';
  defaultDisplayBehavior: 'include_all_with_warnings';
  interpretationPolicy: 'observed_values_without_intrinsic_group_inference';
  uiCaveat: string;
  rows: NationalityComparisonDatum[];
  calculatedRows: NationalityComparisonDatum[];
  orderedRows: NationalityComparisonDatum[];
  highRows: NationalityComparisonDatum[];
  lowRows: NationalityComparisonDatum[];
  japaneseReference: NationalityComparisonDatum;
  refusedCount: number;
  refusalReasons: Array<{ reason: string; count: number }>;
  warningCodes: string[];
  mismatchCodes: string[];
  sources: DashboardSource[];
}

export interface ClearanceShareTrendPoint {
  year: number;
  allPersonsTotal: number;
  japaneseEtcResidualCount: number;
  japaneseEtcResidualShare: number;
  allForeignCount: number;
  allForeignShare: number;
  visitingForeignCount: number;
  visitingForeignShare: number;
  allForeignMinusVisitingCount: number;
  allForeignMinusVisitingShare: number;
}

export interface ClearanceShareTrendViewModel {
  trendId: typeof CLEARANCE_SHARE_TREND_ID;
  metric: ClearanceShareMetric;
  metricLabel: string;
  unitLabel: '件' | '人';
  label: string;
  years: number[];
  points: ClearanceShareTrendPoint[];
  uiCaveat: string;
  interpretationPolicy: 'share_of_clearances_not_population_risk';
  warningCodes: string[];
  sources: DashboardSource[];
}

export interface OffenseCompositionCategory {
  id: string;
  label: string;
  displayOrder: number;
  color: string;
  officialSeverityRole: OffenseCategoryDefinition['official_severity_role'];
}

export interface OffenseCompositionCell {
  offenseId: string;
  count: number;
  share: number | null;
  shareStatus: 'calculated' | 'refused_zero_total';
}

export interface OffenseCompositionEntity {
  id: string;
  name: string;
  publishedLabel: string;
  sourceOrder: number;
  isJapaneseReference: boolean;
  entityKind: string;
  year: number;
  total: number;
  calculationStatus: 'calculated' | 'refused';
  refusalReason: string | null;
  derivationMethod: string;
  derivationFormula: string;
  numeratorSourceIds: string[];
  mismatchCodes: string[];
  warningCodes: string[];
  cells: OffenseCompositionCell[];
}

export interface OffenseCompositionViewModel {
  compositionId: typeof OFFENSE_COMPOSITION_ID;
  metric: OffenseCompositionMetric;
  metricLabel: '検挙人員' | '検挙件数';
  unitLabel: '人' | '件';
  order: OffenseCompositionOrder;
  year: number;
  label: string;
  interpretationPolicy: 'patterns_without_intrinsic_group_inference';
  uiCaveat: string;
  smallNumberTotalThreshold: number;
  categories: OffenseCompositionCategory[];
  entities: OffenseCompositionEntity[];
  japaneseReference: OffenseCompositionEntity;
  clustering: OffenseClusteringDefinition;
  warningCodes: string[];
  mismatchCodes: string[];
  sources: DashboardSource[];
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function parseDashboardData(value: unknown): DashboardData {
  if (!isObject(value) || value.compact_export_schema_version !== 7) {
    throw new Error('Unsupported compact export schema version.');
  }

  const definitions = value.definitions;
  const records = value.records;
  const sources = value.sources;
  if (
    !isObject(definitions) ||
    !isObject(definitions.context_ids) ||
    !isObject(definitions.indicator_ids) ||
    !isObject(definitions.nationality_comparison_ids) ||
    !isObject(definitions.offense_composition_ids) ||
    !isObject(definitions.offense_category_ids) ||
    !isObject(definitions.clearance_share_ids) ||
    !isObject(records) ||
    !Array.isArray(records.all_resident_context) ||
    !Array.isArray(records.nationality_indicators) ||
    !Array.isArray(records.nationality_comparison) ||
    !Array.isArray(records.offense_composition) ||
    !Array.isArray(records.clearance_share_trends) ||
    !isObject(sources)
  ) {
    throw new Error('Compact export is missing the regional dashboard data.');
  }

  return value as unknown as DashboardData;
}

function collectSources(
  dashboard: DashboardData,
  sourceIds: Iterable<string>,
): DashboardSource[] {
  return [...new Set(sourceIds)].sort().map((id) => {
    const source = dashboard.sources[id];
    if (!source) throw new Error(`Public source metadata is missing: ${id}`);
    return {
      id,
      publisher: source.publisher,
      dataset: source.dataset,
      sourceTable: source.source_table,
      sourcePeriod: source.source_period,
      retrievedAt: source.retrieved_at,
      landingUrl: source.landing_url,
      downloadUrl: source.download_url,
      sha256: source.sha256,
    };
  });
}

function countRefusalReasons(
  rows: Array<{ refusal_reason: string | null }>,
): Array<{ reason: string; count: number }> {
  const counter = new Map<string, number>();
  for (const row of rows) {
    const reason = row.refusal_reason ?? 'reason_not_recorded';
    counter.set(reason, (counter.get(reason) ?? 0) + 1);
  }
  return [...counter.entries()]
    .map(([reason, count]) => ({ reason, count }))
    .sort((left, right) => right.count - left.count);
}

function requireDatum(row: ContextRow, mode: ValueMode): RegionalDatum {
  if (
    row.numerator_value === null ||
    row.denominator_value === null ||
    row.display_value === null
  ) {
    throw new Error(`Calculated row ${row.geography_id} has missing values.`);
  }
  if (row.context_id === SAME_YEAR_GAP_CONTEXT_ID) {
    if (
      row.recognized_cases_value === null ||
      row.recognized_cases_value === undefined ||
      row.cleared_cases_value === null ||
      row.cleared_cases_value === undefined ||
      row.denominator_value !== row.recognized_cases_value ||
      row.numerator_value !==
        row.recognized_cases_value - row.cleared_cases_value
    ) {
      throw new Error(
        `Same-year gap row ${row.geography_id} fails source-count reconciliation.`,
      );
    }
  }

  return {
    id: row.geography_id,
    name: row.geography_label,
    value: mode === 'ratio' ? row.display_value : row.numerator_value,
    rawCount: row.numerator_value,
    denominatorValue: row.denominator_value,
    referenceRatio: row.display_value,
  };
}

function requireNamedDatum(rows: RegionalDatum[], id: string): RegionalDatum {
  const datum = rows.find((candidate) => candidate.id === id);
  if (!datum) {
    throw new Error(`Required regional datum is missing: ${id}`);
  }
  return datum;
}

export function buildRegionalViewModel(
  dashboard: DashboardData,
  metricId: ContextMetricId,
  mode: ValueMode,
): RegionalViewModel {
  const definition = dashboard.definitions.context_ids[metricId];
  if (!definition) {
    throw new Error(`Context definition is missing: ${metricId}`);
  }

  const selectedRows = dashboard.records.all_resident_context.filter(
    (row) => row.context_id === metricId,
  );
  const calculatedRows = selectedRows.filter(
    (row) => row.calculation_status === 'calculated',
  );
  const calculatedData = calculatedRows.map((row) => requireDatum(row, mode));
  const prefectures = calculatedRows
    .filter((row) => row.geography_type === 'prefecture')
    .map((row) => requireDatum(row, mode))
    .sort((left, right) => right.value - left.value);
  const national = requireNamedDatum(calculatedData, 'jp:all');
  const tokyo = requireNamedDatum(calculatedData, 'jp-prefecture:13');
  const saitama = requireNamedDatum(calculatedData, 'jp-prefecture:11');

  const refusedRows = selectedRows.filter(
    (row) => row.calculation_status === 'refused',
  );

  const sourceIds = new Set<string>();
  for (const row of calculatedRows) {
    if (row.numerator_source_id) sourceIds.add(row.numerator_source_id);
    if (row.denominator_source_id) sourceIds.add(row.denominator_source_id);
  }
  const sources = collectSources(dashboard, sourceIds);

  const warningCodes = [
    ...new Set(calculatedRows.flatMap((row) => row.mismatch_flags)),
  ].sort();
  const firstRow = calculatedRows[0];
  if (!firstRow) throw new Error(`No calculated rows exist for ${metricId}`);
  const isPersonMetric = firstRow.numerator_metric === 'cleared_persons';
  const isSameYearGap = metricId === SAME_YEAR_GAP_CONTEXT_ID;
  if (
    isSameYearGap &&
    (definition.display_kind !== 'same_year_recognition_clearance_gap' ||
      definition.interpretation_policy !==
        'same_year_flow_difference_not_cohort_unresolved' ||
      !definition.ui_caveat)
  ) {
    throw new Error('Same-year gap interpretation contract is incomplete.');
  }

  return {
    metricId,
    metricLabel:
      CONTEXT_METRICS.find((metric) => metric.id === metricId)?.label ??
      definition.label_ja,
    mode,
    unitLabel:
      mode === 'ratio'
        ? definition.display_unit_label_ja
        : isPersonMetric
          ? '人'
          : '件',
    ratioUnitLabel: definition.display_unit_label_ja,
    rawCountLabel: isSameYearGap
      ? '同年差分件数'
      : isPersonMetric
        ? '人員'
        : '件数',
    denominatorLabel: isSameYearGap ? '認知件数' : '人口',
    ratioDetailLabel: isSameYearGap ? '同年差分率' : '参考比率',
    isSameYearGap,
    uiCaveat: definition.ui_caveat ?? '',
    year: firstRow.year,
    referenceDate: firstRow.reference_date,
    formula: definition.canonical_formula,
    displayMultiplier: definition.display_multiplier,
    statisticalCompatibility: definition.statistical_compatibility,
    prefectures,
    national,
    tokyo,
    saitama,
    refusedCount: refusedRows.length,
    refusalReasons: countRefusalReasons(refusedRows),
    warningCodes,
    sources,
  };
}

function requireNationalityDatum(
  row: NationalityIndicatorRow,
  mode: ValueMode,
): NationalityDatum {
  if (
    row.numerator_value === null ||
    row.denominator_value === null ||
    row.display_value === null
  ) {
    throw new Error(
      `Calculated nationality row ${row.published_label} has missing values.`,
    );
  }
  return {
    name: row.published_label,
    value: mode === 'ratio' ? row.display_value : row.numerator_value,
    numerator: row.numerator_value,
    denominator: row.denominator_value,
    referenceRatio: row.display_value,
    warningCodes: row.small_number_warning_flags,
  };
}

export function buildNationalityViewModel(
  dashboard: DashboardData,
  metricId: NationalityMetricId,
  mode: ValueMode,
): NationalityViewModel {
  const definition = dashboard.definitions.indicator_ids[metricId];
  if (!definition) {
    throw new Error(`Indicator definition is missing: ${metricId}`);
  }
  const selectedRows = dashboard.records.nationality_indicators.filter(
    (row) => row.indicator_id === metricId,
  );
  const calculatedRows = selectedRows.filter(
    (row) => row.calculation_status === 'calculated',
  );
  const refusedRows = selectedRows.filter(
    (row) => row.calculation_status === 'refused',
  );
  const firstRow = calculatedRows[0];
  if (!firstRow) throw new Error(`No calculated rows exist for ${metricId}`);

  const rankedRows = calculatedRows
    .filter((row) => !row.default_ranking_excluded)
    .map((row) => requireNationalityDatum(row, mode))
    .sort((left, right) => right.value - left.value);
  const excludedRows = calculatedRows
    .filter((row) => row.default_ranking_excluded)
    .map((row) => requireNationalityDatum(row, mode))
    .sort((left, right) => right.value - left.value);

  const sourceIds = new Set<string>();
  for (const row of selectedRows) {
    if (row.numerator_source_id) sourceIds.add(row.numerator_source_id);
    if (row.denominator_source_id) sourceIds.add(row.denominator_source_id);
  }

  return {
    metricId,
    metricLabel:
      NATIONALITY_METRICS.find((metric) => metric.id === metricId)?.label ??
      definition.label_ja,
    mode,
    unitLabel:
      mode === 'ratio'
        ? definition.display_unit_label_ja
        : firstRow.numerator_metric === 'cleared_persons'
          ? '人'
          : '件',
    year: firstRow.year,
    periodEnd: firstRow.period_end,
    geographyLabel: firstRow.geography_label,
    uiCaveat: definition.ui_caveat,
    formula: definition.canonical_formula,
    crosswalkPolicy: definition.crosswalk_policy,
    rankingRows: rankedRows,
    excludedRows,
    refusedCount: refusedRows.length,
    refusalReasons: countRefusalReasons(refusedRows),
    warningCodes: [
      ...new Set(
        calculatedRows.flatMap((row) => row.small_number_warning_flags),
      ),
    ].sort(),
    mismatchCodes: [
      ...new Set(calculatedRows.flatMap((row) => row.mismatch_flags)),
    ].sort(),
    sources: collectSources(dashboard, sourceIds),
  };
}

function requireNationalityComparisonDatum(
  row: NationalityComparisonRow,
  mode: ValueMode,
): NationalityComparisonDatum {
  if (row.numerator_value === null) {
    throw new Error(
      `Nationality comparison row ${row.display_label} has missing values.`,
    );
  }
  if (
    row.calculation_status === 'calculated' &&
    (row.denominator_value === null || row.display_value === null)
  ) {
    throw new Error(
      `Nationality comparison row ${row.display_label} has missing values.`,
    );
  }
  return {
    id: row.entity_id,
    name: row.display_label,
    publishedLabel: row.published_label,
    sourceOrder: row.source_order,
    isJapaneseReference: row.is_japanese_reference,
    year: row.year,
    value: mode === 'ratio' ? row.display_value : row.numerator_value,
    numerator: row.numerator_value,
    denominator: row.denominator_value,
    referenceRatio: row.display_value,
    calculationStatus: row.calculation_status,
    refusalReason: row.refusal_reason,
    warningCodes: [...row.small_number_warning_flags],
    mismatchCodes: [...row.mismatch_flags],
    derivationMethod: row.derivation_method,
    derivationFormula: row.derivation_formula,
    numeratorSourceIds: [...row.numerator_source_ids],
    denominatorSourceId: row.denominator_source_id,
  };
}

function nationalityPerspectiveLabel(
  perspectiveId: NationalityPerspectiveId,
): string {
  const perspective = NATIONALITY_PERSPECTIVES.find(
    (candidate) => candidate.id === perspectiveId,
  );
  if (!perspective) {
    throw new Error(`Nationality perspective is missing: ${perspectiveId}`);
  }
  return perspective.label;
}

function selectNationalitySides(rows: NationalityComparisonDatum[]): {
  highRows: NationalityComparisonDatum[];
  lowRows: NationalityComparisonDatum[];
} {
  const displayableRows = rows.filter((row) => row.value !== null);
  const descending = (
    left: NationalityComparisonDatum,
    right: NationalityComparisonDatum,
  ) =>
    (right.value ?? Number.NEGATIVE_INFINITY) -
      (left.value ?? Number.NEGATIVE_INFINITY) ||
    left.sourceOrder - right.sourceOrder;
  const ascending = (
    left: NationalityComparisonDatum,
    right: NationalityComparisonDatum,
  ) =>
    (left.value ?? Number.POSITIVE_INFINITY) -
      (right.value ?? Number.POSITIVE_INFINITY) ||
    left.sourceOrder - right.sourceOrder;
  return {
    highRows: [...displayableRows]
      .sort(descending)
      .slice(0, COMPARISON_SIDE_SIZE),
    lowRows: [...displayableRows]
      .sort(ascending)
      .slice(0, COMPARISON_SIDE_SIZE),
  };
}

function orderNationalityReferenceRatios(
  rows: NationalityComparisonDatum[],
): NationalityComparisonDatum[] {
  return [...rows].sort((left, right) => {
    if (left.referenceRatio === null && right.referenceRatio === null) {
      return (
        left.sourceOrder - right.sourceOrder ||
        left.name.localeCompare(right.name, 'ja')
      );
    }
    if (left.referenceRatio === null) return 1;
    if (right.referenceRatio === null) return -1;
    return (
      right.referenceRatio - left.referenceRatio ||
      left.sourceOrder - right.sourceOrder ||
      left.name.localeCompare(right.name, 'ja')
    );
  });
}

function countComparisonRefusalReasons(
  rows: NationalityComparisonDatum[],
): Array<{ reason: string; count: number }> {
  return countRefusalReasons(
    rows
      .filter((row) => row.calculationStatus === 'refused')
      .map((row) => ({ refusal_reason: row.refusalReason })),
  );
}

export function buildNationalityComparisonViewModel(
  dashboard: DashboardData,
  mode: ValueMode = 'ratio',
): NationalityComparisonViewModel {
  const definition =
    dashboard.definitions.nationality_comparison_ids[NATIONALITY_COMPARISON_ID];
  if (!definition) {
    throw new Error(
      `Nationality comparison definition is missing: ${NATIONALITY_COMPARISON_ID}`,
    );
  }

  const selectedRows = dashboard.records.nationality_comparison.filter(
    (row) => row.comparison_id === NATIONALITY_COMPARISON_ID,
  );
  if (selectedRows.length === 0) {
    throw new Error('No nationality comparison rows exist.');
  }
  const rows = selectedRows
    .map((row) => requireNationalityComparisonDatum(row, mode))
    .sort((left, right) => left.sourceOrder - right.sourceOrder);
  const calculatedRows = rows.filter(
    (row) => row.calculationStatus === 'calculated',
  );
  const { highRows, lowRows } = selectNationalitySides(rows);
  const japaneseRows = rows.filter((row) => row.isJapaneseReference);
  if (japaneseRows.length !== 1) {
    throw new Error(
      `Expected exactly one Japanese reference row, received ${japaneseRows.length}.`,
    );
  }

  const sourceIds = new Set<string>();
  for (const row of selectedRows) {
    for (const sourceId of row.numerator_source_ids) sourceIds.add(sourceId);
    if (row.denominator_source_id) sourceIds.add(row.denominator_source_id);
  }
  const firstRow = selectedRows[0];

  return {
    comparisonId: NATIONALITY_COMPARISON_ID,
    perspectiveId: NATIONALITY_COMPARISON_ID,
    perspectiveLabel: nationalityPerspectiveLabel(NATIONALITY_COMPARISON_ID),
    perspectiveKind: 'japanese_inclusive_comparison',
    metricLabel: definition.label_ja,
    mode,
    unitLabel: mode === 'ratio' ? definition.display_unit_label_ja : '人',
    numeratorLabel: '検挙人員',
    rawUnitLabel: '人',
    scopeLabel: '刑法犯の検挙人員／外国人は公表値、日本は差し引きによる参考値',
    geographyLabel: '日本全国',
    year: firstRow.year,
    referenceDates: [
      ...new Set(selectedRows.map((row) => row.denominator_reference_date)),
    ].sort(),
    formula: definition.canonical_formula,
    displayMultiplier: definition.display_multiplier,
    statisticalCompatibility: definition.statistical_compatibility,
    defaultDisplayBehavior: definition.default_display_behavior,
    interpretationPolicy: definition.interpretation_policy,
    uiCaveat: definition.ui_caveat,
    rows,
    calculatedRows,
    orderedRows: orderNationalityReferenceRatios(rows),
    highRows,
    lowRows,
    japaneseReference: japaneseRows[0],
    refusedCount: rows.filter((row) => row.calculationStatus === 'refused')
      .length,
    refusalReasons: countComparisonRefusalReasons(rows),
    warningCodes: [
      ...new Set(selectedRows.flatMap((row) => row.small_number_warning_flags)),
    ].sort(),
    mismatchCodes: [
      ...new Set(selectedRows.flatMap((row) => row.mismatch_flags)),
    ].sort(),
    sources: collectSources(dashboard, sourceIds),
  };
}

function nationalityComparisonEntityKey(value: {
  sourceOrder: number;
  publishedLabel: string;
  isJapaneseReference: boolean;
}): string {
  return `${value.sourceOrder}:${value.publishedLabel}:${value.isJapaneseReference}`;
}

function buildNationalityCasesComparisonViewModel(
  dashboard: DashboardData,
  mode: ValueMode,
): NationalityComparisonViewModel {
  const definition =
    dashboard.definitions.nationality_comparison_ids[NATIONALITY_COMPARISON_ID];
  if (!definition) {
    throw new Error(
      `Nationality comparison definition is missing: ${NATIONALITY_COMPARISON_ID}`,
    );
  }
  const denominatorRows = dashboard.records.nationality_comparison.filter(
    (row) => row.comparison_id === NATIONALITY_COMPARISON_ID,
  );
  if (denominatorRows.length === 0) {
    throw new Error('No nationality comparison denominator rows exist.');
  }

  const offenseView = buildOffenseCompositionViewModel(
    dashboard,
    'cleared_cases',
    'source',
  );
  const offenseByKey = new Map<string, OffenseCompositionEntity>();
  for (const entity of offenseView.entities) {
    const key = nationalityComparisonEntityKey(entity);
    if (offenseByKey.has(key)) {
      throw new Error(`Duplicate cleared-case comparison entity: ${key}`);
    }
    offenseByKey.set(key, entity);
  }

  const rows = denominatorRows
    .map((row): NationalityComparisonDatum => {
      const key = nationalityComparisonEntityKey({
        sourceOrder: row.source_order,
        publishedLabel: row.published_label,
        isJapaneseReference: row.is_japanese_reference,
      });
      const entity = offenseByKey.get(key);
      if (!entity) {
        throw new Error(`Cleared-case comparison entity is missing: ${key}`);
      }
      if (entity.year !== row.year) {
        throw new Error(`Cleared-case comparison year conflicts for ${key}`);
      }
      if (
        row.calculation_status === 'calculated' &&
        row.denominator_value === null
      ) {
        throw new Error(
          `Cleared-case comparison denominator is missing: ${key}`,
        );
      }
      const referenceRatio =
        row.calculation_status === 'calculated' &&
        row.denominator_value !== null
          ? (entity.total / row.denominator_value) *
            definition.display_multiplier
          : null;
      return {
        id: `${NATIONALITY_CASES_COMPARISON_ID}:${entity.id}`,
        name: entity.name,
        publishedLabel: entity.publishedLabel,
        sourceOrder: entity.sourceOrder,
        isJapaneseReference: entity.isJapaneseReference,
        year: entity.year,
        value: mode === 'ratio' ? referenceRatio : entity.total,
        numerator: entity.total,
        denominator: row.denominator_value,
        referenceRatio,
        calculationStatus: row.calculation_status,
        refusalReason: row.refusal_reason,
        warningCodes: [
          ...new Set([
            ...row.small_number_warning_flags.filter(
              (warning) => warning !== 'sparse_numerator_count',
            ),
            ...entity.warningCodes.filter(
              (warning) => warning !== 'sparse_entity_total_cleared_persons',
            ),
          ]),
        ].sort(),
        mismatchCodes: [
          ...new Set([...row.mismatch_flags, ...entity.mismatchCodes]),
        ].sort(),
        derivationMethod: entity.derivationMethod,
        derivationFormula: entity.derivationFormula,
        numeratorSourceIds: [...entity.numeratorSourceIds],
        denominatorSourceId: row.denominator_source_id,
      };
    })
    .sort((left, right) => left.sourceOrder - right.sourceOrder);
  if (offenseByKey.size !== rows.length) {
    throw new Error('Cleared-case and population comparison entities differ.');
  }

  const calculatedRows = rows.filter(
    (row) => row.calculationStatus === 'calculated',
  );
  const { highRows, lowRows } = selectNationalitySides(rows);
  const japaneseRows = rows.filter((row) => row.isJapaneseReference);
  if (japaneseRows.length !== 1) {
    throw new Error(
      `Expected exactly one Japanese cleared-case row, received ${japaneseRows.length}.`,
    );
  }
  const sourceIds = new Set<string>();
  for (const row of rows) {
    for (const sourceId of row.numeratorSourceIds) sourceIds.add(sourceId);
    if (row.denominatorSourceId) sourceIds.add(row.denominatorSourceId);
  }

  return {
    comparisonId: NATIONALITY_CASES_COMPARISON_ID,
    perspectiveId: NATIONALITY_CASES_COMPARISON_ID,
    perspectiveLabel: nationalityPerspectiveLabel(
      NATIONALITY_CASES_COMPARISON_ID,
    ),
    perspectiveKind: 'japanese_inclusive_comparison',
    metricLabel: '全国・国籍等別 刑法犯検挙件数 ÷ 対応人口',
    mode,
    unitLabel: mode === 'ratio' ? definition.display_unit_label_ja : '件',
    numeratorLabel: '検挙件数',
    rawUnitLabel: '件',
    scopeLabel: '刑法犯の検挙件数／外国人は公表値、日本は差し引きによる参考値',
    geographyLabel: '日本全国',
    year: denominatorRows[0].year,
    referenceDates: [
      ...new Set(denominatorRows.map((row) => row.denominator_reference_date)),
    ].sort(),
    formula: definition.canonical_formula,
    displayMultiplier: definition.display_multiplier,
    statisticalCompatibility: definition.statistical_compatibility,
    defaultDisplayBehavior: definition.default_display_behavior,
    interpretationPolicy: definition.interpretation_policy,
    uiCaveat:
      '公表された刑法犯検挙件数と対応人口を機械的に組み合わせた参考比率。日本は全件数から全外国人の件数を差し引いた残差による参考値であり、集団の本質、因果、個人riskを示さない。',
    rows,
    calculatedRows,
    orderedRows: orderNationalityReferenceRatios(rows),
    highRows,
    lowRows,
    japaneseReference: japaneseRows[0],
    refusedCount: rows.filter((row) => row.calculationStatus === 'refused')
      .length,
    refusalReasons: countComparisonRefusalReasons(rows),
    warningCodes: [...new Set(rows.flatMap((row) => row.warningCodes))].sort(),
    mismatchCodes: [
      ...new Set(rows.flatMap((row) => row.mismatchCodes)),
    ].sort(),
    sources: collectSources(dashboard, sourceIds),
  };
}

function legacyNationalityName(
  row: NationalityIndicatorRow,
  duplicateLabels: ReadonlyMap<string, number>,
): string {
  const region = row.numerator_context?.region;
  if ((duplicateLabels.get(row.published_label) ?? 0) > 1 && region) {
    return `${row.published_label}（${region}）`;
  }
  return row.published_label;
}

function buildPublishedIndicatorComparisonViewModel(
  dashboard: DashboardData,
  metricId: NationalityMetricId,
  mode: ValueMode,
): NationalityComparisonViewModel {
  const definition = dashboard.definitions.indicator_ids[metricId];
  if (!definition) {
    throw new Error(`Indicator definition is missing: ${metricId}`);
  }
  const selectedRows = dashboard.records.nationality_indicators.filter(
    (row) => row.indicator_id === metricId,
  );
  if (selectedRows.length === 0) {
    throw new Error(`No nationality indicator rows exist for ${metricId}`);
  }

  const japaneseAnchors = dashboard.records.nationality_comparison.filter(
    (row) =>
      row.comparison_id === NATIONALITY_COMPARISON_ID &&
      row.is_japanese_reference,
  );
  if (
    japaneseAnchors.length !== 1 ||
    japaneseAnchors[0].denominator_value === null
  ) {
    throw new Error(
      `Expected one Japanese population anchor, received ${japaneseAnchors.length}.`,
    );
  }
  const japaneseAnchor = japaneseAnchors[0];

  const duplicateLabels = new Map<string, number>();
  for (const row of selectedRows) {
    duplicateLabels.set(
      row.published_label,
      (duplicateLabels.get(row.published_label) ?? 0) + 1,
    );
  }

  const publishedRows = selectedRows.map(
    (row, index): NationalityComparisonDatum => {
      if (
        row.calculation_status === 'calculated' &&
        (row.numerator_value === null ||
          row.denominator_value === null ||
          row.display_value === null)
      ) {
        throw new Error(
          `Calculated nationality row ${row.published_label} has missing values.`,
        );
      }
      return {
        id: `${metricId}:${index}:${row.published_label}`,
        name: legacyNationalityName(row, duplicateLabels),
        publishedLabel: row.published_label,
        sourceOrder: index + 1,
        isJapaneseReference: false,
        year: row.year,
        value: mode === 'ratio' ? row.display_value : row.numerator_value,
        numerator: row.numerator_value,
        denominator: row.denominator_value,
        referenceRatio: row.display_value,
        calculationStatus: row.calculation_status,
        refusalReason: row.refusal_reason,
        warningCodes: [...row.small_number_warning_flags],
        mismatchCodes: [...row.mismatch_flags],
        derivationMethod: 'published_source_observation',
        derivationFormula: `${row.numerator_source_id}.published_${row.numerator_metric}`,
        numeratorSourceIds: row.numerator_source_id
          ? [row.numerator_source_id]
          : [],
        denominatorSourceId: row.denominator_source_id,
      };
    },
  );

  const japaneseReference: NationalityComparisonDatum = {
    id: `${metricId}:japanese-reference-unavailable`,
    name: '日本（対応する公表分子なし）',
    publishedLabel: '日本',
    sourceOrder: 0,
    isJapaneseReference: true,
    year: selectedRows[0].year,
    value: null,
    numerator: null,
    denominator: japaneseAnchor.denominator_value,
    referenceRatio: null,
    calculationStatus: 'refused',
    refusalReason: 'compatible_japanese_numerator_not_available',
    warningCodes: [],
    mismatchCodes: [
      'japanese_numerator_scope_not_available_for_selected_perspective',
    ],
    derivationMethod: 'not_derived',
    derivationFormula: '対応する日本国籍分子なし（推計しない）',
    numeratorSourceIds: [],
    denominatorSourceId: japaneseAnchor.denominator_source_id,
  };
  const rows = [japaneseReference, ...publishedRows];
  const calculatedRows = rows.filter(
    (row) => row.calculationStatus === 'calculated',
  );
  const { highRows, lowRows } = selectNationalitySides(rows);
  const firstRow = selectedRows[0];
  const isPersonMetric = firstRow.numerator_metric === 'cleared_persons';
  const populationScope = metricId.startsWith('x_') ? '全外国人' : '来日外国人';
  const crosswalkLabel =
    definition.crosswalk_policy === 'exact'
      ? '同じ国籍区分で人口と対応'
      : '公表された国籍区分のまま人口と対応';

  const sourceIds = new Set<string>([japaneseAnchor.denominator_source_id]);
  for (const row of selectedRows) {
    if (row.numerator_source_id) sourceIds.add(row.numerator_source_id);
    if (row.denominator_source_id) sourceIds.add(row.denominator_source_id);
  }

  return {
    comparisonId: metricId,
    perspectiveId: metricId,
    perspectiveLabel: nationalityPerspectiveLabel(metricId),
    perspectiveKind: 'published_indicator',
    metricLabel: definition.label_ja,
    mode,
    unitLabel:
      mode === 'ratio'
        ? definition.display_unit_label_ja
        : isPersonMetric
          ? '人'
          : '件',
    numeratorLabel: isPersonMetric ? '検挙人員' : '検挙件数',
    rawUnitLabel: isPersonMetric ? '人' : '件',
    scopeLabel: `刑法犯と特別法犯の合計／${populationScope}／${crosswalkLabel}`,
    geographyLabel: firstRow.geography_label,
    year: firstRow.year,
    referenceDates: [
      ...new Set([
        ...selectedRows.map((row) => row.period_end),
        japaneseAnchor.denominator_reference_date,
      ]),
    ].sort(),
    formula: definition.canonical_formula,
    displayMultiplier: definition.display_multiplier,
    statisticalCompatibility: definition.statistical_compatibility,
    defaultDisplayBehavior: 'include_all_with_warnings',
    interpretationPolicy: 'observed_values_without_intrinsic_group_inference',
    uiCaveat: `${definition.ui_caveat} 対応する日本国籍分子は推計せず、未算出として表示する。`,
    rows,
    calculatedRows,
    orderedRows: orderNationalityReferenceRatios(rows),
    highRows,
    lowRows,
    japaneseReference,
    refusedCount: rows.filter((row) => row.calculationStatus === 'refused')
      .length,
    refusalReasons: countComparisonRefusalReasons(rows),
    warningCodes: [...new Set(rows.flatMap((row) => row.warningCodes))].sort(),
    mismatchCodes: [
      ...new Set(rows.flatMap((row) => row.mismatchCodes)),
    ].sort(),
    sources: collectSources(dashboard, sourceIds),
  };
}

export function buildSelectableNationalityViewModel(
  dashboard: DashboardData,
  perspectiveId: NationalityPerspectiveId,
  mode: ValueMode,
): NationalityComparisonViewModel {
  if (perspectiveId === NATIONALITY_COMPARISON_ID) {
    return buildNationalityComparisonViewModel(dashboard, mode);
  }
  if (perspectiveId === NATIONALITY_CASES_COMPARISON_ID) {
    return buildNationalityCasesComparisonViewModel(dashboard, mode);
  }
  return buildPublishedIndicatorComparisonViewModel(
    dashboard,
    perspectiveId,
    mode,
  );
}

function clearanceShareSemanticError(detail: string): never {
  throw new Error(`Clearance-share semantic contract: ${detail}.`);
}

function stringArraysEqual(
  actual: string[],
  expected: readonly string[],
): boolean {
  return (
    actual.length === expected.length &&
    actual.every((value, index) => value === expected[index])
  );
}

function validateClearanceShareComponents(
  row: ClearanceShareRow,
  expected: ReadonlyArray<
    readonly [
      string,
      string,
      ClearanceShareMetric,
      number,
      string,
      string,
      number,
      number,
    ]
  >,
): void {
  const components: unknown = row.source_components;
  if (
    !Array.isArray(components) ||
    components.some((component) => !isObject(component))
  ) {
    clearanceShareSemanticError('source_components must be an object array');
  }
  const actual = components.map((component) => [
    component.source_id,
    component.role,
    component.metric,
    component.value,
    component.source_table,
    component.source_sheet,
    component.source_row,
    component.source_column,
  ]);
  if (
    actual.length !== expected.length ||
    actual.some(
      (component, index) =>
        component.length !== expected[index].length ||
        component.some((value, part) => value !== expected[index][part]),
    )
  ) {
    clearanceShareSemanticError(
      'source_components do not match the bound scope inputs',
    );
  }
}

function requireClearanceShareRow(
  row: ClearanceShareRow,
  definition: ClearanceShareDefinition,
): void {
  const scopeContract = CLEARANCE_SHARE_SCOPE_CONTRACTS[row.foreign_scope];
  if (
    !scopeContract ||
    row.foreign_scope_label_ja !== scopeContract.label ||
    row.numerator_source_id !== scopeContract.numeratorSourceId ||
    row.denominator_source_id !== 'S15' ||
    row.derivation_method !== scopeContract.derivationMethod ||
    row.metric_label_ja !==
      (row.metric === 'cleared_cases' ? '検挙件数' : '検挙人員') ||
    !Array.isArray(row.numerator_source_ids) ||
    !stringArraysEqual(
      row.numerator_source_ids,
      scopeContract.numeratorSourceIds,
    ) ||
    !Array.isArray(row.mismatch_flags) ||
    !scopeContract.requiredFlags.every((flag) =>
      row.mismatch_flags.includes(flag),
    )
  ) {
    clearanceShareSemanticError(
      `scope, source, label, or warning binding differs for ${row.metric}/${row.foreign_scope}/${row.year}`,
    );
  }
  if (
    row.calculation_status !== 'calculated' ||
    row.refusal_reason !== null ||
    !Number.isSafeInteger(row.numerator_value) ||
    !Number.isSafeInteger(row.denominator_value) ||
    row.numerator_value < 0 ||
    row.denominator_value <= 0 ||
    row.numerator_value > row.denominator_value ||
    !Array.isArray(row.numerator_source_ids) ||
    row.numerator_source_ids.length === 0 ||
    row.numerator_source_ids.some(
      (sourceId) => typeof sourceId !== 'string' || sourceId.length === 0,
    )
  ) {
    throw new Error(
      `Invalid clearance-share counts for ${row.metric}/${row.foreign_scope}/${row.year}.`,
    );
  }
  const expectedQuotient = row.numerator_value / row.denominator_value;
  const expectedDisplay = expectedQuotient * definition.display_multiplier;
  if (
    Math.abs(row.quotient - expectedQuotient) > 1e-12 ||
    Math.abs(row.display_value - expectedDisplay) > 1e-10
  ) {
    throw new Error(
      `Clearance-share arithmetic conflicts for ${row.metric}/${row.foreign_scope}/${row.year}.`,
    );
  }
  const expectedFormula =
    row.foreign_scope === 'all_foreign_minus_visiting_foreign'
      ? `(S08.${row.metric} - S09.${row.metric}) / S15.${row.metric}`
      : `${scopeContract.numeratorSourceId}.${row.metric} / S15.${row.metric}`;
  if (row.derivation_formula !== expectedFormula) {
    clearanceShareSemanticError(
      `derivation formula differs for ${row.metric}/${row.foreign_scope}/${row.year}`,
    );
  }
}

export function buildClearanceShareTrendViewModel(
  dashboard: DashboardData,
  metric: ClearanceShareMetric = 'cleared_cases',
): ClearanceShareTrendViewModel {
  const definition =
    dashboard.definitions.clearance_share_ids[CLEARANCE_SHARE_TREND_ID];
  if (!definition) {
    throw new Error(
      `Clearance-share definition is missing: ${CLEARANCE_SHARE_TREND_ID}`,
    );
  }
  if (
    definition.label_ja !== CLEARANCE_SHARE_LABEL_JA ||
    definition.interpretation_policy !==
      CLEARANCE_SHARE_INTERPRETATION_POLICY ||
    definition.ui_caveat !== CLEARANCE_SHARE_UI_CAVEAT ||
    definition.display_multiplier !== 100 ||
    definition.display_unit_label_ja !== '%'
  ) {
    clearanceShareSemanticError('definition binding differs');
  }
  const selectedRows = dashboard.records.clearance_share_trends.filter(
    (row) => row.trend_id === CLEARANCE_SHARE_TREND_ID && row.metric === metric,
  );
  if (selectedRows.length === 0) {
    throw new Error(`No clearance-share rows exist for ${metric}.`);
  }

  const rowsByYear = new Map<number, Map<string, ClearanceShareRow>>();
  for (const row of selectedRows) {
    requireClearanceShareRow(row, definition);
    const scopeRows = rowsByYear.get(row.year) ?? new Map();
    if (scopeRows.has(row.foreign_scope)) {
      throw new Error(
        `Duplicate clearance-share row for ${metric}/${row.foreign_scope}/${row.year}.`,
      );
    }
    scopeRows.set(row.foreign_scope, row);
    rowsByYear.set(row.year, scopeRows);
  }

  const years = [...rowsByYear.keys()].sort((left, right) => left - right);
  const points = years.map((year): ClearanceShareTrendPoint => {
    const scopeRows = rowsByYear.get(year);
    const allForeign = scopeRows?.get('all_foreign');
    const visitingForeign = scopeRows?.get('visiting_foreign');
    const allForeignMinusVisiting = scopeRows?.get(
      'all_foreign_minus_visiting_foreign',
    );
    if (
      !allForeign ||
      !visitingForeign ||
      !allForeignMinusVisiting ||
      scopeRows?.size !== 3
    ) {
      throw new Error(
        `Clearance-share scopes are incomplete for ${metric}/${year}.`,
      );
    }
    if (
      allForeign.denominator_value !== visitingForeign.denominator_value ||
      allForeign.denominator_value !==
        allForeignMinusVisiting.denominator_value ||
      allForeign.denominator_source_id !==
        visitingForeign.denominator_source_id ||
      allForeign.denominator_source_id !==
        allForeignMinusVisiting.denominator_source_id
    ) {
      throw new Error(
        `Clearance-share denominators conflict for ${metric}/${year}.`,
      );
    }
    if (visitingForeign.numerator_value > allForeign.numerator_value) {
      throw new Error(
        `Visiting-foreign clearances exceed all-foreign clearances for ${metric}/${year}.`,
      );
    }
    const expectedResidual =
      allForeign.numerator_value - visitingForeign.numerator_value;
    if (
      allForeignMinusVisiting.numerator_value !== expectedResidual ||
      allForeignMinusVisiting.derivation_method !==
        'arithmetic_residual_all_foreign_minus_visiting_foreign' ||
      allForeignMinusVisiting.numerator_source_ids.join('|') !==
        [
          allForeign.numerator_source_id,
          visitingForeign.numerator_source_id,
        ].join('|')
    ) {
      throw new Error(
        `All-foreign minus visiting-foreign residual conflicts for ${metric}/${year}.`,
      );
    }
    validateClearanceShareComponents(allForeign, [
      [
        'S08',
        'numerator',
        metric,
        allForeign.numerator_value,
        '130',
        '01',
        year - 2007,
        metric === 'cleared_cases' ? 7 : 8,
      ],
      [
        'S15',
        'denominator',
        metric,
        allForeign.denominator_value,
        '3',
        '刑法犯総数',
        year - 2006,
        metric === 'cleared_cases' ? 5 : 6,
      ],
    ]);
    validateClearanceShareComponents(visitingForeign, [
      [
        'S09',
        'numerator',
        metric,
        visitingForeign.numerator_value,
        '131',
        '01',
        year - 2007,
        metric === 'cleared_cases' ? 6 : 7,
      ],
      [
        'S15',
        'denominator',
        metric,
        visitingForeign.denominator_value,
        '3',
        '刑法犯総数',
        year - 2006,
        metric === 'cleared_cases' ? 5 : 6,
      ],
    ]);
    validateClearanceShareComponents(allForeignMinusVisiting, [
      [
        'S08',
        'numerator_minuend',
        metric,
        allForeign.numerator_value,
        '130',
        '01',
        year - 2007,
        metric === 'cleared_cases' ? 7 : 8,
      ],
      [
        'S09',
        'numerator_subtrahend',
        metric,
        visitingForeign.numerator_value,
        '131',
        '01',
        year - 2007,
        metric === 'cleared_cases' ? 6 : 7,
      ],
      [
        'S15',
        'denominator',
        metric,
        allForeignMinusVisiting.denominator_value,
        '3',
        '刑法犯総数',
        year - 2006,
        metric === 'cleared_cases' ? 5 : 6,
      ],
    ]);
    return {
      year,
      allPersonsTotal: allForeign.denominator_value,
      japaneseEtcResidualCount:
        allForeign.denominator_value - allForeign.numerator_value,
      japaneseEtcResidualShare: 100 - allForeign.display_value,
      allForeignCount: allForeign.numerator_value,
      allForeignShare: allForeign.display_value,
      visitingForeignCount: visitingForeign.numerator_value,
      visitingForeignShare: visitingForeign.display_value,
      allForeignMinusVisitingCount: allForeignMinusVisiting.numerator_value,
      allForeignMinusVisitingShare: allForeignMinusVisiting.display_value,
    };
  });

  const sourceIds = selectedRows.flatMap((row) => [
    ...row.numerator_source_ids,
    row.denominator_source_id,
  ]);
  return {
    trendId: CLEARANCE_SHARE_TREND_ID,
    metric,
    metricLabel: selectedRows[0].metric_label_ja,
    unitLabel: metric === 'cleared_cases' ? '件' : '人',
    label: definition.label_ja,
    years,
    points,
    uiCaveat: definition.ui_caveat,
    interpretationPolicy: definition.interpretation_policy,
    warningCodes: [
      ...new Set(selectedRows.flatMap((row) => row.mismatch_flags)),
    ].sort(),
    sources: collectSources(dashboard, sourceIds),
  };
}

function requireOffenseEntity(
  rows: OffenseCompositionRow[],
  categories: OffenseCompositionCategory[],
  metric: OffenseCompositionMetric,
): OffenseCompositionEntity {
  const first = rows[0];
  if (!first) throw new Error('Offense composition entity has no rows.');
  const byOffense = new Map(rows.map((row) => [row.offense_id, row]));
  if (
    rows.length !== categories.length ||
    categories.some((category) => !byOffense.has(category.id))
  ) {
    throw new Error(
      `Offense categories are incomplete for ${first.entity_id}.`,
    );
  }
  const totalField =
    metric === 'cleared_persons'
      ? 'criminal_code_cleared_persons_total'
      : 'criminal_code_cleared_cases_total';
  const countField =
    metric === 'cleared_persons' ? 'cleared_persons' : 'cleared_cases';
  const shareField =
    metric === 'cleared_persons'
      ? 'cleared_persons_share'
      : 'cleared_cases_share';
  const statusField =
    metric === 'cleared_persons'
      ? 'cleared_persons_share_status'
      : 'cleared_cases_share_status';
  const total = first[totalField];
  const cells = categories.map((category): OffenseCompositionCell => {
    const row = byOffense.get(category.id);
    if (!row) {
      throw new Error(
        `Offense category ${category.id} is missing for ${first.entity_id}.`,
      );
    }
    if (row[totalField] !== total) {
      throw new Error(`Offense totals conflict for ${first.entity_id}.`);
    }
    const share = row[shareField];
    const shareStatus = row[statusField];
    if (
      (total > 0 && (share === null || shareStatus !== 'calculated')) ||
      (total === 0 && (share !== null || shareStatus !== 'refused_zero_total'))
    ) {
      throw new Error(`Offense share status conflicts for ${first.entity_id}.`);
    }
    return {
      offenseId: category.id,
      count: row[countField],
      share,
      shareStatus,
    };
  });
  if (
    cells.reduce((sum, cell) => sum + cell.count, 0) !== total ||
    (total > 0 &&
      Math.abs(cells.reduce((sum, cell) => sum + (cell.share ?? 0), 0) - 1) >
        1e-9)
  ) {
    throw new Error(
      `Offense composition does not reconcile for ${first.entity_id}.`,
    );
  }
  return {
    id: first.entity_id,
    name: first.display_label,
    publishedLabel: first.published_label,
    sourceOrder: first.source_order,
    isJapaneseReference: first.is_japanese_reference,
    entityKind: first.entity_kind,
    year: first.year,
    total,
    calculationStatus: first.calculation_status,
    refusalReason: first.refusal_reason,
    derivationMethod: first.derivation_method,
    derivationFormula: first.derivation_formula,
    numeratorSourceIds: [...first.numerator_source_ids],
    mismatchCodes: [...first.mismatch_flags],
    warningCodes: [...first.small_number_warning_flags],
    cells,
  };
}

export function buildOffenseCompositionViewModel(
  dashboard: DashboardData,
  metric: OffenseCompositionMetric = 'cleared_persons',
  order: OffenseCompositionOrder = 'cluster',
): OffenseCompositionViewModel {
  const definition =
    dashboard.definitions.offense_composition_ids[OFFENSE_COMPOSITION_ID];
  if (!definition) {
    throw new Error(
      `Offense composition definition is missing: ${OFFENSE_COMPOSITION_ID}`,
    );
  }
  const categories = definition.category_ids.map(
    (offenseId): OffenseCompositionCategory => {
      const category = dashboard.definitions.offense_category_ids[offenseId];
      if (!category) {
        throw new Error(`Offense category definition is missing: ${offenseId}`);
      }
      return {
        id: offenseId,
        label: category.label_ja,
        displayOrder: category.display_order,
        color: category.color,
        officialSeverityRole: category.official_severity_role,
      };
    },
  );
  categories.sort((left, right) => left.displayOrder - right.displayOrder);
  const selectedRows = dashboard.records.offense_composition.filter(
    (row) =>
      row.composition_id === OFFENSE_COMPOSITION_ID && row.display_included,
  );
  if (selectedRows.length === 0) {
    throw new Error('No offense composition rows exist.');
  }
  const grouped = new Map<string, OffenseCompositionRow[]>();
  for (const row of selectedRows) {
    const entityRows = grouped.get(row.entity_id) ?? [];
    entityRows.push(row);
    grouped.set(row.entity_id, entityRows);
  }
  const sourceOrdered = [...grouped.values()]
    .map((rows) => requireOffenseEntity(rows, categories, metric))
    .sort(
      (left, right) =>
        left.sourceOrder - right.sourceOrder ||
        left.name.localeCompare(right.name, 'ja'),
    );
  const byEntity = new Map(sourceOrdered.map((entity) => [entity.id, entity]));
  const clustering = definition.clustering[metric];
  if (!clustering) {
    throw new Error(`Offense clustering is missing for ${metric}.`);
  }
  if (
    clustering.order.length !== byEntity.size ||
    new Set(clustering.order).size !== byEntity.size ||
    clustering.order.some((entityId) => !byEntity.has(entityId))
  ) {
    throw new Error(`Offense cluster order is incomplete for ${metric}.`);
  }
  const entities =
    order === 'source'
      ? sourceOrdered
      : clustering.order.map((entityId) => {
          const entity = byEntity.get(entityId);
          if (!entity) {
            throw new Error(`Cluster entity is missing: ${entityId}`);
          }
          return entity;
        });
  const japanese = entities.filter((entity) => entity.isJapaneseReference);
  if (japanese.length !== 1) {
    throw new Error(
      `Expected exactly one Japanese offense reference, received ${japanese.length}.`,
    );
  }
  const sourceIds = new Set(
    selectedRows.flatMap((row) => row.numerator_source_ids),
  );
  const first = selectedRows[0];
  return {
    compositionId: OFFENSE_COMPOSITION_ID,
    metric,
    metricLabel: metric === 'cleared_persons' ? '検挙人員' : '検挙件数',
    unitLabel: metric === 'cleared_persons' ? '人' : '件',
    order,
    year: first.year,
    label: definition.label_ja,
    interpretationPolicy: definition.interpretation_policy,
    uiCaveat: definition.ui_caveat,
    smallNumberTotalThreshold: definition.small_number_total_threshold,
    categories,
    entities,
    japaneseReference: japanese[0],
    clustering,
    warningCodes: [
      ...new Set(selectedRows.flatMap((row) => row.small_number_warning_flags)),
    ].sort(),
    mismatchCodes: [
      ...new Set(selectedRows.flatMap((row) => row.mismatch_flags)),
    ].sort(),
    sources: collectSources(dashboard, sourceIds),
  };
}

export function formatDashboardValue(value: number, mode: ValueMode): string {
  return value.toLocaleString('ja-JP', {
    minimumFractionDigits: mode === 'ratio' ? 2 : 0,
    maximumFractionDigits: mode === 'ratio' ? 2 : 0,
  });
}
