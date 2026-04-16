'use client';

import { useEffect, useState } from 'react';

/**
 * Height (px) of the screen region covered by the virtual keyboard / browser chrome,
 * derived from the Visual Viewport API. Use margin-bottom on the chat input dock so
 * the field stays above the keyboard (including inside cross-origin iframes).
 */
export function useVisualViewportKeyboardInset(enabled: boolean): number {
  const [inset, setInset] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setInset(0);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    const vv = window.visualViewport;
    if (!vv) return;

    const update = () => {
      const layoutH = window.innerHeight;
      const visibleBottom = vv.offsetTop + vv.height;
      const overlap = Math.max(0, layoutH - visibleBottom);
      setInset(overlap);
    };

    update();
    vv.addEventListener('resize', update);
    vv.addEventListener('scroll', update);
    window.addEventListener('resize', update);

    return () => {
      vv.removeEventListener('resize', update);
      vv.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, [enabled]);

  return inset;
}
