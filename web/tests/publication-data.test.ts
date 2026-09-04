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
      compact_export_schema_version: 5,
      source_run_relpath: pointer.run_relpath,
      dashboard_export_sha256: pointer.dashboard_export_sha256,
      record_counts: {
        all_resident_context: 248,
        nationality_comparison: 26,
        nationality_indicators: 290,
      },
      definition_counts: {
        context_ids: 4,
        indicator_ids: 10,
        nationality_comparison_ids: 1,
      },
      source_count: 8,
      source_pointer_sha256: sha256(readFileSync(source.pointerPath)),
    });

    const published = JSON.parse(readFileSync(destinationPath, 'utf8'));
    expect(published.publication_policy).toMatchObject({
      primary_view: 'all_resident_context',
      secondary_view: 'nationality_comparison',
      supplementary_view: 'nationality_indicators',
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
