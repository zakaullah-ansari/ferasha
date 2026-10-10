import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge class names, with later Tailwind utilities winning over earlier. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
