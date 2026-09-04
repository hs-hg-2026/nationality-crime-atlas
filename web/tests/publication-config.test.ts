import { describe, expect, it } from 'vitest';

import {
  normalizeBasePath,
  normalizeSiteUrl,
  publicAssetPath,
  publicAssetUrl,
} from '../publication-config.mjs';

describe('GitHub Pages publication paths', () => {
  it('keeps root deployments at the origin root', () => {
    expect(normalizeBasePath('')).toBe('');
    expect(normalizeBasePath('/')).toBe('');
    expect(publicAssetPath('/og.png', '')).toBe('/og.png');
  });

  it('prefixes project-site assets with the exact Pages base path', () => {
    expect(normalizeBasePath('/nationality-crime-atlas')).toBe(
      '/nationality-crime-atlas',
    );
    expect(publicAssetPath('/og.png', '/nationality-crime-atlas')).toBe(
      '/nationality-crime-atlas/og.png',
    );
  });

  it.each([
    'nationality-crime-atlas',
    '/nationality-crime-atlas/',
    '/nationality-crime-atlas?preview=1',
    'https://example.test/nationality-crime-atlas',
  ])('rejects an unsafe or ambiguous base path: %s', (value) => {
    expect(() => normalizeBasePath(value)).toThrow(/base path/i);
  });

  it('rejects an asset path that is not origin-relative', () => {
    expect(() => publicAssetPath('og.png', '')).toThrow(/asset path/i);
  });

  it('builds an absolute public URL from matching Pages metadata', () => {
    const siteUrl = 'https://hs-hg-2026.github.io/nationality-crime-atlas';
    expect(normalizeSiteUrl(`${siteUrl}/`)).toBe(siteUrl);
    expect(publicAssetUrl('/og.png', '/nationality-crime-atlas', siteUrl)).toBe(
      `${siteUrl}/og.png`,
    );
  });

  it('rejects non-HTTPS or path-inconsistent publication URLs', () => {
    expect(() =>
      normalizeSiteUrl('http://hs-hg-2026.github.io/nationality-crime-atlas'),
    ).toThrow(/site URL/i);
    expect(() =>
      publicAssetUrl(
        '/og.png',
        '/nationality-crime-atlas',
        'https://hs-hg-2026.github.io/another-project',
      ),
    ).toThrow(/does not match/i);
  });
});
