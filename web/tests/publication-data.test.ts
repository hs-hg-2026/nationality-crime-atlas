import { createHash } from 'node:crypto';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { afterEach, describe, expect, it } from 'vitest';

const temporaryDirectories: string[] = [];
const webRoot = process.cwd();
const scriptPath = join(webRoot, 'scripts/sync-dashboard-export.mjs');
const checkedInDashboardPath = join(
  webRoot,
  'public/data/dashboard_export.json',
);
const checkedInManifestPath = join(
  webRoot,
  'public/data/dashboard_export.manifest.json',
);

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

function makeTemporaryDirectory(): string {
  const directory = mkdtempSync(join(tmpdir(), 'nca-publication-data-test-'));
  temporaryDirectories.push(directory);
  return directory;
}

function runScript(arguments_: string[]) {
  return spawnSync(process.execPath, [scriptPath, ...arguments_], {
    cwd: webRoot,
    encoding: 'utf8',
  });
}

function sha256(bytes: Buffer | string): string {
  return createHash('sha256').update(bytes).digest('hex');
}

function makeCompactSource(directory: string) {
  const manifest = JSON.parse(readFileSync(checkedInManifestPath, 'utf8'));
  const compactRoot = join(directory, 'compact_export');
  const runDirectory = join(compactRoot, manifest.source_run_relpath);
  mkdirSync(runDirectory, { recursive: true });
  const dashboardBytes = readFileSync(checkedInDashboardPath);
  const summary = {
    compact_export_schema_version: manifest.compact_export_schema_version,
    dashboard_export_sha256: sha256(dashboardBytes),
    definition_counts: manifest.definition_counts,
    generated_at: manifest.source_run_generated_at,
    record_counts: manifest.record_counts,
    source_count: manifest.source_count,
  };
  const summaryBytes = Buffer.from(`${JSON.stringify(summary, null, 2)}\n`);
  const pointer = {
    compact_export_schema_version: manifest.compact_export_schema_version,
    dashboard_export_sha256: sha256(dashboardBytes),
    generated_at: manifest.generated_at,
    run_relpath: manifest.source_run_relpath,
    summary_sha256: sha256(summaryBytes),
  };
  const pointerPath = join(compactRoot, 'latest.json');
  const summaryPath = join(runDirectory, 'summary.json');
  const dashboardPath = join(runDirectory, 'dashboard_export.json');
  writeFileSync(pointerPath, `${JSON.stringify(pointer, null, 2)}\n`);
  writeFileSync(summaryPath, summaryBytes);
  writeFileSync(dashboardPath, dashboardBytes);
  return { dashboardPath, pointerPath, summaryPath };
}

function writeHashClosedDashboard(
  source: ReturnType<typeof makeCompactSource>,
  payload: unknown,
): void {
  const dashboardBytes = Buffer.from(`${JSON.stringify(payload, null, 2)}\n`);
  writeFileSync(source.dashboardPath, dashboardBytes);

  const summary = JSON.parse(readFileSync(source.summaryPath, 'utf8'));
  summary.dashboard_export_sha256 = sha256(dashboardBytes);
  const summaryBytes = Buffer.from(`${JSON.stringify(summary, null, 2)}\n`);
  writeFileSync(source.summaryPath, summaryBytes);

  const pointer = JSON.parse(readFileSync(source.pointerPath, 'utf8'));
  pointer.dashboard_export_sha256 = sha256(dashboardBytes);
  pointer.summary_sha256 = sha256(summaryBytes);
  writeFileSync(source.pointerPath, `${JSON.stringify(pointer, null, 2)}\n`);
}

