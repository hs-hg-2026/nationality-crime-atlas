import {
  existsSync,
  lstatSync,
  readdirSync,
  renameSync,
  rmdirSync,
} from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { normalizeBasePath } from '../publication-config.mjs';

const scriptDirectory = fileURLToPath(new URL('.', import.meta.url));
const defaultDirectory = resolve(scriptDirectory, '../dist/client');

function optionValue(arguments_, flag, fallback) {
  const index = arguments_.indexOf(flag);
  if (index === -1) return fallback;
  const value = arguments_[index + 1];
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`${flag} requires a value.`);
  }
  return value;
}

function requireDirectory(path, label) {
  if (!existsSync(path) || !lstatSync(path).isDirectory()) {
    throw new Error(`${label} is missing: ${path}.`);
  }
}

export function preparePagesArtifact(directory, basePathValue) {
  const root = resolve(directory);
  const basePath = normalizeBasePath(basePathValue);
  requireDirectory(root, 'vinext client artifact directory');
  const targetAssets = join(root, '_next');

  if (!basePath) {
    requireDirectory(targetAssets, 'root _next asset directory');
    return { basePath, promoted: false };
  }

  const prefixedRoot = join(root, basePath.slice(1));
  const sourceAssets = join(prefixedRoot, '_next');
  requireDirectory(sourceAssets, 'prefixed vinext _next asset directory');
  if (existsSync(targetAssets)) {
    throw new Error(
      `Refusing to overwrite an existing root _next asset directory: ${targetAssets}.`,
    );
  }
  const unexpectedEntries = readdirSync(prefixedRoot).filter(
    (entry) => entry !== '_next',
  );
  if (unexpectedEntries.length > 0) {
    throw new Error(
      `Refusing to remove a non-empty vinext prefix directory; unexpected entries: ${unexpectedEntries.join(', ')}.`,
    );
  }

  renameSync(sourceAssets, targetAssets);
  rmdirSync(prefixedRoot);
  return { basePath, promoted: true };
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
  const result = preparePagesArtifact(directory, basePath);
  process.stdout.write(
    result.promoted
      ? `Pages assets promoted from ${result.basePath}/_next to the artifact root.\n`
      : 'Pages assets already use the artifact root.\n',
  );
} catch (error) {
  process.stderr.write(`Pages artifact preparation error: ${error.message}\n`);
  process.exitCode = 1;
}
