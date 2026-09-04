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

const EXPECTED_COMPACT_EXPORT_SCHEMA_VERSION = 5;
const SAME_YEAR_GAP_CONTEXT_ID =
  'all_resident_same_year_recognition_clearance_gap';
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

function validateRecordLinks(payload) {
  const indicatorDefinitions = payload.definitions.indicator_ids;
  const contextDefinitions = payload.definitions.context_ids;
  const comparisonDefinitions = payload.definitions.nationality_comparison_ids;
  const offenseDefinitions = payload.definitions.offense_composition_ids;
  const offenseCategoryDefinitions = payload.definitions.offense_category_ids;
  const sources = payload.sources;

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
