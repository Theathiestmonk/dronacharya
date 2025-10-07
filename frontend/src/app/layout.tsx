import './globals.css';

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
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/prakriti_logo.webp" type="image/webp" />
        <link rel="shortcut icon" href="/prakriti_logo.webp" type="image/webp" />
        <link rel="apple-touch-icon" href="/prakriti_logo.webp" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  // Only run on client side
                  if (typeof window === 'undefined') return;
                  
                  const savedTheme = localStorage.getItem('theme');
                  let theme = 'light';
                  
                  if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
                    theme = savedTheme;
                  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    theme = 'dark';
                  }
                  
                  // Apply theme class without causing hydration issues
                  const html = document.documentElement;
                  html.classList.remove('light', 'dark');
                  html.classList.add(theme);
                  
                  // Set a data attribute for CSS to use
                  html.setAttribute('data-theme', theme);
                  
                  // Store theme in a global variable for React to read
                  window.__INITIAL_THEME__ = theme;
                  
                  console.log('🎨 Theme script applied:', theme);
                } catch (e) {
                  console.warn('Failed to apply theme:', e);
                }
              })();
            `,
          }}
        />
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
