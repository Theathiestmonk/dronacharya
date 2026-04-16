'use client';

import { useEffect, useState } from 'react';

/** Tracks largest innerHeight seen in iframe (keyboard open shrinks current innerHeight). */
let iframePeakInnerHeight = 0;

/**
 * Height (px) of the screen region covered by the virtual keyboard / browser chrome,
 * derived from the Visual Viewport API. Use margin-bottom on the chat input dock so
 * the field stays above the keyboard (including inside cross-origin iframes).
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

    const postToParent = (insetBottom: number) => {
      if (typeof window === 'undefined' || window.self === window.top) return;
      try {
        window.parent.postMessage(
          {
            source: 'prakriti-chat',
            type: 'keyboard-inset',
            insetBottom: Math.round(insetBottom),
          },
          '*'
        );
      } catch {
        /* cross-origin parent may still receive postMessage */
      }
    };

    const update = () => {
      const layoutH = window.innerHeight;
      const visibleBottom = vv.offsetTop + vv.height;
      let overlap = Math.max(0, layoutH - visibleBottom);

      /** Peer: inner window height drop (helps some WebKit iframe + keyboard cases) */
      if (window.self !== window.top) {
        const ih = window.innerHeight;
        iframePeakInnerHeight = Math.max(iframePeakInnerHeight, ih);
        overlap = Math.max(overlap, iframePeakInnerHeight - ih);
      }

      setInset(overlap);
      postToParent(overlap);
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
    const onOrientation = () => {
      iframePeakInnerHeight = 0;
      update();
    };
    window.addEventListener('orientationchange', onOrientation);
    document.addEventListener('focusin', onFocusFlow);
    document.addEventListener('focusout', onFocusFlow);

    return () => {
      vv.removeEventListener('resize', update);
      vv.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      window.removeEventListener('orientationchange', onOrientation);
      document.removeEventListener('focusin', onFocusFlow);
      document.removeEventListener('focusout', onFocusFlow);
    };
  }, [enabled]);

  return inset;
}