function addClearancePopulationFixture(payload: Record<string, any>): void {
  const trendId = 'national_clearance_population_reference_ratio';
  const uiCaveat =
    '1年間の刑法犯検挙件数または検挙人員を、10月1日の日本人人口または12月31日の在留外国人数で単純に割った公表統計由来の参考比率である。犯罪統計の分子から居住者だけを識別できず、特に「外国人全体」と在留外国人人口の対象範囲は一致しない。犯罪を行う確率や公的な犯罪率を示さない。';
  payload.compact_export_schema_version = 8;
  payload.publication_policy.clearance_population_view = trendId;
  payload.definitions.clearance_population_ids = {
    [trendId]: {
      clearance_population_trend_schema_version: 1,
      display_multiplier: 1000,
      display_unit_label_ja: '人口1,000人当たり',
      interpretation_policy: 'public_data_reference_ratio_not_probability',
      label_en: 'Criminal-code clearances per 1,000 reference population',
      label_ja: '人口1,000人当たりの刑法犯検挙参考比率',
      ui_caveat: uiCaveat,
    },
  };
  payload.sources.S19_2024 = {
    ...payload.sources.S17,
    dataset: 'Resident foreign population by nationality/region',
    series_id: 'resident_foreigner_population',
    source_period: '2024-12-31',
    source_table: '1',
  };

  const metrics = ['cleared_cases', 'cleared_persons'];
  payload.records.clearance_population_trends = metrics.flatMap((metric) => {
    const share = payload.records.clearance_share_trends.find(
      (row: Record<string, unknown>) =>
        row.year === 2024 &&
        row.metric === metric &&
        row.foreign_scope === 'all_foreign',
    );
    const allPerson = share.denominator_value;
    const allForeign = share.numerator_value;
    const japanese = allPerson - allForeign;
    const metricLabel = metric === 'cleared_cases' ? '検挙件数' : '検挙人員';
    const clearanceColumn = metric === 'cleared_cases' ? 5 : 6;
    const foreignColumn = metric === 'cleared_cases' ? 7 : 8;
    const japanesePopulation = 120_296_000;
    const foreignPopulation = 3_768_977;
    const common = {
      trend_id: trendId,
      year: 2024,
      metric,
      metric_label_ja: metricLabel,
      display_multiplier: 1000,
      display_unit_label_ja: '人口1,000人当たり',
      calculation_status: 'calculated',
      refusal_reason: null,
    };
    return [
      {
        ...common,
        population_group: 'japanese_etc_residual',
        population_group_label_ja: '日本人等（全国総数−外国人全体の残差）',
        numerator_value: japanese,
        denominator_value: japanesePopulation,
        quotient: japanese / japanesePopulation,
        display_value: (japanese / japanesePopulation) * 1000,
        numerator_source_ids: ['S15', 'S08'],
        denominator_source_id: 'S17',
        population_reference_date: '2024-10-01',
        population_scope: 'japanese_population',
        denominator_rounding: 'nearest_1000_persons',
        derivation_method:
          'arithmetic_residual_all_person_minus_all_foreign_division',
        derivation_formula: `(S15.${metric} - S08.${metric}) / S17.population * 1000`,
        source_components: [
          {
            source_id: 'S15',
            source_table: '3',
            source_sheet: '刑法犯総数',
            source_row: 18,
            source_column: clearanceColumn,
            metric,
            value: allPerson,
            role: 'numerator_minuend',
          },
          {
            source_id: 'S08',
            source_table: '130',
            source_sheet: '01',
            source_row: 17,
            source_column: foreignColumn,
            metric,
            value: allForeign,
            role: 'numerator_subtrahend',
          },
          {
            source_id: 'S17',
            source_table: '2',
            source_sheet: '第2表',
            source_row: 12,
            source_column: 9,
            metric: 'population',
            value: japanesePopulation,
            published_value: japanesePopulation / 1000,
            published_unit: '1000_persons',
            role: 'denominator',
          },
        ],
        mismatch_flags: [
          'annual_clearance_flow_vs_point_in_time_population_stock',
          'japanese_numerator_is_arithmetic_residual',
          'japanese_population_rounded_to_nearest_1000',
          'numerator_residency_scope_not_established',
          'october_1_population_reference_date',
          'public_data_reference_ratio_not_official_crime_rate',
        ],
      },
      {
        ...common,
        population_group: 'all_foreign',
        population_group_label_ja: '外国人全体（分母は在留外国人数）',
        numerator_value: allForeign,
        denominator_value: foreignPopulation,
        quotient: allForeign / foreignPopulation,
        display_value: (allForeign / foreignPopulation) * 1000,
        numerator_source_ids: ['S08'],
        denominator_source_id: 'S19_2024',
        population_reference_date: '2024-12-31',
        population_scope: 'resident_foreigner_population',
        denominator_rounding: 'as_published_persons',
        derivation_method: 'direct_published_count_division',
        derivation_formula: `S08.${metric} / S19_2024.population * 1000`,
        source_components: [
          {
            source_id: 'S08',
            source_table: '130',
            source_sheet: '01',
            source_row: 17,
            source_column: foreignColumn,
            metric,
            value: allForeign,
            role: 'numerator',
          },
          {
            source_id: 'S19_2024',
            source_table: '1',
            source_sheet: '24-12-01m',
            source_row: 5,
            source_column: 5,
            metric: 'population',
            value: foreignPopulation,
            published_value: foreignPopulation,
            published_unit: 'persons',
            role: 'denominator',
          },
        ],
        mismatch_flags: [
          'all_foreign_numerator_vs_resident_foreigner_denominator',
          'annual_clearance_flow_vs_point_in_time_population_stock',
          'december_31_population_reference_date',
          'numerator_residency_scope_not_established',
          'public_data_reference_ratio_not_official_crime_rate',
        ],
      },
    ];
  });
}

