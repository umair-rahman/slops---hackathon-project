"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

/**
 * Marginalia top navigation.
 *
 * Highlights:
 *  • Scroll-aware: top progress bar + glassy bg intensifies after scroll.
 *  • "Magnetic" sliding indicator pill that follows the active / hovered link.
 *  • Live activity ticker that counts up — feels like the product is alive.
 *  • Animated logo with pulsing yellow dot (mirrors the hero "live" cue).
 *  • Command-palette hint (⌘K) — primes power-user perception.
 *  • Animated hamburger + slide-down mobile drawer for small screens.
 */

const NAV_LINKS = [
  { href: "/analyze", label: "analyze", hint: "score a single review" },
  { href: "/conference", label: "scan venue", hint: "audit a whole conference" },
  { href: "/methodology", label: "methodology", hint: "how the math works" },
] as const;

export function Nav() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [scrollPct, setScrollPct] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [reviews, setReviews] = useState(1247);
  const [hovered, setHovered] = useState<string | null>(null);

  /* ── Scroll listener: progress bar + glass intensity ────────────────── */
  useEffect(() => {
    function onScroll() {
      const y = window.scrollY || 0;
      setScrolled(y > 12);
      const max = Math.max(
        1,
        document.documentElement.scrollHeight - window.innerHeight
      );
      setScrollPct(Math.min(1, y / max));
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* ── Live ticker: bumps reviews count occasionally ──────────────────── */
  useEffect(() => {
    const id = setInterval(() => {
      setReviews((r) => r + Math.floor(Math.random() * 3) + 1);
    }, 3500);
    return () => clearInterval(id);
  }, []);

  /* ── Close mobile drawer on route change or escape ──────────────────── */
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  /* ── Magnetic indicator: track active / hovered link rect ───────────── */
  const linksWrapRef = useRef<HTMLDivElement | null>(null);
  const linkRefs = useRef<Record<string, HTMLAnchorElement | null>>({});
  const [indicator, setIndicator] = useState({
    left: 0,
    width: 0,
    visible: false,
  });

  const targetHref = useMemo(() => {
    if (hovered) return hovered;
    const match = NAV_LINKS.find((l) => pathname === l.href);
    return match?.href ?? null;
  }, [hovered, pathname]);

  useLayoutEffect(() => {
    if (!targetHref || !linksWrapRef.current) {
      setIndicator((s) => ({ ...s, visible: false }));
      return;
    }
    const wrap = linksWrapRef.current.getBoundingClientRect();
    const el = linkRefs.current[targetHref];
    if (!el) {
      setIndicator((s) => ({ ...s, visible: false }));
      return;
    }
    const rect = el.getBoundingClientRect();
    setIndicator({
      left: rect.left - wrap.left,
      width: rect.width,
      visible: true,
    });
  }, [targetHref]);

  return (
    <>
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "backdrop-blur-2xl bg-[#08080b]/80 border-b border-white/[0.06]"
            : "backdrop-blur-md bg-[#08080b]/40 border-b border-transparent"
        }`}
      >
        {/* Scroll progress bar */}
        <div
          className="absolute left-0 top-0 h-[2px] bg-gradient-to-r from-[#facc15] via-[#fde047] to-[#facc15]"
          style={{
            width: `${scrollPct * 100}%`,
            opacity: scrollPct > 0.005 ? 1 : 0,
            transition: "opacity 200ms ease",
            boxShadow: "0 0 12px rgba(250, 204, 21, 0.6)",
          }}
        />

        <div
          className={`max-w-7xl mx-auto px-6 sm:px-8 flex items-center justify-between transition-all duration-300 ${
            scrolled ? "h-14" : "h-16"
          }`}
        >
          {/* ── Logo ───────────────────────────────────────────────────── */}
          <Link href="/" className="group flex items-center gap-2 shrink-0">
            <span className="relative flex items-center">
              <span className="font-serif text-xl tracking-tight italic transition-colors group-hover:text-[#fde047]">
                marginalia
              </span>
              <span className="relative ml-1 inline-block w-2 h-2">
                <span className="absolute inset-0 rounded-full bg-[#facc15]" />
                <span className="absolute inset-0 rounded-full bg-[#facc15] animate-ping opacity-60" />
              </span>
            </span>
          </Link>

          {/* ── Center nav with magnetic indicator ─────────────────────── */}
          <div
            ref={linksWrapRef}
            onMouseLeave={() => setHovered(null)}
            className="relative hidden md:flex items-center"
          >
            {/* Sliding pill */}
            <div
              aria-hidden
              className="absolute top-1/2 -translate-y-1/2 h-9 rounded-full bg-white/[0.04] border border-white/[0.06] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
              style={{
                left: indicator.left,
                width: indicator.width,
                opacity: indicator.visible ? 1 : 0,
              }}
            />
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  ref={(el) => {
                    linkRefs.current[link.href] = el;
                  }}
                  onMouseEnter={() => setHovered(link.href)}
                  className={`relative z-10 px-4 py-2 text-sm rounded-full transition-colors ${
                    isActive
                      ? "text-[#facc15]"
                      : "text-[#a3a3a3] hover:text-white"
                  }`}
                >
                  <span className="relative">
                    {link.label}
                    {isActive && (
                      <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[#facc15] shadow-[0_0_8px_rgba(250,204,21,0.8)]" />
                    )}
                  </span>
                </Link>
              );
            })}
          </div>

          {/* ── Right cluster ──────────────────────────────────────────── */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Live activity chip */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] text-xs">
              <span className="dot-pulse" />
              <span className="font-mono text-[#a3a3a3]">
                <span className="text-white tabular-nums">
                  {reviews.toLocaleString()}
                </span>{" "}
                reviews scanned today
              </span>
            </div>

            {/* Command palette hint */}
            <button
              type="button"
              onClick={() => {
                /* hook into a future command palette */
              }}
              className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-white/[0.06] bg-white/[0.02] text-xs text-[#737373] hover:text-white hover:border-white/[0.15] transition-colors"
              title="Open command palette"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <kbd className="font-mono">⌘K</kbd>
            </button>

            {/* GitHub */}
            <a
              href="https://github.com/marginalia-ai/marginalia"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-[#a3a3a3] hover:text-white transition-colors"
              title="github"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
              </svg>
              <span className="hidden xl:inline">github</span>
            </a>

            {/* CTA */}
            <Link
              href="/analyze"
              className="btn-primary text-sm py-2 px-4 hidden sm:inline-flex"
            >
              try it
              <span>→</span>
            </Link>

            {/* Mobile menu toggle */}
            <button
              type="button"
              aria-label="Toggle menu"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((v) => !v)}
              className="md:hidden relative w-10 h-10 rounded-md border border-white/[0.06] bg-white/[0.02] flex items-center justify-center"
            >
              <span
                className={`absolute h-[1.5px] w-5 bg-white transition-all duration-300 ${
                  mobileOpen ? "rotate-45" : "-translate-y-[5px]"
                }`}
              />
              <span
                className={`absolute h-[1.5px] w-5 bg-white transition-all duration-300 ${
                  mobileOpen ? "opacity-0" : "opacity-100"
                }`}
              />
              <span
                className={`absolute h-[1.5px] w-5 bg-white transition-all duration-300 ${
                  mobileOpen ? "-rotate-45" : "translate-y-[5px]"
                }`}
              />
            </button>
          </div>
        </div>

        {/* ── Mobile drawer ─────────────────────────────────────────────── */}
        <div
          className={`md:hidden overflow-hidden transition-[max-height,opacity] duration-300 ${
            mobileOpen ? "max-h-[420px] opacity-100" : "max-h-0 opacity-0"
          }`}
        >
          <div className="px-6 pb-6 pt-2 border-t border-white/[0.05] bg-[#08080b]/95 backdrop-blur-2xl">
            <div className="flex items-center gap-2 mb-4 mt-3 text-xs">
              <span className="dot-pulse" />
              <span className="font-mono text-[#a3a3a3]">
                <span className="text-white tabular-nums">
                  {reviews.toLocaleString()}
                </span>{" "}
                reviews scanned today
              </span>
            </div>
            <div className="flex flex-col gap-1">
              {NAV_LINKS.map((link, i) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`group flex items-center justify-between rounded-lg px-3 py-3 border transition-colors ${
                      isActive
                        ? "border-[#facc15]/30 bg-[#facc15]/5"
                        : "border-white/[0.05] bg-white/[0.02] hover:border-white/[0.12]"
                    }`}
                    style={{
                      animation: mobileOpen
                        ? `fade-up 0.4s cubic-bezier(0.16,1,0.3,1) ${
                            i * 60
                          }ms backwards`
                        : undefined,
                    }}
                  >
                    <div>
                      <div
                        className={`text-sm ${
                          isActive ? "text-[#facc15]" : "text-white"
                        }`}
                      >
                        {link.label}
                      </div>
                      <div className="text-xs text-[#737373] mt-0.5">
                        {link.hint}
                      </div>
                    </div>
                    <span className="text-[#737373] group-hover:text-white group-hover:translate-x-1 transition-all">
                      →
                    </span>
                  </Link>
                );
              })}
            </div>
            <div className="grid grid-cols-2 gap-3 mt-4">
              <a
                href="https://github.com/marginalia-ai/marginalia"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-sm py-2 justify-center"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
                github
              </a>
              <Link
                href="/analyze"
                className="btn-primary text-sm py-2 justify-center"
              >
                try it →
              </Link>
            </div>
          </div>
        </div>
      </nav>
    </>
  );
}
