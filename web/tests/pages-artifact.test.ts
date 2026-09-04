import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { afterEach, describe, expect, it } from 'vitest';

const temporaryDirectories: string[] = [];
const webRoot = process.cwd();
const prepareScriptPath = join(webRoot, 'scripts/prepare-pages-artifact.mjs');
const verifierPath = join(webRoot, 'scripts/verify-pages-artifact.mjs');

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

function makeArtifact(indexHtml: string): string {
  const directory = mkdtempSync(join(tmpdir(), 'nca-pages-artifact-test-'));
  temporaryDirectories.push(directory);
  mkdirSync(join(directory, 'data'), { recursive: true });
  mkdirSync(join(directory, '_next/static'), { recursive: true });
  writeFileSync(join(directory, '.nojekyll'), '');
  writeFileSync(join(directory, 'index.html'), indexHtml);
  writeFileSync(join(directory, 'og.png'), 'test-image');
  writeFileSync(join(directory, 'favicon.svg'), '<svg></svg>');
  writeFileSync(join(directory, '_next/static/app.js'), 'export {};');

  writeFileSync(
    join(directory, 'data/dashboard_export.json'),
    readFileSync(join(webRoot, 'public/data/dashboard_export.json')),
  );
  writeFileSync(
    join(directory, 'data/dashboard_export.manifest.json'),
    readFileSync(join(webRoot, 'public/data/dashboard_export.manifest.json')),
  );
  return directory;
}

function verify(directory: string) {
  return spawnSync(
    process.execPath,
    [
      verifierPath,
      '--directory',
      directory,
      '--base-path',
      '/nationality-crime-atlas',
      '--site-url',
      'https://hs-hg-2026.github.io/nationality-crime-atlas',
    ],
    { cwd: webRoot, encoding: 'utf8' },
  );
}

describe('GitHub Pages artifact contract', () => {
  it('accepts a complete artifact whose URLs use the project base path', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );

    const result = verify(directory);

    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toMatch(/Pages artifact verified/i);
  });

  it('rejects root-relative framework URLs for a project-site deployment', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="/og.png"></head><body><script src="/_next/static/app.js"></script></body></html>',
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/outside configured base path/i);
  });

  it('rejects an artifact whose publication bundle no longer matches its manifest', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );
    writeFileSync(
      join(directory, 'data/dashboard_export.json'),
      Buffer.concat([
        readFileSync(join(directory, 'data/dashboard_export.json')),
        Buffer.from('\n'),
      ]),
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/published dashboard SHA-256 mismatch/i);
  });

  it('rejects a private filesystem path embedded in compiled text', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );
    writeFileSync(
      join(directory, '_next/static/app.js'),
      'const buildPath = "/private/var/folders/example/project";',
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/private local path/i);
  });

  it('accepts escaped Unicode-regex fragments in compiled text', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );
    writeFileSync(
      join(directory, '_next/static/app.js'),
      'const pattern = "[\\\\u0000-\\\\u001F \\\\u200B\\\\uFEFF]*";',
    );

    const result = verify(directory);

    expect(result.status, result.stderr).toBe(0);
  });

  it('still rejects a complete UNC filesystem path', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );
    const compiledText = String.raw`const buildPath = "\\builder\private-build\artifact";`;
    writeFileSync(join(directory, '_next/static/app.js'), compiledText);

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/private local path/i);
  });

  it('promotes vinext prefixed assets to the Pages artifact root', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );
    const prefixedDirectory = join(directory, 'nationality-crime-atlas');
    mkdirSync(prefixedDirectory);
    renameSync(join(directory, '_next'), join(prefixedDirectory, '_next'));

    const result = spawnSync(
      process.execPath,
      [
        prepareScriptPath,
        '--directory',
        directory,
        '--base-path',
        '/nationality-crime-atlas',
      ],
      { cwd: webRoot, encoding: 'utf8' },
    );

    expect(result.status, result.stderr).toBe(0);
    expect(existsSync(join(directory, '_next/static/app.js'))).toBe(true);
    expect(existsSync(prefixedDirectory)).toBe(false);
  });

  it('refuses to overwrite a colliding root asset tree', () => {
    const directory = makeArtifact(
      '<html><head><meta property="og:image" content="https://hs-hg-2026.github.io/nationality-crime-atlas/og.png"></head><body><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>',
    );
    const nestedAssets = join(
      directory,
      'nationality-crime-atlas/_next/static',
    );
    mkdirSync(nestedAssets, { recursive: true });
    writeFileSync(join(nestedAssets, 'other.js'), 'export {};');

    const result = spawnSync(
      process.execPath,
      [
        prepareScriptPath,
        '--directory',
        directory,
        '--base-path',
        '/nationality-crime-atlas',
      ],
      { cwd: webRoot, encoding: 'utf8' },
    );

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/refusing to overwrite/i);
  });
});
