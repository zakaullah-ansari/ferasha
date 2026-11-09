import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, within } from "storybook/test";

import { ProductReviews } from "@/components/product/ProductReviews";
import type { Review, ReviewSummary } from "@/lib/api/types";

import { CUSTOMER, PRODUCT } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

/** Reviews on the product page: summary, published reviews, and writing one. */
const meta = {
  title: "Product page/Reviews",
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const SUMMARY: ReviewSummary = {
  count: 3,
  average: "4.3",
  distribution: { "1": 0, "2": 0, "3": 1, "4": 0, "5": 2 },
  fit: { ran_small: 0, true_to_size: 2, ran_large: 1 },
  modesty_as_described: { yes: 3, no: 0 },
};

const REVIEWS: Review[] = [
  {
    id: "r1",
    product: PRODUCT.id,
    author_name: "Ayesha",
    rating: 5,
    title: "Wore it for my sister's Nikah",
    body: "The lining is lovely and nothing is sheer. Sleeves were exactly full length as described.",
    fit_feedback: "true_to_size",
    modesty_as_described: true,
    is_verified_purchase: true,
    created_at: "2026-11-02T10:00:00Z",
  },
  {
    id: "r2",
    product: PRODUCT.id,
    author_name: "Sana",
    rating: 3,
    title: "",
    body: "Beautiful work, but size up if you are between sizes.",
    fit_feedback: "ran_small",
    modesty_as_described: true,
    is_verified_purchase: false,
    created_at: "2026-10-28T10:00:00Z",
  },
];

const signedIn = (extra: Parameters<typeof mockFetch>[0] = []) =>
  mockFetch([{ path: "/api/v1/auth/me/", body: CUSTOMER }, ...extra]);

export const WithReviews: Story = {
  beforeEach: () => mockFetch([{ path: "/api/v1/auth/me/", status: 401, body: {} }]),
  render: () => <ProductReviews productId={PRODUCT.id} productSlug={PRODUCT.slug} summary={SUMMARY} reviews={REVIEWS} />,
};

export const NoReviewsYet: Story = {
  beforeEach: () => mockFetch([{ path: "/api/v1/auth/me/", status: 401, body: {} }]),
  render: () => (
    <ProductReviews
      productId={PRODUCT.id}
      productSlug={PRODUCT.slug}
      summary={{ ...SUMMARY, count: 0, average: null }}
      reviews={[]}
    />
  ),
};

/** Signed in: stars are required, then the review goes to moderation. */
export const WriteAReview: Story = {
  beforeEach: () => signedIn([{ method: "POST", path: "/api/v1/reviews/", status: 201, body: REVIEWS[0] }]),
  render: () => <ProductReviews productId={PRODUCT.id} productSlug={PRODUCT.slug} summary={SUMMARY} reviews={[]} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Write a review" }));
    await userEvent.click(canvas.getByRole("button", { name: "Send review" }));
    await expect(canvas.getByText("Choose from one to five stars.")).toBeInTheDocument();
    await userEvent.click(canvas.getByText("4 stars"));
    await userEvent.type(canvas.getByLabelText("Your review"), "Beautifully lined.");
    await userEvent.click(canvas.getByRole("button", { name: "Send review" }));
    await expect(await canvas.findByText(/once the atelier has read it/)).toBeInTheDocument();
  },
};

/** One review per piece: the API's answer is shown, not swallowed. */
export const AlreadyReviewed: Story = {
  beforeEach: () =>
    signedIn([
      { method: "POST", path: "/api/v1/reviews/", status: 400, body: { product: ["You have already reviewed this product."] } },
    ]),
  render: () => <ProductReviews productId={PRODUCT.id} productSlug={PRODUCT.slug} summary={SUMMARY} reviews={[]} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Write a review" }));
    await userEvent.click(canvas.getByText("5 stars"));
    await userEvent.click(canvas.getByRole("button", { name: "Send review" }));
    await expect(await canvas.findByRole("alert")).toHaveTextContent("You have already reviewed this product.");
  },
};
