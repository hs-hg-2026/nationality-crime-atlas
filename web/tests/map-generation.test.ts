import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { afterEach, describe, expect, it } from 'vitest';

const temporaryDirectories: string[] = [];
const projectRoot = process.cwd();
const generatorPath = join(projectRoot, 'scripts/generate-japan-map-data.mjs');
const canonicalSourcePath = join(
  projectRoot,
  'assets/maps/deformed-japan-prefecture-map.svg',
);

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

function makeTemporaryDirectory(): string {
  const directory = mkdtempSync(join(tmpdir(), 'nca-map-test-'));
  temporaryDirectories.push(directory);
  return directory;
}

describe('Japan map asset generation', () => {
  it('rejects map bytes that do not match the pinned digest', () => {
    const temporaryDirectory = makeTemporaryDirectory();
    const sourcePath = join(temporaryDirectory, 'tampered-map.svg');
    const outputPath = join(temporaryDirectory, 'generated.ts');
    const canonicalSource = readFileSync(canonicalSourcePath);
    writeFileSync(
      sourcePath,
      Buffer.concat([canonicalSource, Buffer.from('\n<!-- changed -->\n')]),
    );

    const result = spawnSync(
      process.execPath,
      [generatorPath, '--source', sourcePath, '--output', outputPath],
      { encoding: 'utf8' },
    );

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/map asset SHA-256 mismatch/i);
  });

  it('regenerates the checked-in module byte-for-byte from the pinned asset', () => {
    const temporaryDirectory = makeTemporaryDirectory();
    const outputPath = join(temporaryDirectory, 'generated.ts');
    const expectedOutput = readFileSync(
      join(projectRoot, 'lib/japan-map-paths.generated.ts'),
    );

    const result = spawnSync(
      process.execPath,
      [generatorPath, '--source', canonicalSourcePath, '--output', outputPath],
      { encoding: 'utf8' },
    );

    expect(result.status).toBe(0);
    expect(readFileSync(outputPath)).toEqual(expectedOutput);
  });
});
