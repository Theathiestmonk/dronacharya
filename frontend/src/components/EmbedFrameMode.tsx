'use client';

import { useEffect } from 'react';

/**
 * When the app runs inside an iframe (or ?embed=1), set html/body classes so
 * the UI can fill the iframe height instead of leaving empty bands.
 */
export function EmbedFrameMode() {
  useEffect(() => {
    const apply = () => {
      const inIframe =
        typeof window !== 'undefined' && window.self !== window.top;
      const embedParam =
        typeof window !== 'undefined' &&
        new URLSearchParams(window.location.search).get('embed') === '1';
      if (inIframe || embedParam) {
        document.documentElement.classList.add('is-embedded');
        document.body.classList.add('is-embedded');
      } else {
        document.documentElement.classList.remove('is-embedded');
        document.body.classList.remove('is-embedded');
      }
    };

    apply();
    return () => {
      document.documentElement.classList.remove('is-embedded');
      document.body.classList.remove('is-embedded');
    };
  }, []);

  return null;
}
