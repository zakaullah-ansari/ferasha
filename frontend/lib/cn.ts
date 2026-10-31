/**
 * Merge class names, with later Tailwind utilities winning over earlier.
 *
 * Backed by shadcn's `cn` package (a compiled clsx + tailwind-merge), because
 * the base-maia registry components import it directly. Using it here too
 * keeps the app on one class-merging implementation.
 */
export { cn } from "cn";
