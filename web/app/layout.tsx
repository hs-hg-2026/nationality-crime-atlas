import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { normalizeSiteUrl, publicAssetUrl } from '../publication-config.mjs';
import './globals.css';

const title = '全国犯罪統計地図';
const description =
  '公表された犯罪統計と人口を、その定義差・出典・非公表範囲とともに比較する可視化。';
const siteUrl = normalizeSiteUrl(process.env.NEXT_PUBLIC_SITE_URL ?? '');
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
  metadataBase: siteUrl ? new URL(siteUrl) : undefined,
  openGraph: {
    title,
    description,
    type: 'website',
    locale: 'ja_JP',
    images: [{ url: ogImageUrl, width: 1200, height: 630, alt: title }],
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
