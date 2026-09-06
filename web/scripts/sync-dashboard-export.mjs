import { createHash, randomUUID } from 'node:crypto';
import {
  mkdirSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const EXPECTED_COMPACT_EXPORT_SCHEMA_VERSION = 8;
const SAME_YEAR_GAP_CONTEXT_ID =
  'all_resident_same_year_recognition_clearance_gap';
const CLEARANCE_SHARE_TREND_ID =
  'national_criminal_code_clearance_foreign_share';
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
};
const CLEARANCE_POPULATION_TREND_ID =
  'national_clearance_population_reference_ratio';
const CLEARANCE_POPULATION_LABEL_JA = '人口1,000人当たりの刑法犯検挙参考比率';
const CLEARANCE_POPULATION_INTERPRETATION_POLICY =
  'public_data_reference_ratio_not_probability';
const CLEARANCE_POPULATION_UI_CAVEAT =
  '1年間の刑法犯検挙件数または検挙人員を、10月1日の日本人人口または12月31日の在留外国人数で単純に割った公表統計由来の参考比率である。犯罪統計の分子から居住者だけを識別できず、特に「外国人全体」と在留外国人人口の対象範囲は一致しない。犯罪を行う確率や公的な犯罪率を示さない。';
const CLEARANCE_POPULATION_GROUP_CONTRACTS = {
  japanese_etc_residual: {
    label: '日本人等（全国総数−外国人全体の残差）',
    numeratorSourceIds: ['S15', 'S08'],
    populationScope: 'japanese_population',
    derivationMethod:
      'arithmetic_residual_all_person_minus_all_foreign_division',
    requiredFlags: [
      'annual_clearance_flow_vs_point_in_time_population_stock',
      'japanese_numerator_is_arithmetic_residual',
      'japanese_population_rounded_to_nearest_1000',
      'numerator_residency_scope_not_established',
      'october_1_population_reference_date',
      'public_data_reference_ratio_not_official_crime_rate',
    ],
  },
  all_foreign: {
    label: '外国人全体（分母は在留外国人数）',
    numeratorSourceIds: ['S08'],
    populationScope: 'resident_foreigner_population',
    derivationMethod: 'direct_published_count_division',
    requiredFlags: [
      'all_foreign_numerator_vs_resident_foreigner_denominator',
      'annual_clearance_flow_vs_point_in_time_population_stock',
      'december_31_population_reference_date',
      'numerator_residency_scope_not_established',
      'public_data_reference_ratio_not_official_crime_rate',
    ],
  },
};
const JAPANESE_POPULATION_SOURCES = new Map([
  ...Array.from({ length: 6 }, (_, index) => [2015 + index, 'S18']),
  [2021, 'S17_2021'],
  [2022, 'S17_2022'],
  [2023, 'S17_2023'],
  [2024, 'S17'],
]);
const FOREIGN_POPULATION_COORDINATES = new Map([
  [2016, ['S19_2016', '16-12-01-1', 7, 3]],
  [2017, ['S19_2017', '17-12-01-1', 7, 3]],
  [2018, ['S19_2018', '18-12-01-1', 7, 3]],
  [2019, ['S19_2019', '19-12-01-1', 7, 2]],
  [2020, ['S19_2020', '20-12-01-1', 7, 2]],
  [2021, ['S19_2021', '21-12-01-1', 7, 2]],
  [2022, ['S19_2022', '22-12-01m', 5, 6]],
  [2023, ['S19_2023', '23-12-01m', 5, 5]],
  [2024, ['S19_2024', '24-12-01m', 5, 5]],
]);
const PUBLICATION_MANIFEST_SCHEMA_VERSION = 1;
const SAFE_RUN_RELPATH = /^\d{8}_\d{6}_compact_export$/u;
const SHA256 = /^[a-f0-9]{64}$/u;
const PRIVATE_LOCAL_PATH =
  /(?:^|[\s"'=(])(?:\/(?!\/|\s)(?:[^\s"'()]+\/)*[^\s"'()]*|[A-Za-z]:[\\/]|\\\\[^\\\s]+\\|file:\/\/)/u;
