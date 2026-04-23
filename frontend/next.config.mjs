import createNextIntlPlugin from 'next-intl/plugin';
import withBundleAnalyzer from '@next/bundle-analyzer';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const withAnalyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: false,
  output: 'standalone',
  webpack: (config) => {
    // react-pdf requires the pdfjs-dist worker to be served as a static asset
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default withAnalyzer(withNextIntl(nextConfig));
