"use client"

import { useEffect, useState, type RefObject } from "react"

/** Taller than any page, so everything above the screen is inside the watched area. */
const PASSED_REACH = "100000px"

/**
 * True once the element has reached the screen, and it stays true.
 *
 * Unlike a plain in-view check, an element the visitor has already scrolled
 * past also counts as seen. IntersectionObserver only reports crossings, so a
 * fast fling, an anchor link or the back button can carry a short element
 * from below the screen to above it in one frame without reporting anything,
 * and reveal animations waiting on it would leave it invisible for good.
 * Stretching the watched area far upward closes that gap.
 *
 * `root: document` measures against the element's own document, so this also
 * works inside an iframe (Storybook, previews), where the implicit root is
 * the top window and the frame's edges would clip the stretched area away.
 *
 * @param bottomOffset How far from the bottom of the screen the element counts
 *   as seen; "-50px" waits until it is 50px inside.
 */
export function useSeen(
  ref: RefObject<Element | null>,
  { enabled = true, bottomOffset = "0px" }: { enabled?: boolean; bottomOffset?: `${number}px` | `${number}%` } = {},
): boolean {
  const [seen, setSeen] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!enabled || seen || !element) return
    // Old browsers without the observer: show the content rather than hide it.
    if (typeof IntersectionObserver === "undefined") {
      setSeen(true)
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setSeen(true)
          observer.disconnect()
        }
      },
      { root: document, rootMargin: `${PASSED_REACH} 0px ${bottomOffset} 0px` },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref, enabled, seen, bottomOffset])

  return seen
}