const PRIVATE_FILESYSTEM_PATH_IN_TEXT =
  /(?:^|[\s"'=(])(?:\/(?:Users|home|private|tmp|var|workspace|opt)(?:\/|$)|[A-Za-z]:[\\/]|\\\\[^\\\s]+\\[^\\\s"'()]+|file:\/\/)/u;

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultPointerPath = resolve(
  scriptDirectory,
  '../../output/compact_export/latest.json',
);
const defaultDestinationPath = resolve(
  scriptDirectory,
  '../public/data/dashboard_export.json',
);
const defaultManifestPath = resolve(
  scriptDirectory,
  '../public/data/dashboard_export.manifest.json',
);
const defaultPublicationPointerPath = resolve(
  scriptDirectory,
  '../../config/publication/compact_export/latest.json',
);

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function parseJson(bytes, label) {
  try {
    return JSON.parse(bytes.toString('utf8'));
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error.message}`);
  }
}

function requireObject(value, label) {
  if (!isObject(value)) throw new Error(`${label} must be a JSON object.`);
  return value;
}

function requireSha256(value, label) {
  if (typeof value !== 'string' || !SHA256.test(value)) {
    throw new Error(`${label} must be a lowercase SHA-256 digest.`);
  }
  return value;
}

function requireCount(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative integer.`);
  }
  return value;
}

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, received ${actual}.`);
  }
}

function clearanceShareSemanticError(detail) {
  throw new Error(`Clearance-share semantic contract: ${detail}.`);
}

function clearancePopulationSemanticError(detail) {
  throw new Error(`Clearance-population semantic contract: ${detail}.`);
}

function arraysEqual(actual, expected) {
  return (
    Array.isArray(actual) &&
    actual.length === expected.length &&
    actual.every((value, index) => value === expected[index])
  );
}

function validateClearanceShareComponents(record, expected) {
  if (
    !Array.isArray(record.source_components) ||
    record.source_components.some((component) => !isObject(component))
  ) {
    clearanceShareSemanticError('source_components must be an object array');
  }
  const actual = record.source_components.map((component) => [
    component.source_id,
    component.role,
    component.metric,
    component.value,
    component.source_table,
    component.source_sheet,
    component.source_row,
    component.source_column,
  ]);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    clearanceShareSemanticError(
      'source_components do not match the bound scope inputs',
    );
  }
}

function validateClearancePopulationComponents(record, expected) {
  if (
    !Array.isArray(record.source_components) ||
    record.source_components.some((component) => !isObject(component))
  ) {
    clearancePopulationSemanticError(
      'source_components must be an object array',
    );
  }
  const actual = record.source_components.map((component) => [
    component.source_id,
    component.role,
    component.metric,
    component.value,
    component.source_table,
    component.source_sheet,
    component.source_row,
    component.source_column,
    component.published_value,
    component.published_unit,
  ]);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    clearancePopulationSemanticError(
      'source_components do not match the population inputs',
    );
  }
}

function visitStrings(value, visitor, path = '$') {
  if (typeof value === 'string') {
    visitor(value, path);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) =>
      visitStrings(item, visitor, `${path}[${index}]`),
    );
    return;
  }
  if (isObject(value)) {
    for (const [key, item] of Object.entries(value)) {
      visitStrings(item, visitor, `${path}.${key}`);
    }
  }
}

export function assertNoPrivateLocalPaths(value) {
  visitStrings(value, (text, path) => {
    if (PRIVATE_LOCAL_PATH.test(text)) {
      throw new Error(`Private local path found at ${path}.`);
    }
  });
}

export function assertNoPrivateFilesystemPathsInText(text) {
  if (typeof text !== 'string' || PRIVATE_FILESYSTEM_PATH_IN_TEXT.test(text)) {
    throw new Error('Private local path found in publication artifact text.');
  }
}

function validateSource(source, sourceId) {
  requireObject(source, `sources.${sourceId}`);
  if (typeof source.publisher !== 'string' || source.publisher.length === 0) {
    throw new Error(`sources.${sourceId}.publisher is missing.`);
  }
  for (const key of ['landing_url', 'download_url']) {
    if (
      typeof source[key] !== 'string' ||
      !source[key].startsWith('https://')
    ) {
      throw new Error(`sources.${sourceId}.${key} must be an HTTPS URL.`);
    }
  }
}

function validateClearancePopulationRecords(payload, definitions, sources) {
  const definition = definitions[CLEARANCE_POPULATION_TREND_ID];
  if (
    !isObject(definition) ||
    definition.label_ja !== CLEARANCE_POPULATION_LABEL_JA ||
    definition.interpretation_policy !==
      CLEARANCE_POPULATION_INTERPRETATION_POLICY ||
    definition.ui_caveat !== CLEARANCE_POPULATION_UI_CAVEAT ||
    definition.display_multiplier !== 1000 ||
    definition.display_unit_label_ja !== '人口1,000人当たり'
  ) {
    clearancePopulationSemanticError('definition binding differs');
  }

  const rowsByMetricYear = new Map();
  const uniqueKeys = new Set();
  payload.records.clearance_population_trends.forEach((record, index) => {
    const label = `records.clearance_population_trends[${index}]`;
    requireObject(record, label);
    if (!Object.hasOwn(definitions, record.trend_id)) {
      throw new Error(`${label} references an unknown trend definition.`);
    }
    if (
      record.trend_id !== CLEARANCE_POPULATION_TREND_ID ||
      !Number.isSafeInteger(record.year) ||
      !['cleared_cases', 'cleared_persons'].includes(record.metric)
    ) {
      throw new Error(`${label} has unsupported dimensions.`);
    }
    const groupContract =
      CLEARANCE_POPULATION_GROUP_CONTRACTS[record.population_group];
    if (!groupContract) {
      throw new Error(`${label} has an unsupported population_group.`);
    }
    if (
      record.population_group_label_ja !== groupContract.label ||
      record.population_scope !== groupContract.populationScope ||
      record.metric_label_ja !==
        (record.metric === 'cleared_cases' ? '検挙件数' : '検挙人員')
    ) {
      clearancePopulationSemanticError(
        `group or metric label binding differs at ${label}`,
      );
    }
    if (
      !arraysEqual(
        record.numerator_source_ids,
        groupContract.numeratorSourceIds,
      )
    ) {
      clearancePopulationSemanticError(
        `numerator source binding differs at ${label}`,
      );
    }
    for (const sourceId of record.numerator_source_ids) {
      if (!Object.hasOwn(sources, sourceId)) {
        throw new Error(`${label} references an unknown numerator source.`);
      }
    }
    if (
      record.denominator_source_id !== null &&
      !Object.hasOwn(sources, record.denominator_source_id)
    ) {
      throw new Error(`${label} references an unknown denominator source.`);
    }
    if (
      !Array.isArray(record.mismatch_flags) ||
      !groupContract.requiredFlags.every((flag) =>
        record.mismatch_flags.includes(flag),
      )
    ) {
      clearancePopulationSemanticError(
        `required mismatch flags are absent at ${label}`,
      );
    }
    if (
      !Number.isSafeInteger(record.numerator_value) ||
      record.numerator_value < 0
    ) {
      throw new Error(`${label} has an invalid numerator.`);
    }

    const uniqueKey = `${record.metric}:${record.year}:${record.population_group}`;
    if (uniqueKeys.has(uniqueKey)) {
      throw new Error(`${label} duplicates ${uniqueKey}.`);
    }
    uniqueKeys.add(uniqueKey);
    const metricYearKey = `${record.metric}:${record.year}`;
    const metricYearRows = rowsByMetricYear.get(metricYearKey) ?? [];
    metricYearRows.push(record);
    rowsByMetricYear.set(metricYearKey, metricYearRows);

    const foreignClearanceComponent = [
      'S08',
      'numerator',
      record.metric,
      record.numerator_value,
      '130',
      '01',
      record.year - 2007,
      record.metric === 'cleared_cases' ? 7 : 8,
      undefined,
      undefined,
    ];

    if (record.population_group === 'japanese_etc_residual') {
      if (
        record.calculation_status !== 'calculated' ||
        record.refusal_reason !== null ||
        !Number.isSafeInteger(record.denominator_value) ||
        record.denominator_value <= 0 ||
        !Array.isArray(record.source_components) ||
        record.source_components.length !== 3
      ) {
        clearancePopulationSemanticError(
          `Japanese residual calculation status differs at ${label}`,
        );
      }
      const [allPersonComponent, allForeignComponent] =
        record.source_components;
      if (
        !isObject(allPersonComponent) ||
        !isObject(allForeignComponent) ||
        !Number.isSafeInteger(allPersonComponent.value) ||
        !Number.isSafeInteger(allForeignComponent.value) ||
        allPersonComponent.value - allForeignComponent.value !==
          record.numerator_value
      ) {
        clearancePopulationSemanticError(
          `Japanese numerator residual differs at ${label}`,
        );
      }
      const sourceId = JAPANESE_POPULATION_SOURCES.get(record.year);
      if (!sourceId) {
        clearancePopulationSemanticError(
          `unsupported Japanese population year at ${label}`,
        );
      }
      const isIntercensal = sourceId === 'S18';
      if (
        record.denominator_source_id !== sourceId ||
        record.population_reference_date !== `${record.year}-10-01` ||
        record.denominator_rounding !== 'nearest_1000_persons' ||
        record.derivation_method !== groupContract.derivationMethod ||
        record.derivation_formula !==
          `(S15.${record.metric} - S08.${record.metric}) / ${sourceId}.population * 1000`
      ) {
        clearancePopulationSemanticError(
          `Japanese source, date, or formula differs at ${label}`,
        );
      }
      validateClearancePopulationComponents(record, [
        [
          'S15',
          'numerator_minuend',
          record.metric,
          allPersonComponent.value,
          '3',
          '刑法犯総数',
          record.year - 2006,
          record.metric === 'cleared_cases' ? 5 : 6,
          undefined,
          undefined,
        ],
        [
          'S08',
          'numerator_subtrahend',
          record.metric,
          allForeignComponent.value,
          '130',
          '01',
          record.year - 2007,
          record.metric === 'cleared_cases' ? 7 : 8,
          undefined,
          undefined,
        ],
        [
          sourceId,
          'denominator',
          'population',
          record.denominator_value,
          isIntercensal ? '5' : '2',
          isIntercensal ? '日本人人口 (2015年～2020年)' : '第2表',
          isIntercensal ? 11 : 12,
          isIntercensal ? record.year - 2010 : 9,
          record.denominator_value / 1000,
          '1000_persons',
        ],
      ]);
    } else {
      const populationCoordinate = FOREIGN_POPULATION_COORDINATES.get(
        record.year,
      );
      if (!populationCoordinate) {
        if (
          record.calculation_status !== 'refused' ||
          record.refusal_reason !==
            'resident_foreigner_population_source_not_registered_for_year' ||
          record.denominator_value !== null ||
          record.quotient !== null ||
          record.display_value !== null ||
          record.denominator_source_id !== null ||
          record.population_reference_date !== null ||
          record.denominator_rounding !== null ||
          record.derivation_method !==
            'direct_published_count_division_refused' ||
          record.derivation_formula !== null ||
          !record.mismatch_flags.includes('population_denominator_unavailable')
        ) {
          clearancePopulationSemanticError(
            `foreign refusal semantics differ at ${label}`,
          );
        }
        validateClearancePopulationComponents(record, [
          foreignClearanceComponent,
        ]);
        return;
      }
      const [sourceId, sheet, sourceRow, sourceColumn] = populationCoordinate;
      if (
        record.calculation_status !== 'calculated' ||
        record.refusal_reason !== null ||
        !Number.isSafeInteger(record.denominator_value) ||
        record.denominator_value <= 0 ||
        record.denominator_source_id !== sourceId ||
        record.population_reference_date !== `${record.year}-12-31` ||
        record.denominator_rounding !== 'as_published_persons' ||
        record.derivation_method !== groupContract.derivationMethod ||
        record.derivation_formula !==
          `S08.${record.metric} / ${sourceId}.population * 1000`
      ) {
        clearancePopulationSemanticError(
          `foreign source, date, or formula differs at ${label}`,
        );
      }
      validateClearancePopulationComponents(record, [
        foreignClearanceComponent,
        [
          sourceId,
          'denominator',
          'population',
          record.denominator_value,
          '1',
          sheet,
          sourceRow,
          sourceColumn,
          record.denominator_value,
          'persons',
        ],
      ]);
    }

    const expectedQuotient = record.numerator_value / record.denominator_value;
    if (
      typeof record.quotient !== 'number' ||
      typeof record.display_value !== 'number' ||
      Math.abs(record.quotient - expectedQuotient) > 1e-12 ||
      Math.abs(record.display_value - expectedQuotient * 1000) > 1e-10
    ) {
      throw new Error(`${label} has inconsistent arithmetic.`);
    }
  });

  const clearanceShares = new Map(
    payload.records.clearance_share_trends
      .filter((record) => record.foreign_scope === 'all_foreign')
      .map((record) => [`${record.metric}:${record.year}`, record]),
  );
  for (const [metricYear, rows] of rowsByMetricYear) {
    const japanese = rows.find(
      (row) => row.population_group === 'japanese_etc_residual',
    );
    const allForeign = rows.find(
      (row) => row.population_group === 'all_foreign',
    );
    if (rows.length !== 2 || !japanese || !allForeign) {
      throw new Error(
        `Clearance-population group set is incomplete for ${metricYear}.`,
      );
    }
    const clearanceShare = clearanceShares.get(metricYear);
    if (
      clearanceShare &&
      (allForeign.numerator_value !== clearanceShare.numerator_value ||
        !arraysEqual(
          allForeign.numerator_source_ids,
          clearanceShare.numerator_source_ids,
        ) ||
        japanese.source_components[0].value !==
          clearanceShare.denominator_value)
    ) {
      clearancePopulationSemanticError(
        `clearance counts differ from clearance-share inputs for ${metricYear}`,
      );
    }
  }
}

function validateRecordLinks(payload) {
  const indicatorDefinitions = payload.definitions.indicator_ids;
  const contextDefinitions = payload.definitions.context_ids;
  const comparisonDefinitions = payload.definitions.nationality_comparison_ids;
  const offenseDefinitions = payload.definitions.offense_composition_ids;
  const offenseCategoryDefinitions = payload.definitions.offense_category_ids;
  const clearanceShareDefinitions = payload.definitions.clearance_share_ids;
  const clearancePopulationDefinitions =
    payload.definitions.clearance_population_ids;
  const sources = payload.sources;
  const clearanceShareDefinition =
    clearanceShareDefinitions[CLEARANCE_SHARE_TREND_ID];
  if (
    !isObject(clearanceShareDefinition) ||
    clearanceShareDefinition.label_ja !== CLEARANCE_SHARE_LABEL_JA ||
    clearanceShareDefinition.interpretation_policy !==
      CLEARANCE_SHARE_INTERPRETATION_POLICY ||
    clearanceShareDefinition.ui_caveat !== CLEARANCE_SHARE_UI_CAVEAT ||
    clearanceShareDefinition.display_multiplier !== 100 ||
    clearanceShareDefinition.display_unit_label_ja !== '%'
  ) {
    clearanceShareSemanticError('definition binding differs');
  }

  payload.records.nationality_indicators.forEach((record, index) => {
    requireObject(record, `records.nationality_indicators[${index}]`);
    if (!Object.hasOwn(indicatorDefinitions, record.indicator_id)) {
      throw new Error(
        `records.nationality_indicators[${index}] references an unknown indicator definition.`,
      );
    }
    for (const key of ['numerator_source_id', 'denominator_source_id']) {
      if (record[key] !== null && !Object.hasOwn(sources, record[key])) {
        throw new Error(
          `records.nationality_indicators[${index}] references an unknown ${key}.`,
        );
      }
    }
    if (
      record.calculation_status === 'calculated' &&
      (!record.numerator_source_id || !record.denominator_source_id)
    ) {
      throw new Error(
        `records.nationality_indicators[${index}] is calculated without both source IDs.`,
      );
    }
  });

  payload.records.all_resident_context.forEach((record, index) => {
    requireObject(record, `records.all_resident_context[${index}]`);
    if (!Object.hasOwn(contextDefinitions, record.context_id)) {
      throw new Error(
        `records.all_resident_context[${index}] references an unknown context definition.`,
      );
    }
    for (const key of ['numerator_source_id', 'denominator_source_id']) {
      if (record[key] !== null && !Object.hasOwn(sources, record[key])) {
        throw new Error(
          `records.all_resident_context[${index}] references an unknown ${key}.`,
        );
      }
    }
    if (
      record.calculation_status === 'calculated' &&
      (!record.numerator_source_id || !record.denominator_source_id)
    ) {
      throw new Error(
        `records.all_resident_context[${index}] is calculated without both source IDs.`,
      );
    }
    if (record.context_id === SAME_YEAR_GAP_CONTEXT_ID) {
      if (
        !Array.isArray(record.mismatch_flags) ||
        !record.mismatch_flags.includes('not_unresolved_case_cohort')
      ) {
        throw new Error(
          `records.all_resident_context[${index}] lacks the non-cohort warning.`,
        );
      }
      if (
        record.recognized_cases_value !== null &&
        record.cleared_cases_value !== null
      ) {
        const expectedGap =
          record.recognized_cases_value - record.cleared_cases_value;
        assertEqual(
          record.numerator_value,
          expectedGap,
          `records.all_resident_context[${index}] same-year gap mismatch`,
        );
        assertEqual(
          record.denominator_value,
          record.recognized_cases_value,
          `records.all_resident_context[${index}] recognized denominator mismatch`,
        );
        if (record.recognized_cases_value > 0) {
          const expectedDisplay =
            (expectedGap / record.recognized_cases_value) * 100;
          if (
            typeof record.display_value !== 'number' ||
            Math.abs(record.display_value - expectedDisplay) > 1e-10
          ) {
            throw new Error(
              `records.all_resident_context[${index}] same-year gap percentage mismatch.`,
            );
          }
        }
      }
    }
  });

  payload.records.nationality_comparison.forEach((record, index) => {
    requireObject(record, `records.nationality_comparison[${index}]`);
    if (!Object.hasOwn(comparisonDefinitions, record.comparison_id)) {
      throw new Error(
        `records.nationality_comparison[${index}] references an unknown comparison definition.`,
      );
    }
    if (
      !Array.isArray(record.numerator_source_ids) ||
      record.numerator_source_ids.length === 0
    ) {
      throw new Error(
        `records.nationality_comparison[${index}].numerator_source_ids must be a non-empty array.`,
      );
    }
    for (const sourceId of record.numerator_source_ids) {
      if (typeof sourceId !== 'string' || !Object.hasOwn(sources, sourceId)) {
        throw new Error(
          `records.nationality_comparison[${index}] references an unknown numerator source.`,
        );
      }
    }
    if (
      typeof record.denominator_source_id !== 'string' ||
      !Object.hasOwn(sources, record.denominator_source_id)
    ) {
      throw new Error(
        `records.nationality_comparison[${index}] references an unknown denominator source.`,
      );
    }
    if (
      record.calculation_status === 'calculated' &&
      (!record.denominator_source_id ||
        record.numerator_source_ids.length === 0)
    ) {
      throw new Error(
        `records.nationality_comparison[${index}] is calculated without numerator and denominator source IDs.`,
      );
    }
  });

  payload.records.offense_composition.forEach((record, index) => {
    requireObject(record, `records.offense_composition[${index}]`);
    if (!Object.hasOwn(offenseDefinitions, record.composition_id)) {
      throw new Error(
        `records.offense_composition[${index}] references an unknown composition definition.`,
      );
    }
    if (!Object.hasOwn(offenseCategoryDefinitions, record.offense_id)) {
      throw new Error(
        `records.offense_composition[${index}] references an unknown offense category.`,
      );
    }
    if (
      !Array.isArray(record.numerator_source_ids) ||
      record.numerator_source_ids.length === 0
    ) {
      throw new Error(
        `records.offense_composition[${index}].numerator_source_ids must be a non-empty array.`,
      );
    }
    for (const sourceId of record.numerator_source_ids) {
      if (typeof sourceId !== 'string' || !Object.hasOwn(sources, sourceId)) {
        throw new Error(
          `records.offense_composition[${index}] references an unknown numerator source.`,
        );
      }
    }
  });

  const clearanceShareKeys = new Set();
  const clearanceShareRowsByMetricYear = new Map();
  payload.records.clearance_share_trends.forEach((record, index) => {
    const label = `records.clearance_share_trends[${index}]`;
    requireObject(record, label);
    if (!Object.hasOwn(clearanceShareDefinitions, record.trend_id)) {
      throw new Error(`${label} references an unknown trend definition.`);
    }
    if (record.trend_id !== CLEARANCE_SHARE_TREND_ID) {
      throw new Error(`${label} has an unsupported trend_id.`);
    }
    if (!['cleared_cases', 'cleared_persons'].includes(record.metric)) {
      throw new Error(`${label} has an unsupported metric.`);
    }
    const scopeContract = CLEARANCE_SHARE_SCOPE_CONTRACTS[record.foreign_scope];
    if (!scopeContract) {
      throw new Error(`${label} has an unsupported foreign_scope.`);
    }
    if (
      record.foreign_scope_label_ja !== scopeContract.label ||
      record.numerator_source_id !== scopeContract.numeratorSourceId ||
      record.denominator_source_id !== 'S15' ||
      record.derivation_method !== scopeContract.derivationMethod ||
      record.metric_label_ja !==
        (record.metric === 'cleared_cases' ? '検挙件数' : '検挙人員')
    ) {
      clearanceShareSemanticError(
        `scope, source, label, or interpretation binding differs at ${label}`,
      );
    }
    for (const key of ['numerator_source_id', 'denominator_source_id']) {
      if (
        typeof record[key] !== 'string' ||
        !Object.hasOwn(sources, record[key])
      ) {
        throw new Error(`${label} references an unknown ${key}.`);
      }
    }
    if (
      !Array.isArray(record.numerator_source_ids) ||
      record.numerator_source_ids.length === 0
    ) {
      throw new Error(
        `${label}.numerator_source_ids must be a non-empty array.`,
      );
    }
    for (const sourceId of record.numerator_source_ids) {
      if (typeof sourceId !== 'string' || !Object.hasOwn(sources, sourceId)) {
        throw new Error(`${label} references an unknown numerator source.`);
      }
    }
    if (
      !arraysEqual(
        record.numerator_source_ids,
        scopeContract.numeratorSourceIds,
      )
    ) {
      clearanceShareSemanticError(
        `numerator source binding differs at ${label}`,
      );
    }
    if (
      !Array.isArray(record.mismatch_flags) ||
      !scopeContract.requiredFlags.every((flag) =>
        record.mismatch_flags.includes(flag),
      )
    ) {
      clearanceShareSemanticError(
        `required mismatch flags are absent at ${label}`,
      );
    }
    if (
      record.calculation_status !== 'calculated' ||
      record.refusal_reason !== null ||
      !Number.isSafeInteger(record.year) ||
      !Number.isSafeInteger(record.numerator_value) ||
      !Number.isSafeInteger(record.denominator_value) ||
      record.numerator_value < 0 ||
      record.denominator_value <= 0 ||
      record.numerator_value > record.denominator_value
    ) {
      throw new Error(`${label} has invalid calculated counts.`);
    }
    const expectedQuotient = record.numerator_value / record.denominator_value;
    const expectedDisplay = expectedQuotient * 100;
    if (
      typeof record.quotient !== 'number' ||
      typeof record.display_value !== 'number' ||
      Math.abs(record.quotient - expectedQuotient) > 1e-12 ||
      Math.abs(record.display_value - expectedDisplay) > 1e-10
    ) {
      throw new Error(`${label} has inconsistent arithmetic.`);
    }
    const expectedFormula =
      record.foreign_scope === 'all_foreign_minus_visiting_foreign'
        ? `(S08.${record.metric} - S09.${record.metric}) / S15.${record.metric}`
        : `${scopeContract.numeratorSourceId}.${record.metric} / S15.${record.metric}`;
    if (record.derivation_formula !== expectedFormula) {
      clearanceShareSemanticError(`derivation formula differs at ${label}`);
    }

    const uniqueKey = `${record.metric}:${record.year}:${record.foreign_scope}`;
    if (clearanceShareKeys.has(uniqueKey)) {
      throw new Error(`${label} duplicates ${uniqueKey}.`);
    }
    clearanceShareKeys.add(uniqueKey);
    const metricYearKey = `${record.metric}:${record.year}`;
    const metricYearRows =
      clearanceShareRowsByMetricYear.get(metricYearKey) ?? [];
    metricYearRows.push(record);
    clearanceShareRowsByMetricYear.set(metricYearKey, metricYearRows);
  });
  for (const [metricYear, rows] of clearanceShareRowsByMetricYear) {
    const allForeign = rows.find((row) => row.foreign_scope === 'all_foreign');
    const visitingForeign = rows.find(
      (row) => row.foreign_scope === 'visiting_foreign',
    );
    const residual = rows.find(
      (row) => row.foreign_scope === 'all_foreign_minus_visiting_foreign',
    );
    if (
      rows.length !== 3 ||
      !allForeign ||
      !visitingForeign ||
      !residual ||
      rows.some(
        (row) => row.denominator_value !== allForeign.denominator_value,
      ) ||
      rows.some(
        (row) => row.denominator_source_id !== allForeign.denominator_source_id,
      )
    ) {
      throw new Error(
        `Clearance-share scope set is incomplete for ${metricYear}.`,
      );
    }
    if (
      visitingForeign.numerator_value > allForeign.numerator_value ||
      residual.numerator_value !==
        allForeign.numerator_value - visitingForeign.numerator_value ||
      residual.derivation_method !==
        'arithmetic_residual_all_foreign_minus_visiting_foreign' ||
      residual.numerator_source_ids.length !== 2 ||
      residual.numerator_source_ids[0] !== allForeign.numerator_source_id ||
      residual.numerator_source_ids[1] !== visitingForeign.numerator_source_id
    ) {
      throw new Error(
        `Clearance-share residual is inconsistent for ${metricYear}.`,
      );
    }
    validateClearanceShareComponents(allForeign, [
      [
        'S08',
        'numerator',
        allForeign.metric,
        allForeign.numerator_value,
        '130',
        '01',
        allForeign.year - 2007,
        allForeign.metric === 'cleared_cases' ? 7 : 8,
      ],
      [
        'S15',
        'denominator',
        allForeign.metric,
        allForeign.denominator_value,
        '3',
        '刑法犯総数',
        allForeign.year - 2006,
        allForeign.metric === 'cleared_cases' ? 5 : 6,
      ],
    ]);
    validateClearanceShareComponents(visitingForeign, [
      [
        'S09',
        'numerator',
        visitingForeign.metric,
        visitingForeign.numerator_value,
        '131',
        '01',
        visitingForeign.year - 2007,
        visitingForeign.metric === 'cleared_cases' ? 6 : 7,
      ],
      [
        'S15',
        'denominator',
        visitingForeign.metric,
        visitingForeign.denominator_value,
        '3',
        '刑法犯総数',
        visitingForeign.year - 2006,
        visitingForeign.metric === 'cleared_cases' ? 5 : 6,
      ],
    ]);
    validateClearanceShareComponents(residual, [
      [
        'S08',
        'numerator_minuend',
        residual.metric,
        allForeign.numerator_value,
        '130',
        '01',
        residual.year - 2007,
        residual.metric === 'cleared_cases' ? 7 : 8,
      ],
      [
        'S09',
        'numerator_subtrahend',
        residual.metric,
        visitingForeign.numerator_value,
        '131',
        '01',
        residual.year - 2007,
        residual.metric === 'cleared_cases' ? 6 : 7,
      ],
      [
        'S15',
        'denominator',
        residual.metric,
        residual.denominator_value,
        '3',
        '刑法犯総数',
        residual.year - 2006,
        residual.metric === 'cleared_cases' ? 5 : 6,
      ],
    ]);
  }
  validateClearancePopulationRecords(
    payload,
    clearancePopulationDefinitions,
    sources,
  );
}

export function inspectDashboardPayload(payload) {
  requireObject(payload, 'dashboard export');
  assertEqual(
    payload.compact_export_schema_version,
    EXPECTED_COMPACT_EXPORT_SCHEMA_VERSION,
    'compact export schema version mismatch',
  );
  requireObject(payload.definitions, 'definitions');
  requireObject(payload.definitions.indicator_ids, 'definitions.indicator_ids');
  requireObject(payload.definitions.context_ids, 'definitions.context_ids');
  requireObject(
    payload.definitions.nationality_comparison_ids,
    'definitions.nationality_comparison_ids',
  );
  requireObject(
    payload.definitions.offense_composition_ids,
    'definitions.offense_composition_ids',
  );
  requireObject(
    payload.definitions.offense_category_ids,
    'definitions.offense_category_ids',
  );
  requireObject(
    payload.definitions.clearance_share_ids,
    'definitions.clearance_share_ids',
  );
  requireObject(
    payload.definitions.clearance_population_ids,
    'definitions.clearance_population_ids',
  );
  requireObject(payload.records, 'records');
  if (!Array.isArray(payload.records.nationality_indicators)) {
    throw new Error('records.nationality_indicators must be an array.');
  }
  if (!Array.isArray(payload.records.all_resident_context)) {
    throw new Error('records.all_resident_context must be an array.');
  }
  if (!Array.isArray(payload.records.nationality_comparison)) {
    throw new Error('records.nationality_comparison must be an array.');
  }
  if (!Array.isArray(payload.records.offense_composition)) {
    throw new Error('records.offense_composition must be an array.');
  }
  if (!Array.isArray(payload.records.clearance_share_trends)) {
    throw new Error('records.clearance_share_trends must be an array.');
  }
  if (!Array.isArray(payload.records.clearance_population_trends)) {
    throw new Error('records.clearance_population_trends must be an array.');
  }
  requireObject(payload.sources, 'sources');
  requireObject(payload.publication_policy, 'publication_policy');
  assertEqual(
    payload.publication_policy.primary_view,
    'all_resident_context',
    'publication primary view mismatch',
  );
  assertEqual(
    payload.publication_policy.secondary_view,
    'nationality_comparison',
    'publication secondary view mismatch',
  );
  assertEqual(
    payload.publication_policy.supplementary_view,
    'nationality_indicators',
    'publication supplementary view mismatch',
  );
  assertEqual(
    payload.publication_policy.composition_view,
    'offense_composition',
    'publication composition view mismatch',
  );
  assertEqual(
    payload.publication_policy.clearance_share_view,
    CLEARANCE_SHARE_TREND_ID,
    'publication clearance-share view mismatch',
  );
  assertEqual(
    payload.publication_policy.clearance_population_view,
    CLEARANCE_POPULATION_TREND_ID,
    'publication clearance-population view mismatch',
  );
  assertEqual(
    payload.publication_policy.same_year_gap_view,
    SAME_YEAR_GAP_CONTEXT_ID,
    'publication same-year gap view mismatch',
  );
  assertEqual(
    payload.publication_policy.same_year_gap_is_unresolved_cohort,
    false,
    'same-year gap cohort policy mismatch',
  );
  const gapDefinition = requireObject(
    payload.definitions.context_ids[SAME_YEAR_GAP_CONTEXT_ID],
    `definitions.context_ids.${SAME_YEAR_GAP_CONTEXT_ID}`,
  );
  assertEqual(
    gapDefinition.interpretation_policy,
    'same_year_flow_difference_not_cohort_unresolved',
    'same-year gap interpretation policy mismatch',
  );
  assertEqual(
    payload.publication_policy.official_crime_rate_claim_allowed,
    false,
    'official crime-rate claim policy mismatch',
  );
  assertEqual(
    payload.publication_policy.derived_value_label_ja,
    '公表統計由来の参考比率',
    'derived-value label mismatch',
  );

  for (const [sourceId, source] of Object.entries(payload.sources)) {
    validateSource(source, sourceId);
  }
  validateRecordLinks(payload);
  assertNoPrivateLocalPaths(payload);

  return {
    compact_export_schema_version: payload.compact_export_schema_version,
    record_counts: {
      all_resident_context: payload.records.all_resident_context.length,
      nationality_comparison: payload.records.nationality_comparison.length,
      nationality_indicators: payload.records.nationality_indicators.length,
      offense_composition: payload.records.offense_composition.length,
      clearance_share_trends: payload.records.clearance_share_trends.length,
      clearance_population_trends:
        payload.records.clearance_population_trends.length,
    },
    definition_counts: {
      context_ids: Object.keys(payload.definitions.context_ids).length,
      indicator_ids: Object.keys(payload.definitions.indicator_ids).length,
      nationality_comparison_ids: Object.keys(
        payload.definitions.nationality_comparison_ids,
      ).length,
      offense_composition_ids: Object.keys(
        payload.definitions.offense_composition_ids,
      ).length,
      offense_category_ids: Object.keys(
        payload.definitions.offense_category_ids,
      ).length,
      clearance_share_ids: Object.keys(payload.definitions.clearance_share_ids)
        .length,
      clearance_population_ids: Object.keys(
        payload.definitions.clearance_population_ids,
      ).length,
    },
    source_count: Object.keys(payload.sources).length,
  };
}

function validateCounts(actual, expected, label) {
  requireObject(expected, label);
  for (const [key, value] of Object.entries(actual)) {
    assertEqual(
      value,
      requireCount(expected[key], `${label}.${key}`),
      `${label}.${key} mismatch`,
    );
  }
}

function validateManifest(manifest, dashboardBytes, dashboardPayload) {
  requireObject(manifest, 'publication manifest');
  assertEqual(
    manifest.publication_manifest_schema_version,
    PUBLICATION_MANIFEST_SCHEMA_VERSION,
    'publication manifest schema version mismatch',
  );
  requireSha256(manifest.dashboard_export_sha256, 'dashboard_export_sha256');
  const actualDigest = sha256(dashboardBytes);
  if (actualDigest !== manifest.dashboard_export_sha256) {
    throw new Error(
      `Published dashboard SHA-256 mismatch: expected ${manifest.dashboard_export_sha256}, received ${actualDigest}.`,
    );
  }
  const inspection = inspectDashboardPayload(dashboardPayload);
  assertEqual(
    manifest.compact_export_schema_version,
    inspection.compact_export_schema_version,
    'manifest compact export schema version mismatch',
  );
  validateCounts(
    inspection.record_counts,
    manifest.record_counts,
    'record_counts',
  );
  validateCounts(
    inspection.definition_counts,
    manifest.definition_counts,
    'definition_counts',
  );
  assertEqual(
    inspection.source_count,
    requireCount(manifest.source_count, 'source_count'),
    'source_count mismatch',
  );
  assertNoPrivateLocalPaths(manifest);
  return { ...inspection, dashboard_export_sha256: actualDigest };
}

export function verifyPublishedBundle(destinationPath, manifestPath) {
  const dashboardBytes = readFileSync(destinationPath);
  const dashboardPayload = parseJson(dashboardBytes, 'published dashboard');
  const manifest = parseJson(
    readFileSync(manifestPath),
    'publication manifest',
  );
  return validateManifest(manifest, dashboardBytes, dashboardPayload);
}

export function verifyPromotedPublication(
  publicationPointerPath,
  destinationPath,
  manifestPath,
) {
  const pointerBytes = readFileSync(publicationPointerPath);
  const pointer = validatePointer(
    pointerBytes,
    'promoted compact-export pointer',
  );
  const { summary } = readAndValidateSummary(publicationPointerPath, pointer);
  const result = verifyPublishedBundle(destinationPath, manifestPath);
  if (result.dashboard_export_sha256 !== pointer.dashboard_export_sha256) {
    throw new Error(
      `Promoted dashboard SHA-256 mismatch: expected ${pointer.dashboard_export_sha256}, received ${result.dashboard_export_sha256}.`,
    );
  }

  const manifest = requireObject(
    parseJson(readFileSync(manifestPath), 'publication manifest'),
    'publication manifest',
  );
  assertEqual(
    manifest.source_pointer_sha256,
    sha256(pointerBytes),
    'source pointer SHA-256 mismatch',
  );
  assertEqual(
    manifest.source_summary_sha256,
    pointer.summary_sha256,
    'source summary SHA-256 mismatch',
  );
  assertEqual(
    manifest.source_run_relpath,
    pointer.run_relpath,
    'source run_relpath mismatch',
  );
  assertEqual(
    manifest.generated_at,
    pointer.generated_at,
    'publication generated_at mismatch',
  );
  assertEqual(
    manifest.source_run_generated_at,
    summary.generated_at,
    'source run generated_at mismatch',
  );
  validateCounts(result.record_counts, summary.record_counts, 'record_counts');
  validateCounts(
    result.definition_counts,
    summary.definition_counts,
    'definition_counts',
  );
  assertEqual(
    result.source_count,
    requireCount(summary.source_count, 'source_count'),
    'source_count mismatch',
  );
  assertNoPrivateLocalPaths(pointer);
  assertNoPrivateLocalPaths(summary);
  return {
    ...result,
    source_pointer_sha256: sha256(pointerBytes),
    source_run_relpath: pointer.run_relpath,
  };
}

function atomicWrite(path, bytes) {
  mkdirSync(dirname(path), { recursive: true });
  const temporaryPath = `${path}.tmp-${process.pid}-${randomUUID()}`;
  try {
    writeFileSync(temporaryPath, bytes, { flag: 'wx' });
    renameSync(temporaryPath, path);
  } catch (error) {
    try {
      unlinkSync(temporaryPath);
    } catch {
      // The staging file may not have been created.
    }
    throw error;
  }
}

function validatePointer(pointerBytes, label = 'compact-export pointer') {
  const pointer = requireObject(parseJson(pointerBytes, label), label);
  if (
    typeof pointer.run_relpath !== 'string' ||
    !SAFE_RUN_RELPATH.test(pointer.run_relpath)
  ) {
    throw new Error(
      `Unsafe compact-export run_relpath: ${String(pointer.run_relpath)}.`,
    );
  }
  requireSha256(pointer.dashboard_export_sha256, 'dashboard_export_sha256');
  requireSha256(pointer.summary_sha256, 'summary_sha256');
  assertEqual(
    pointer.compact_export_schema_version,
    EXPECTED_COMPACT_EXPORT_SCHEMA_VERSION,
    'pointer compact export schema version mismatch',
  );
  return pointer;
}

function readAndValidateSummary(pointerPath, pointer) {
  const summaryPath = join(
    dirname(pointerPath),
    pointer.run_relpath,
    'summary.json',
  );
  const summaryBytes = readFileSync(summaryPath);
  const actualSummaryDigest = sha256(summaryBytes);
  if (actualSummaryDigest !== pointer.summary_sha256) {
    throw new Error(
      `Compact export summary SHA-256 mismatch: expected ${pointer.summary_sha256}, received ${actualSummaryDigest}.`,
    );
  }
  const summary = requireObject(
    parseJson(summaryBytes, 'compact-export summary'),
    'compact-export summary',
  );
  assertEqual(
    summary.compact_export_schema_version,
    pointer.compact_export_schema_version,
    'summary compact export schema version mismatch',
  );
  assertEqual(
    summary.dashboard_export_sha256,
    pointer.dashboard_export_sha256,
    'summary dashboard SHA-256 mismatch',
  );
  return { summary, summaryBytes };
}

function buildPublicationManifest(pointer, pointerBytes, summary, inspection) {
  return {
    publication_manifest_schema_version: PUBLICATION_MANIFEST_SCHEMA_VERSION,
    compact_export_schema_version: inspection.compact_export_schema_version,
    source_run_relpath: pointer.run_relpath,
    generated_at: pointer.generated_at,
    dashboard_export_sha256: pointer.dashboard_export_sha256,
    record_counts: inspection.record_counts,
    definition_counts: inspection.definition_counts,
    source_count: inspection.source_count,
    source_pointer_sha256: sha256(pointerBytes),
    source_summary_sha256: pointer.summary_sha256,
    source_run_generated_at: summary.generated_at,
  };
}

export function syncDashboardBundle(
  pointerPath,
  destinationPath,
  manifestPath,
  publicationPointerPath,
) {
  const pointerBytes = readFileSync(pointerPath);
  const pointer = validatePointer(pointerBytes);

  const runDirectory = join(dirname(pointerPath), pointer.run_relpath);
  const { summary, summaryBytes } = readAndValidateSummary(
    pointerPath,
    pointer,
  );

  const dashboardBytes = readFileSync(
    join(runDirectory, 'dashboard_export.json'),
  );
  const actualDashboardDigest = sha256(dashboardBytes);
  if (actualDashboardDigest !== pointer.dashboard_export_sha256) {
    throw new Error(
      `Dashboard export SHA-256 mismatch: expected ${pointer.dashboard_export_sha256}, received ${actualDashboardDigest}.`,
    );
  }
  const dashboardPayload = parseJson(dashboardBytes, 'dashboard export');
  const inspection = inspectDashboardPayload(dashboardPayload);
  validateCounts(
    inspection.record_counts,
    summary.record_counts,
    'record_counts',
  );
  validateCounts(
    inspection.definition_counts,
    summary.definition_counts,
    'definition_counts',
  );
  assertEqual(
    inspection.source_count,
    requireCount(summary.source_count, 'source_count'),
    'source_count mismatch',
  );

  const manifest = buildPublicationManifest(
    pointer,
    pointerBytes,
    summary,
    inspection,
  );
  const manifestBytes = Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`);
  validateManifest(manifest, dashboardBytes, dashboardPayload);
  const publicationSummaryPath = join(
    dirname(publicationPointerPath),
    pointer.run_relpath,
    'summary.json',
  );
  atomicWrite(publicationSummaryPath, summaryBytes);
  atomicWrite(publicationPointerPath, pointerBytes);
  atomicWrite(destinationPath, dashboardBytes);
  atomicWrite(manifestPath, manifestBytes);
  return { ...inspection, dashboard_export_sha256: actualDashboardDigest };
}

