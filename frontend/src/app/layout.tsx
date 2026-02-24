import './globals.css';
import Script from 'next/script';

import { SupabaseProvider } from '../providers/SupabaseProvider';
import { AuthProvider } from '../providers/AuthProvider';
import type { Metadata } from 'next';
import { Geist, Geist_Mono } from "next/font/google";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: 'Prakriti School AI Assistant',
  description: 'AI-powered school automation system for Prakriti School',
  icons: {
    icon: '/prakriti_logo.webp',
    shortcut: '/prakriti_logo.webp',
    apple: '/prakriti_logo.webp',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/prakriti_logo.webp" type="image/webp" />
        <link rel="shortcut icon" href="/prakriti_logo.webp" type="image/webp" />
        <link rel="apple-touch-icon" href="/prakriti_logo.webp" />
        <meta name="theme-color" content="#23479f" />
        <Script src="https://accounts.google.com/gsi/client" strategy="beforeInteractive" />
      </head>
      <body className="min-h-screen" suppressHydrationWarning>
        <SupabaseProvider>
          <AuthProvider>
            <div className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
              {children}
            </div>
          </AuthProvider>
        </SupabaseProvider>
      </body>
    </html>
  );
}
