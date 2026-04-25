import createNextIntlPlugin from 'next-intl/plugin';
import withBundleAnalyzer from '@next/bundle-analyzer';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const _require = createRequire(import.meta.url);

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const withAnalyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
});

// npm workspaces hoists these to the repo root — resolve them so both
// Turbopack (relative path from CWD) and webpack (absolute path) can find them.
const workspaceRoot = resolve(__dirname, '..');
const hoistedPackages = ['react-pdf', 'pdfjs-dist', 'docx-preview', 'react-markdown', 'remark-gfm'];

const turboAlias = Object.fromEntries(
  hoistedPackages.map((pkg) => [pkg, `../node_modules/${pkg}`])
);

const webpackAlias = Object.fromEntries(
  hoistedPackages.map((pkg) => [pkg, resolve(workspaceRoot, 'node_modules', pkg)])
);

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    resolveAlias: turboAlias,
  },
  output: 'standalone',
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    Object.assign(config.resolve.alias, webpackAlias);
    return config;
  },
};

export default withAnalyzer(withNextIntl(nextConfig));
