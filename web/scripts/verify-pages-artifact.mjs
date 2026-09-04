import { lstatSync, readFileSync, readdirSync } from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  normalizeBasePath,
  normalizeSiteUrl,
  publicAssetUrl,
} from '../publication-config.mjs';
import {
  assertNoPrivateFilesystemPathsInText,
  verifyPublishedBundle,
} from './sync-dashboard-export.mjs';

const scriptDirectory = fileURLToPath(new URL('.', import.meta.url));
const defaultDirectory = resolve(scriptDirectory, '../dist/client');
const requiredFiles = [
  '.nojekyll',
  'index.html',
  'data/dashboard_export.json',
  'data/dashboard_export.manifest.json',
  'og.png',
  'favicon.svg',
];
const textExtensions = new Set([
  '.css',
  '.html',
  '.js',
  '.json',
  '.svg',
  '.txt',
]);

function optionValue(arguments_, flag, fallback) {
  const index = arguments_.indexOf(flag);
  if (index === -1) return fallback;
  const value = arguments_[index + 1];
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`${flag} requires a value.`);
  }
  return value;
}

function collectFiles(root, directory = root, files = []) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    const status = lstatSync(path);
    if (status.isSymbolicLink()) {
      throw new Error(
        `Pages artifact must not contain symlinks: ${relative(root, path)}.`,
      );
    }
    if (entry.isDirectory()) collectFiles(root, path, files);
    else if (entry.isFile()) files.push(path);
  }
  return files;
}

function assertRequiredFiles(root, files) {
  const relativeFiles = new Set(files.map((path) => relative(root, path)));
  for (const required of requiredFiles) {
    if (!relativeFiles.has(required)) {
      throw new Error(`Pages artifact is missing required file: ${required}.`);
    }
  }
  if (![...relativeFiles].some((path) => path.startsWith('_next/'))) {
    throw new Error('Pages artifact is missing compiled _next assets.');
  }
}

function attributeUrls(html) {
  return [...html.matchAll(/\b(?:content|href|src)=["']([^"']+)["']/gu)].map(
    (match) => match[1],
  );
}

function originRelativeUrls(html) {
  return attributeUrls(html).filter(
    (url) => url.startsWith('/') && !url.startsWith('//'),
  );
}

function assertBasePathUrls(html, basePath, siteUrl) {
  const urls = originRelativeUrls(html);
  if (basePath) {
    const outside = urls.find(
      (url) => url !== basePath && !url.startsWith(`${basePath}/`),
    );
    if (outside) {
      throw new Error(
        `Artifact URL is outside configured base path ${basePath}: ${outside}.`,
      );
    }
  }
  const expectedFrameworkPrefix = `${basePath}/_next/`;
  if (!urls.some((url) => url.startsWith(expectedFrameworkPrefix))) {
    throw new Error(
      `Artifact HTML does not reference compiled assets at ${expectedFrameworkPrefix}.`,
    );
  }
  const expectedOgUrl = publicAssetUrl('/og.png', basePath, siteUrl);
  if (!attributeUrls(html).includes(expectedOgUrl)) {
    throw new Error(`Artifact HTML does not reference ${expectedOgUrl}.`);
  }
  if (/https?:\/\/localhost(?::\d+)?\//u.test(html)) {
    throw new Error('Artifact HTML contains a localhost publication URL.');
  }
}

export function verifyPagesArtifact(root, basePathValue, siteUrlValue = '') {
  const resolvedRoot = resolve(root);
  const basePath = normalizeBasePath(basePathValue);
  const siteUrl = normalizeSiteUrl(siteUrlValue);
  const files = collectFiles(resolvedRoot);
  assertRequiredFiles(resolvedRoot, files);
  const html = readFileSync(join(resolvedRoot, 'index.html'), 'utf8');
  assertBasePathUrls(html, basePath, siteUrl);
  for (const path of files) {
    if (
      textExtensions.has(extname(path).toLowerCase()) ||
      path.endsWith('.nojekyll')
    ) {
      assertNoPrivateFilesystemPathsInText(readFileSync(path, 'utf8'));
    }
  }
  const data = verifyPublishedBundle(
    join(resolvedRoot, 'data/dashboard_export.json'),
    join(resolvedRoot, 'data/dashboard_export.manifest.json'),
  );
  return { basePath, siteUrl, fileCount: files.length, ...data };
}

try {
  const arguments_ = process.argv.slice(2);
  const directory = resolve(
    optionValue(arguments_, '--directory', defaultDirectory),
  );
  const basePath = optionValue(
    arguments_,
    '--base-path',
    process.env.NEXT_PUBLIC_BASE_PATH ?? '',
  );
  const siteUrl = optionValue(
    arguments_,
    '--site-url',
    process.env.NEXT_PUBLIC_SITE_URL ?? '',
  );
  const result = verifyPagesArtifact(directory, basePath, siteUrl);
  process.stdout.write(
    `Pages artifact verified: ${result.fileCount} files, base path "${result.basePath || '/'}", dashboard ${result.dashboard_export_sha256}.\n`,
  );
} catch (error) {
  process.stderr.write(`Pages artifact error: ${error.message}\n`);
  process.exitCode = 1;
}
