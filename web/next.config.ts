import type { NextConfig } from 'next';

import { normalizeBasePath } from './publication-config.mjs';

const publicationPath = normalizeBasePath(
  process.env.NEXT_PUBLIC_BASE_PATH ?? '',
);

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  // vinext beta currently sends `/` (without basePath) to its prerender RSC
  // handler. GitHub Pages mounts this single-route artifact at the project path,
  // so only static asset URLs need the Pages prefix.
  assetPrefix: publicationPath || undefined,
  images: { unoptimized: true },
};

export default nextConfig;
