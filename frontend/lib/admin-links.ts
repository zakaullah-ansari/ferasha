/**
 * Django admin, where records are edited. The owner dashboard links into it
 * rather than rebuilding its forms (the hybrid admin decision): one place to
 * edit, so one set of validation rules.
 */

const ADMIN = (process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:8000/admin").replace(/\/+$/, "");

const search = (path: string, query: string) => `${ADMIN}/${path}/?q=${encodeURIComponent(query)}`;

export const ADMIN_LINKS = {
  home: `${ADMIN}/`,
  products: `${ADMIN}/catalog/product/`,
  addProduct: `${ADMIN}/catalog/product/add/`,
  categories: `${ADMIN}/catalog/category/`,
  pendingReviews: `${ADMIN}/reviews/review/?status__exact=pending`,
  photosToReview: `${ADMIN}/media_assets/mediaasset/?moderation_status__exact=needs_review`,
  variant: (sku: string) => search("catalog/productvariant", sku),
  order: (orderNumber: string) => search("orders/order", orderNumber),
} as const;