function optionValue(arguments_, flag, fallback) {
  const index = arguments_.indexOf(flag);
  if (index === -1) return fallback;
  const value = arguments_[index + 1];
  if (!value || value.startsWith('--')) {
    throw new Error(`${flag} requires a file path.`);
  }
  return resolve(value);
}

function runCli(arguments_) {
  const destinationPath = optionValue(
    arguments_,
    '--destination',
    defaultDestinationPath,
  );
  const manifestPath = optionValue(
    arguments_,
    '--manifest',
    defaultManifestPath,
  );
  const publicationPointerPath = optionValue(
    arguments_,
    '--publication-pointer',
    defaultPublicationPointerPath,
  );
  if (arguments_.includes('--verify')) {
    const result = verifyPromotedPublication(
      publicationPointerPath,
      destinationPath,
      manifestPath,
    );
    process.stdout.write(
      `Promoted publication verified: ${result.dashboard_export_sha256}\n`,
    );
    return;
  }
  const pointerPath = optionValue(arguments_, '--pointer', defaultPointerPath);
  const result = syncDashboardBundle(
    pointerPath,
    destinationPath,
    manifestPath,
    publicationPointerPath,
  );
  process.stdout.write(
    `Dashboard publication bundle synchronized and verified: ${result.dashboard_export_sha256}\n`,
  );
}

const invokedPath = process.argv[1]
  ? pathToFileURL(resolve(process.argv[1])).href
  : '';
if (invokedPath === import.meta.url) {
  try {
    runCli(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`Publication data error: ${error.message}\n`);
    process.exitCode = 1;
  }
}
