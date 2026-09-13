import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { normalizeSiteUrl, publicAssetUrl } from '../publication-config.mjs';
import './globals.css';

const siteName = '日本の犯罪統計アトラス';
const title = '日本の犯罪統計アトラス｜公表犯罪統計と人口統計を可視化';
const description =
  '警察庁などが公表した日本の犯罪統計と人口統計を、地域・国籍等・犯罪種別・時系列で、出典・定義の違い・未算出理由とともに比較する可視化サイト。';
const siteUrl = normalizeSiteUrl(process.env.NEXT_PUBLIC_SITE_URL ?? '');
const canonicalUrl = `${siteUrl || 'https://hs-hg-2026.github.io/nationality-crime-atlas'}/`;
const ogImageUrl = publicAssetUrl(
  '/og.png',
  process.env.NEXT_PUBLIC_BASE_PATH ?? '',
  siteUrl,
);

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title,
  description,
  applicationName: siteName,
  metadataBase: new URL(canonicalUrl),
  alternates: {
    canonical: canonicalUrl,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
      'max-video-preview': -1,
    },
  },
  openGraph: {
    title,
    description,
    siteName,
    type: 'website',
    locale: 'ja_JP',
    url: canonicalUrl,
    images: [{ url: ogImageUrl, width: 1200, height: 630, alt: siteName }],
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
    images: [ogImageUrl],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
