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
const siteUrl = 'https://hs-hg-2026.github.io/nationality-crime-atlas/';
const siteName = '日本の犯罪統計アトラス';
const pageTitle =
  '日本の犯罪統計アトラス｜公表犯罪統計と人口統計を可視化';
const description =
  '警察庁などが公表した日本の犯罪統計と人口統計を、地域・国籍等・犯罪種別・時系列で、出典・定義の違い・未算出理由とともに比較する可視化サイト。';

function validIndexHtml(): string {
  return `<html lang="ja"><head><title>${pageTitle}</title><meta name="description" content="${description}"><meta name="robots" content="index, follow"><link rel="canonical" href="${siteUrl}"><meta property="og:site_name" content="${siteName}"><meta property="og:title" content="${pageTitle}"><meta property="og:description" content="${description}"><meta property="og:url" content="${siteUrl}"><meta property="og:image" content="${siteUrl}og.png"></head><body><h1>${siteName}</h1><script src="/nationality-crime-atlas/_next/static/app.js"></script></body></html>`;
}

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
  writeFileSync(
    join(directory, 'sitemap.xml'),
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${siteUrl}</loc></url></urlset>`,
  );
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
      siteUrl,
    ],
    { cwd: webRoot, encoding: 'utf8' },
  );
}

describe('GitHub Pages artifact contract', () => {
  it('accepts a complete artifact whose URLs use the project base path', () => {
    const directory = makeArtifact(validIndexHtml());

    const result = verify(directory);

    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toMatch(/Pages artifact verified/i);
  });

  it('rejects root-relative framework URLs for a project-site deployment', () => {
    const directory = makeArtifact(
      validIndexHtml()
        .replace(`${siteUrl}og.png`, '/og.png')
        .replace('/nationality-crime-atlas/_next/', '/_next/'),
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/outside configured base path/i);
  });

  it('rejects an artifact whose publication bundle no longer matches its manifest', () => {
    const directory = makeArtifact(validIndexHtml());
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
    const directory = makeArtifact(validIndexHtml());
    writeFileSync(
      join(directory, '_next/static/app.js'),
      'const buildPath = "/private/var/folders/example/project";',
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/private local path/i);
  });

  it('accepts escaped Unicode-regex fragments in compiled text', () => {
    const directory = makeArtifact(validIndexHtml());
    writeFileSync(
      join(directory, '_next/static/app.js'),
      'const pattern = "[\\\\u0000-\\\\u001F \\\\u200B\\\\uFEFF]*";',
    );

    const result = verify(directory);

    expect(result.status, result.stderr).toBe(0);
  });

  it('still rejects a complete UNC filesystem path', () => {
    const directory = makeArtifact(validIndexHtml());
    const compiledText = String.raw`const buildPath = "\\builder\private-build\artifact";`;
    writeFileSync(join(directory, '_next/static/app.js'), compiledText);

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/private local path/i);
  });

  it('rejects an artifact without the canonical sitemap', () => {
    const directory = makeArtifact(validIndexHtml());
    rmSync(join(directory, 'sitemap.xml'));

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/sitemap\.xml/i);
  });

  it('rejects an artifact whose canonical URL is missing', () => {
    const directory = makeArtifact(
      validIndexHtml().replace(
        `<link rel="canonical" href="${siteUrl}">`,
        '',
      ),
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/canonical/i);
  });

  it('rejects an artifact that retains the old generic site name', () => {
    const directory = makeArtifact(
      validIndexHtml().replaceAll(siteName, '全国犯罪統計地図'),
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/site name|title/i);
  });

  it('rejects an artifact that asks crawlers not to index the page', () => {
    const directory = makeArtifact(
      validIndexHtml().replace('content="index, follow"', 'content="noindex"'),
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/robots|index/i);
  });

  it('rejects a sitemap that names a different canonical page', () => {
    const directory = makeArtifact(validIndexHtml());
    writeFileSync(
      join(directory, 'sitemap.xml'),
      '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.test/</loc></url></urlset>',
    );

    const result = verify(directory);

    expect(result.status).not.toBe(0);
    expect(result.stderr).toMatch(/sitemap|canonical/i);
  });

  it('promotes vinext prefixed assets to the Pages artifact root', () => {
    const directory = makeArtifact(validIndexHtml());
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
    const directory = makeArtifact(validIndexHtml());
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
