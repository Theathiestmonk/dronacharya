'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

/**
 * When the app runs inside an iframe, ?embed=1, or /chat (embed-friendly layout),
 * set html/body classes so the UI can fill the iframe height instead of leaving empty bands.
 */
export function EmbedFrameMode() {
  const pathname = usePathname();

  useEffect(() => {
    const apply = () => {
      const inIframe =
        typeof window !== 'undefined' && window.self !== window.top;
      const embedParam =
        typeof window !== 'undefined' &&
        new URLSearchParams(window.location.search).get('embed') === '1';
      const chatOnlyPath = pathname === '/chat';
      if (inIframe || embedParam || chatOnlyPath) {
        document.documentElement.classList.add('is-embedded');
        document.body.classList.add('is-embedded');
        if (chatOnlyPath) {
          document.documentElement.classList.add('is-chat-only');
        } else {
          document.documentElement.classList.remove('is-chat-only');
        }
      } else {
        document.documentElement.classList.remove('is-embedded');
        document.documentElement.classList.remove('is-chat-only');
        document.body.classList.remove('is-embedded');
      }
    };

    apply();
    return () => {
      document.documentElement.classList.remove('is-embedded');
      document.documentElement.classList.remove('is-chat-only');
      document.body.classList.remove('is-embedded');
    };
  }, [pathname]);

  return null;
}
