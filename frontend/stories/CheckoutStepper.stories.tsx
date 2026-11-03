import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { CheckoutStepper } from "@/components/CheckoutStepper";

import { ORDER, QUOTE } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

const meta = {
  title: "Checkout/CheckoutStepper",
  component: CheckoutStepper,
  parameters: { layout: "padded" },
  args: { onPlaced: fn() },
} satisfies Meta<typeof CheckoutStepper>;

export default meta;
type Story = StoryObj<typeof meta>;

const QUOTE_URL = "/api/v1/checkout/quote/";
const PLACE_URL = "/api/v1/checkout/place-order/";

async function fillMumbaiAddress(canvasElement: HTMLElement) {
  const canvas = within(canvasElement);
  await userEvent.type(canvas.getByLabelText("Full name"), "Ayesha Khan");
  await userEvent.type(canvas.getByLabelText("Mobile"), "+919820012345");
  await userEvent.type(canvas.getByLabelText("Address"), "402 Imperial Heights");
  await userEvent.type(canvas.getByLabelText("City"), "Mumbai");
  await userEvent.type(canvas.getByLabelText("State code"), "MH");
  await userEvent.type(canvas.getByLabelText("PIN code"), "400001");
  await userEvent.click(canvas.getByRole("button", { name: "Continue to review" }));
}

/** First step, empty. */
export const DeliveryAddress: Story = {};

/** Server-priced review: CGST + SGST within Maharashtra, free delivery. */
export const Review: Story = {
  beforeEach: () =>
    mockFetch([
      { method: "POST", path: QUOTE_URL, body: QUOTE },
      { method: "POST", path: PLACE_URL, body: ORDER, status: 201 },
    ]),
  play: async ({ canvasElement }) => {
    await fillMumbaiAddress(canvasElement);
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Review your order")).toBeInTheDocument();
    await expect(canvas.getByRole("button", { name: "Place order · ₹14,160" })).toBeEnabled();
  },
};

/** A price moved between review and placing: shown, never silently charged. */
export const PriceChanged: Story = {
  beforeEach: () =>
    mockFetch([
      { method: "POST", path: QUOTE_URL, body: QUOTE },
      {
        method: "POST",
        path: PLACE_URL,
        status: 409,
        body: {
          detail: "Prices have changed since your quote. Please review your order.",
          quote: { ...QUOTE, grand_total: "15340.00" },
        },
      },
    ]),
  play: async ({ canvasElement }) => {
    await fillMumbaiAddress(canvasElement);
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: /Place order/ }));
    await expect(await canvas.findByRole("alert")).toHaveTextContent("Prices have changed");
    await expect(canvas.getByRole("button", { name: "Place order · ₹15,340" })).toBeInTheDocument();
  },
};

/** The server rejected a field; the message sits under that field. */
export const InvalidPhone: Story = {
  beforeEach: () =>
    mockFetch([
      { method: "POST", path: QUOTE_URL, status: 400, body: { address: { phone: ["Enter a valid phone number."] } } },
    ]),
  play: async ({ canvasElement }) => {
    await fillMumbaiAddress(canvasElement);
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Enter a valid phone number.")).toBeInTheDocument();
  },
};