function writeHashClosedSchema8Dashboard(
  source: ReturnType<typeof makeCompactSource>,
  payload: Record<string, any>,
): void {
  const dashboardBytes = Buffer.from(`${JSON.stringify(payload, null, 2)}\n`);
  writeFileSync(source.dashboardPath, dashboardBytes);

  const summary = JSON.parse(readFileSync(source.summaryPath, 'utf8'));
  summary.compact_export_schema_version = 8;
  summary.dashboard_export_sha256 = sha256(dashboardBytes);
  summary.record_counts.clearance_population_trends =
    payload.records.clearance_population_trends.length;
  summary.definition_counts.clearance_population_ids = Object.keys(
    payload.definitions.clearance_population_ids,
  ).length;
  summary.source_count = Object.keys(payload.sources).length;
  const summaryBytes = Buffer.from(`${JSON.stringify(summary, null, 2)}\n`);
  writeFileSync(source.summaryPath, summaryBytes);

  const pointer = JSON.parse(readFileSync(source.pointerPath, 'utf8'));
  pointer.compact_export_schema_version = 8;
  pointer.dashboard_export_sha256 = sha256(dashboardBytes);
  pointer.summary_sha256 = sha256(summaryBytes);
  writeFileSync(source.pointerPath, `${JSON.stringify(pointer, null, 2)}\n`);
}

function syncCanonicalBundle(directory: string) {
  const source = makeCompactSource(directory);
  const destinationPath = join(directory, 'dashboard_export.json');
  const manifestPath = join(directory, 'dashboard_export.manifest.json');
  const publicationPointerPath = join(
    directory,
    'publication/compact_export/latest.json',
  );
  const result = runScript([
    '--pointer',
    source.pointerPath,
    '--publication-pointer',
    publicationPointerPath,
    '--destination',
    destinationPath,
    '--manifest',
    manifestPath,
  ]);
  return {
    destinationPath,
    manifestPath,
    publicationPointerPath,
    result,
    source,
  };
}

