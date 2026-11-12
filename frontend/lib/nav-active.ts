/**
 * Whether a nav link points at the page being shown. A link with a query
 * ("/products?category=suits") is current only when every parameter it names
 * matches, so "Suits" is not lit on the Bridal listing; extra parameters on
 * the page (a sort, a size filter) still count as the same section.
 */
export function isCurrentLink(href: string, pathname: string, search: URLSearchParams): boolean {
  const url = new URL(href, "https://ferasha.invalid");
  if (url.pathname !== pathname) return false;
  for (const [key, value] of url.searchParams) {
    if (search.get(key) !== value) return false;
  }
  return true;
}
