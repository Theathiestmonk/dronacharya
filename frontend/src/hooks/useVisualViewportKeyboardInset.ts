'use client';

import { useEffect, useState } from 'react';

/**
 * Height (px) of the screen region covered by the virtual keyboard / browser chrome,
 * derived from the Visual Viewport API. Use margin-bottom on the chat input dock on the
 * standalone app. When embedded in an iframe, Chatbot sets margin to 0 and the parent
 * page should lift `.prakriti-chat-embed` (see embed doc §2b) to avoid double offset / gap.
 *
 * Always-on: overlap is 0 when no keyboard; avoids classifying large phones / tablet
 * landscape as “desktop” and skipping the inset.
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

    /** Focus/blur on inputs: mobile Safari sometimes lags viewport events until next frame */
    const onFocusFlow = () => {
      requestAnimationFrame(() => {
        update();
        requestAnimationFrame(update);
      });
    };

    update();
    vv.addEventListener('resize', update);
    vv.addEventListener('scroll', update);
    window.addEventListener('resize', update);
    document.addEventListener('focusin', onFocusFlow);
    document.addEventListener('focusout', onFocusFlow);

    return () => {
      vv.removeEventListener('resize', update);
      vv.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      document.removeEventListener('focusin', onFocusFlow);
      document.removeEventListener('focusout', onFocusFlow);
    };
  }, [enabled]);

  return inset;
}