describe('dashboard publication bundle', () => {
  it('copies the hash-pinned compact export and its promotion record deterministically', () => {
    const directory = makeTemporaryDirectory();
    const {
      destinationPath,
      manifestPath,
      publicationPointerPath,
      result,
      source,
    } = syncCanonicalBundle(directory);

    expect(result.status, result.stderr).toBe(0);
    const pointer = JSON.parse(readFileSync(source.pointerPath, 'utf8'));
    const sourcePath = join(
      dirname(source.pointerPath),
      pointer.run_relpath,
      'dashboard_export.json',
    );
    expect(readFileSync(destinationPath)).toEqual(readFileSync(sourcePath));
    expect(readFileSync(publicationPointerPath)).toEqual(
      readFileSync(source.pointerPath),
    );
    expect(
      readFileSync(
        join(
          dirname(publicationPointerPath),
          pointer.run_relpath,
          'summary.json',
        ),
      ),
    ).toEqual(readFileSync(source.summaryPath));

    const firstManifest = readFileSync(manifestPath);
    const manifest = JSON.parse(firstManifest.toString('utf8'));
    expect(manifest).toMatchObject({
      publication_manifest_schema_version: 1,
      compact_export_schema_version: 7,
      source_run_relpath: pointer.run_relpath,
      dashboard_export_sha256: pointer.dashboard_export_sha256,
      record_counts: {
        all_resident_context: 248,
        nationality_comparison: 26,
        nationality_indicators: 290,
        clearance_share_trends: 60,
      },
      definition_counts: {
        context_ids: 4,
        indicator_ids: 10,
        nationality_comparison_ids: 1,
        clearance_share_ids: 1,
      },
      source_count: 8,
      source_pointer_sha256: sha256(readFileSync(source.pointerPath)),
    });

    const published = JSON.parse(readFileSync(destinationPath, 'utf8'));
    expect(published.publication_policy).toMatchObject({
      primary_view: 'all_resident_context',
      secondary_view: 'nationality_comparison',
      supplementary_view: 'nationality_indicators',
      clearance_share_view: 'national_criminal_code_clearance_foreign_share',
      same_year_gap_view: 'all_resident_same_year_recognition_clearance_gap',
      same_year_gap_is_unresolved_cohort: false,
    });
    const japaneseReference = published.records.nationality_comparison.find(
      (row: { is_japanese_reference?: boolean }) =>
        row.is_japanese_reference === true,
    );
    expect(japaneseReference).toMatchObject({
      display_label: '日本（残差による参考値）',
      numerator_source_ids: ['S08', 'S15'],
      denominator_source_id: 'S17',
      calculation_status: 'calculated',
    });
    const latestVisitingCases = published.records.clearance_share_trends.find(
      (row: { year?: number; metric?: string; foreign_scope?: string }) =>
        row.year === 2024 &&
        row.metric === 'cleared_cases' &&
        row.foreign_scope === 'visiting_foreign',
    );
    expect(latestVisitingCases).toMatchObject({
      numerator_value: 13_405,
      denominator_value: 287_273,
      numerator_source_id: 'S09',
      denominator_source_id: 'S15',
    });
    const latestResidualCases = published.records.clearance_share_trends.find(
      (row: { year?: number; metric?: string; foreign_scope?: string }) =>
        row.year === 2024 &&
        row.metric === 'cleared_cases' &&
        row.foreign_scope === 'all_foreign_minus_visiting_foreign',
    );
    expect(latestResidualCases).toMatchObject({
      numerator_value: 5_456,
      denominator_value: 287_273,
      numerator_source_ids: ['S08', 'S09'],
      denominator_source_id: 'S15',
      derivation_method:
        'arithmetic_residual_all_foreign_minus_visiting_foreign',
    });

    const second = syncCanonicalBundle(directory);
    expect(second.result.status, second.result.stderr).toBe(0);
    expect(readFileSync(manifestPath)).toEqual(firstManifest);
  }, 15_000);

  it('rejects tampered source bytes without changing the destination', () => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    writeFileSync(
      source.dashboardPath,
      Buffer.concat([readFileSync(source.dashboardPath), Buffer.from('\n')]),
    );
    const destinationPath = join(directory, 'published.json');
    const manifestPath = join(directory, 'published.manifest.json');
    writeFileSync(destinationPath, 'keep-existing');

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      destinationPath,
      '--manifest',
      manifestPath,
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/dashboard export SHA-256 mismatch/i);
    expect(readFileSync(destinationPath, 'utf8')).toBe('keep-existing');
    expect(existsSync(manifestPath)).toBe(false);
  });

  it('rejects path traversal in the compact-export pointer', () => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    const pointer = JSON.parse(readFileSync(source.pointerPath, 'utf8'));
    pointer.run_relpath = '../outside';
    writeFileSync(source.pointerPath, `${JSON.stringify(pointer, null, 2)}\n`);

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      join(directory, 'published.json'),
      '--manifest',
      join(directory, 'published.manifest.json'),
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/run_relpath/i);
  });

  it('detects published-data tampering in verify-only mode', () => {
    const directory = makeTemporaryDirectory();
    const {
      destinationPath,
      manifestPath,
      publicationPointerPath,
      result: syncResult,
    } = syncCanonicalBundle(directory);
    expect(syncResult.status, syncResult.stderr).toBe(0);
    writeFileSync(
      destinationPath,
      Buffer.concat([readFileSync(destinationPath), Buffer.from('\n')]),
    );

    const result = runScript([
      '--verify',
      '--publication-pointer',
      publicationPointerPath,
      '--destination',
      destinationPath,
      '--manifest',
      manifestPath,
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/published dashboard SHA-256 mismatch/i);
  });

  it('rejects an internally consistent bundle that diverges from the promoted pointer', () => {
    const directory = makeTemporaryDirectory();
    const {
      destinationPath,
      manifestPath,
      publicationPointerPath,
      result: syncResult,
    } = syncCanonicalBundle(directory);
    expect(syncResult.status, syncResult.stderr).toBe(0);
    const modifiedBytes = Buffer.concat([
      readFileSync(destinationPath),
      Buffer.from('\n'),
    ]);
    writeFileSync(destinationPath, modifiedBytes);
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
    manifest.dashboard_export_sha256 = sha256(modifiedBytes);
    writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

    const result = runScript([
      '--verify',
      '--publication-pointer',
      publicationPointerPath,
      '--destination',
      destinationPath,
      '--manifest',
      manifestPath,
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/promoted dashboard SHA-256 mismatch/i);
  });

  it('rejects an unknown source in a nationality comparison numerator', () => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    const payload = JSON.parse(readFileSync(source.dashboardPath, 'utf8'));
    payload.records.nationality_comparison[0].numerator_source_ids = [
      'UNKNOWN',
    ];
    const dashboardBytes = Buffer.from(`${JSON.stringify(payload, null, 2)}\n`);
    writeFileSync(source.dashboardPath, dashboardBytes);

    const summary = JSON.parse(readFileSync(source.summaryPath, 'utf8'));
    summary.dashboard_export_sha256 = sha256(dashboardBytes);
    const summaryBytes = Buffer.from(`${JSON.stringify(summary, null, 2)}\n`);
    writeFileSync(source.summaryPath, summaryBytes);

    const pointer = JSON.parse(readFileSync(source.pointerPath, 'utf8'));
    pointer.dashboard_export_sha256 = sha256(dashboardBytes);
    pointer.summary_sha256 = sha256(summaryBytes);
    writeFileSync(source.pointerPath, `${JSON.stringify(pointer, null, 2)}\n`);

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      join(directory, 'published.json'),
      '--manifest',
      join(directory, 'published.manifest.json'),
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/nationality_comparison.*unknown/i);
  });

  it.each([
    'scope_source_binding',
    'residual_label',
    'required_warnings',
    'source_components',
    'interpretation_policy',
    'ui_caveat',
    'metric_label',
    'source_coordinates',
  ])('rejects unsafe clearance-share semantics: %s', (mutation) => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    const payload = JSON.parse(readFileSync(source.dashboardPath, 'utf8'));
    const rows: Array<Record<string, unknown>> =
      payload.records.clearance_share_trends;

    if (mutation === 'scope_source_binding') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign') {
          row.numerator_source_id = 'S09';
          row.numerator_source_ids = ['S09'];
        } else if (row.foreign_scope === 'visiting_foreign') {
          row.numerator_source_id = 'S08';
          row.numerator_source_ids = ['S08'];
        } else {
          row.numerator_source_id = 'S09';
          row.numerator_source_ids = ['S09', 'S08'];
        }
      }
    } else if (mutation === 'residual_label') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          row.foreign_scope_label_ja = '在留外国人';
        }
      }
    } else if (mutation === 'required_warnings') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          row.mismatch_flags = [];
        }
      }
    } else if (mutation === 'source_components') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          row.source_components = [];
        }
      }
    } else if (mutation === 'interpretation_policy') {
      payload.definitions.clearance_share_ids[
        'national_criminal_code_clearance_foreign_share'
      ].interpretation_policy = 'population_crime_rate';
    } else if (mutation === 'ui_caveat') {
      payload.definitions.clearance_share_ids[
        'national_criminal_code_clearance_foreign_share'
      ].ui_caveat = '在留外国人の犯罪率を示す。';
    } else if (mutation === 'metric_label') {
      for (const row of rows) {
        row.metric_label_ja = '犯罪率';
      }
    } else if (mutation === 'source_coordinates') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          const components = row.source_components as Array<
            Record<string, unknown>
          >;
          components[0].source_table = '999';
          components[0].source_row = 999;
        }
      }
    }
    writeHashClosedDashboard(source, payload);

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      join(directory, 'published.json'),
      '--manifest',
      join(directory, 'published.manifest.json'),
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/clearance-share semantic contract/i);
  });

  it('accepts provenance-bound clearance population reference trends', () => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    const payload = JSON.parse(readFileSync(source.dashboardPath, 'utf8'));
    addClearancePopulationFixture(payload);
    writeHashClosedSchema8Dashboard(source, payload);

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      join(directory, 'published.json'),
      '--manifest',
      join(directory, 'published.manifest.json'),
    ]);

    expect(result.status, result.stderr).toBe(0);
  });

  it.each([
    'group_label',
    'source_binding',
    'required_warnings',
    'interpretation_policy',
    'source_coordinates',
    'population_reference_date',
    'metric_label',
    'formula',
  ])('rejects unsafe clearance-population semantics: %s', (mutation) => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    const payload = JSON.parse(readFileSync(source.dashboardPath, 'utf8'));
    addClearancePopulationFixture(payload);
    const rows: Array<Record<string, any>> =
      payload.records.clearance_population_trends;
    const target = rows.find(
      (row) =>
        row.year === 2024 &&
        row.population_group === 'all_foreign' &&
        row.metric === 'cleared_cases',
    );
    if (!target) throw new Error('Clearance-population test row is missing.');

    if (mutation === 'group_label') {
      target.population_group_label_ja = '在留外国人の犯罪率';
    } else if (mutation === 'source_binding') {
      target.numerator_source_ids = ['S15'];
    } else if (mutation === 'required_warnings') {
      target.mismatch_flags = [];
    } else if (mutation === 'interpretation_policy') {
      payload.definitions.clearance_population_ids[
        'national_clearance_population_reference_ratio'
      ].interpretation_policy = 'official_population_crime_probability';
    } else if (mutation === 'source_coordinates') {
      target.source_components[1].source_row = 999;
    } else if (mutation === 'population_reference_date') {
      target.population_reference_date = '2024-10-01';
    } else if (mutation === 'metric_label') {
      target.metric_label_ja = '犯罪率';
    } else if (mutation === 'formula') {
      target.derivation_formula = 'S08.cleared_cases / S15.population';
    }
    writeHashClosedSchema8Dashboard(source, payload);

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      join(directory, 'published.json'),
      '--manifest',
      join(directory, 'published.manifest.json'),
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/clearance-population semantic contract/i);
  });

  it.each([
    '/Users/example/private-project',
    '/private/var/folders/example/build.json',
    '/tmp/nca/result.json',
    '/workspace/nca/result.json',
    '/opt/local/nca/result.json',
    'C:\\Users\\example\\private-project',
  ])('rejects a private local path before publication: %s', (privatePath) => {
    const directory = makeTemporaryDirectory();
    const source = makeCompactSource(directory);
    const payload = JSON.parse(readFileSync(source.dashboardPath, 'utf8'));
    payload.debug_path = privatePath;
    const dashboardBytes = Buffer.from(`${JSON.stringify(payload, null, 2)}\n`);
    writeFileSync(source.dashboardPath, dashboardBytes);

    const summary = JSON.parse(readFileSync(source.summaryPath, 'utf8'));
    summary.dashboard_export_sha256 = sha256(dashboardBytes);
    const summaryBytes = Buffer.from(`${JSON.stringify(summary, null, 2)}\n`);
    writeFileSync(source.summaryPath, summaryBytes);

    const pointer = JSON.parse(readFileSync(source.pointerPath, 'utf8'));
    pointer.dashboard_export_sha256 = sha256(dashboardBytes);
    pointer.summary_sha256 = sha256(summaryBytes);
    writeFileSync(source.pointerPath, `${JSON.stringify(pointer, null, 2)}\n`);

    const result = runScript([
      '--pointer',
      source.pointerPath,
      '--publication-pointer',
      join(directory, 'publication/compact_export/latest.json'),
      '--destination',
      join(directory, 'published.json'),
      '--manifest',
      join(directory, 'published.manifest.json'),
    ]);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/private local path/i);
  });

  it('verifies checked-in data against the tracked promotion record', () => {
    const result = runScript(['--verify']);

    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toMatch(/promoted publication verified/i);
  });
});
