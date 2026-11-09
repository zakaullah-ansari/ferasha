/**
 * Frosted glass, in three strengths. Tailwind classes only, defined once:
 * every glass surface on the site comes from here.
 *
 * Glass is for things that float: over photography, over scrolling content,
 * over the dimmed page behind a dialog. Long text on glass over a busy
 * image reads badly, so each strength keeps enough of the theme's own
 * background to hold body-text contrast.
 */
export const GLASS = {
  /** Drawers, sheets and dialogs over the dimmed page. */
  panel:
    "bg-popover/80 backdrop-blur-2xl backdrop-saturate-150 border border-white/50 shadow-[0_24px_64px_-24px_rgb(0_0_0/0.35),inset_0_1px_0_rgb(255_255_255/0.6)] dark:border-white/10 dark:shadow-[0_24px_64px_-24px_rgb(0_0_0/0.6),inset_0_1px_0_rgb(255_255_255/0.08)]",
  /** Small things floating over photography: badges, captions, buttons. */
  float:
    "bg-background/60 backdrop-blur-md backdrop-saturate-150 border border-white/60 shadow-[0_6px_20px_-8px_rgb(0_0_0/0.25),inset_0_1px_0_rgb(255_255_255/0.7)] dark:bg-background/40 dark:border-white/15 dark:shadow-[inset_0_1px_0_rgb(255_255_255/0.1)]",
  /**
   * The phone buy bar: pinned over the page below md, inline (no glass) above.
   * Written out with its prefix because Tailwind only generates classes it
   * finds literally in the source.
   */
  phoneBar:
    "max-md:bg-background/70 max-md:backdrop-blur-xl max-md:backdrop-saturate-150 max-md:border-white/50 max-md:shadow-[0_-8px_24px_-12px_rgb(0_0_0/0.15),inset_0_1px_0_rgb(255_255_255/0.6)]",
} as const;
