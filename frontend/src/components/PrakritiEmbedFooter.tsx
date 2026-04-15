'use client';

import React, { useEffect, useState } from 'react';

const LINKS: { label: string; href: string; separator?: boolean }[] = [
  { label: 'Schoolaroo', href: 'https://prakriti.edu.in/schoolaroo/' },
  { label: 'Prakriti Way of Learning', href: 'https://prakriti.edu.in/prakriti-way-of-learning/' },
  { label: 'Home', href: 'https://prakriti.edu.in/home/' },
  { label: 'Our Programmes', href: 'https://prakriti.edu.in/our-programmes/' },
  { label: 'Team', href: 'https://prakriti.edu.in/team/' },
  { label: '|', href: '#', separator: true },
  {
    label: 'Green School',
    href: 'https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should?utm_campaign=post&utm_medium=web&triedRedirect=true',
  },
  { label: 'Roots of All Beings', href: 'https://prakriti.edu.in/roots-of-all-beings/' },
  { label: 'Calendar', href: 'https://events.prakriti.edu.in/' },
  { label: 'Admissions', href: 'https://prakriti.edu.in/admissions/' },
  { label: 'Contact', href: 'https://prakriti.edu.in/contact/' },
];

/**
 * Shown only when the app runs inside an iframe (e.g. WordPress embed).
 * Links open in the top window so users leave the iframe to the main school site.
 */
export function PrakritiEmbedFooter() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const inIframe = typeof window !== 'undefined' && window.self !== window.top;
    setShow(inIframe);
  }, []);

  if (!show) return null;

  return (
    <nav
      className="flex-shrink-0 w-full border-t border-white/10 px-2 py-2.5 sm:py-3"
      style={{
        backgroundColor: 'var(--brand-primary)',
        fontFamily: 'Georgia, "Times New Roman", Times, serif',
      }}
      aria-label="Prakriti School links"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-2 gap-y-2 sm:gap-x-4 text-center text-[11px] leading-snug text-white sm:text-xs md:text-sm">
        {LINKS.map((item, i) =>
          item.separator ? (
            <span key={`sep-${i}`} className="select-none text-white/90" aria-hidden>
              |
            </span>
          ) : (
            <a
              key={item.href + item.label}
              href={item.href}
              target="_top"
              rel="noopener noreferrer"
              className="whitespace-nowrap text-white underline-offset-2 transition-opacity hover:opacity-90 hover:underline"
            >
              {item.label}
            </a>
          )
        )}
      </div>
    </nav>
  );
}
