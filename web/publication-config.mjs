const SAFE_SEGMENT = /^[A-Za-z0-9._~-]+$/u;

export function normalizeBasePath(value = '') {
  if (value === '' || value === '/') return '';
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.endsWith('/') ||
    value.includes('\\') ||
    value.includes('?') ||
    value.includes('#')
  ) {
    throw new Error(`Invalid GitHub Pages base path: ${String(value)}`);
  }

  const segments = value.slice(1).split('/');
  if (
    segments.length === 0 ||
    segments.some(
      (segment) =>
        segment.length === 0 ||
        segment === '.' ||
        segment === '..' ||
        !SAFE_SEGMENT.test(segment),
    )
  ) {
    throw new Error(`Invalid GitHub Pages base path: ${value}`);
  }
  return value;
}

export function publicAssetPath(assetPath, basePath = '') {
  if (
    typeof assetPath !== 'string' ||
    !assetPath.startsWith('/') ||
    assetPath.startsWith('//') ||
    assetPath.includes('\\') ||
    assetPath.split('/').includes('..')
  ) {
    throw new Error(`Invalid public asset path: ${String(assetPath)}`);
  }
  return `${normalizeBasePath(basePath)}${assetPath}`;
}

export function normalizeSiteUrl(value = '') {
  if (value === '') return '';
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`Invalid publication site URL: ${String(value)}`);
  }
  if (
    url.protocol !== 'https:' ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new Error(`Invalid publication site URL: ${value}`);
  }
  const pathname = url.pathname === '/' ? '' : url.pathname.replace(/\/$/u, '');
  return `${url.origin}${pathname}`;
}

export function publicAssetUrl(assetPath, basePath = '', siteUrl = '') {
  const normalizedBasePath = normalizeBasePath(basePath);
  const normalizedSiteUrl = normalizeSiteUrl(siteUrl);
  const path = publicAssetPath(assetPath, normalizedBasePath);
  if (!normalizedSiteUrl) return path;
  const parsedSiteUrl = new URL(normalizedSiteUrl);
  const sitePath = parsedSiteUrl.pathname === '/' ? '' : parsedSiteUrl.pathname;
  if (sitePath !== normalizedBasePath) {
    throw new Error(
      `Publication site URL path ${sitePath || '/'} does not match base path ${normalizedBasePath || '/'}.`,
    );
  }
  return `${parsedSiteUrl.origin}${path}`;
}
