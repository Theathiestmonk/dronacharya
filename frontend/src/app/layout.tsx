import './globals.css';

import { SupabaseProvider } from '../providers/SupabaseProvider';
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
  title: 'AI School Chatbot',
  description: 'AI-powered school automation system',
  icons: {
    icon: '/prakriti_logo.webp',
    shortcut: '/prakriti_logo.webp',
    apple: '/prakriti_logo.webp',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/prakriti_logo.webp" type="image/webp" />
        <link rel="shortcut icon" href="/prakriti_logo.webp" type="image/webp" />
        <link rel="apple-touch-icon" href="/prakriti_logo.webp" />
      </head>
      <body className="min-h-screen">
        <SupabaseProvider>
          <div className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
            {children}
          </div>
        </SupabaseProvider>
      </body>
    </html>
  );
}
