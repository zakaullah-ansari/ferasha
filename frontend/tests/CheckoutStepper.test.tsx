/**
 * CheckoutStepper against a stubbed network.
 *
 * The real API client runs; only `fetch` is replaced. What matters is the
 * money contract: figures come from the server, the total the customer saw is
 * sent back, and a retry can never place a second order.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CheckoutStepper } from "@/components/CheckoutStepper";
import type { CheckoutQuote } from "@/lib/api/types";

const QUOTE: CheckoutQuote = {
  currency: "INR",
  lines: [
    {
      variant_id: "v-1",
      sku: "SKU-1",
      product_name: "Karachi Lawn Suit",
      variant_label: "M / Ivory",
      quantity: 1,
      unit_price: "12000.00",
      line_total: "12000.00",
    },
  ],
  subtotal: "12000.00",
  shipping_charge: "0.00",
  tax: {
    supply_type: "intra_state",
    lines: [],
    taxable_value: "12000.00",
    cgst_total: "1080.00",
    sgst_total: "1080.00",
    igst_total: "0.00",
    tax_total: "2160.00",
    grand_total: "14160.00",
    is_zero_rated_export: false,
    regime: "GST 2.0",
    notes: [],
  },
  tax_total: "2160.00",
  grand_total: "14160.00",
};

const ORDER = { order_number: "FER-ABC123", status: "placed", grand_total: "14160.00", currency: "INR" };

function respond(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  // motion's useInView / useReducedMotion need these; jsdom has neither.
  // Stubbed per test because afterEach's unstubAllGlobals removes them.
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function requestTo(call: Parameters<typeof fetch>) {
  const [url, init] = call;
  return {
    url: String(url),
    headers: init?.headers as Record<string, string>,
    body: JSON.parse(String(init?.body)),
  };
}

async function fillAddressAndContinue(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Full name"), "Ayesha Khan");
  await user.type(screen.getByLabelText("Mobile"), "+919820012345");
  await user.type(screen.getByLabelText("Address"), "402 Imperial Heights");
  await user.type(screen.getByLabelText("City"), "Mumbai");
  await user.type(screen.getByLabelText("State code"), "mh");
  await user.type(screen.getByLabelText("PIN code"), "400001");
  await user.click(screen.getByRole("button", { name: "Continue to review" }));
}

function setup() {
  const onPlaced = vi.fn();
  const user = userEvent.setup();
  render(<CheckoutStepper accessToken="test-token" onPlaced={onPlaced} />);
  return { user, onPlaced };
}

describe("CheckoutStepper", () => {
  it("prices the bag on the server and shows its figures", async () => {
    fetchMock.mockImplementationOnce(() => respond(200, QUOTE));
    const { user } = setup();

    await fillAddressAndContinue(user);

    const quoteCall = requestTo(fetchMock.mock.calls[0]!);
    expect(quoteCall.url).toBe("/api/v1/checkout/quote/");
    expect(quoteCall.headers.Authorization).toBe("Bearer test-token");
    expect(quoteCall.body.address).toMatchObject({ state_code: "MH", country_code: "IN" });

    expect(await screen.findByText("Review your order")).toBeInTheDocument();
    expect(screen.getByText("Free")).toBeInTheDocument();
    expect(screen.getAllByText("₹1,080")).toHaveLength(2); // CGST + SGST
    expect(screen.queryByText("IGST")).not.toBeInTheDocument();
  });

  it("places the order with the total the customer saw and an idempotency key", async () => {
    fetchMock
      .mockImplementationOnce(() => respond(200, QUOTE))
      .mockImplementationOnce(() => respond(201, ORDER));
    const { user, onPlaced } = setup();
    await fillAddressAndContinue(user);

    await user.click(await screen.findByRole("button", { name: /Place order/ }));

    await waitFor(() => expect(onPlaced).toHaveBeenCalledWith(ORDER));
    const placeCall = requestTo(fetchMock.mock.calls[1]!);
    expect(placeCall.url).toBe("/api/v1/checkout/place-order/");
    expect(placeCall.body.expected_grand_total).toBe("14160.00");
    expect(placeCall.headers["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("a network retry reuses the key so it cannot create a second order", async () => {
    fetchMock
      .mockImplementationOnce(() => respond(200, QUOTE))
      .mockImplementationOnce(() => Promise.reject(new TypeError("Failed to fetch")))
      .mockImplementationOnce(() => respond(201, ORDER));
    const { user, onPlaced } = setup();
    await fillAddressAndContinue(user);

    const place = await screen.findByRole("button", { name: /Place order/ });
    await user.click(place);
    expect(await screen.findByRole("alert")).toHaveTextContent("try again");
    await user.click(place);

    await waitFor(() => expect(onPlaced).toHaveBeenCalled());
    const firstKey = requestTo(fetchMock.mock.calls[1]!).headers["Idempotency-Key"];
    const retryKey = requestTo(fetchMock.mock.calls[2]!).headers["Idempotency-Key"];
    expect(retryKey).toBe(firstKey);
  });

  it("a price change is shown, not charged, and confirming again is a new attempt", async () => {
    const repriced = { ...QUOTE, grand_total: "15340.00" };
    fetchMock
      .mockImplementationOnce(() => respond(200, QUOTE))
      .mockImplementationOnce(() =>
        respond(409, { detail: "Prices have changed since your quote.", quote: repriced }),
      )
      .mockImplementationOnce(() => respond(201, ORDER));
    const { user, onPlaced } = setup();
    await fillAddressAndContinue(user);

    await user.click(await screen.findByRole("button", { name: /Place order/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Prices have changed");
    expect(onPlaced).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Place order · ₹15,340" }));

    await waitFor(() => expect(onPlaced).toHaveBeenCalled());
    const stale = requestTo(fetchMock.mock.calls[1]!);
    const confirmed = requestTo(fetchMock.mock.calls[2]!);
    expect(confirmed.body.expected_grand_total).toBe("15340.00");
    expect(confirmed.headers["Idempotency-Key"]).not.toBe(stale.headers["Idempotency-Key"]);
  });

  it("puts server field errors on the field that caused them", async () => {
    fetchMock.mockImplementationOnce(() =>
      respond(400, { address: { phone: ["Enter a valid phone number."] } }),
    );
    const { user } = setup();

    await fillAddressAndContinue(user);

    const phone = screen.getByLabelText("Mobile");
    await waitFor(() => expect(phone).toHaveAttribute("aria-invalid", "true"));
    expect(phone).toHaveAccessibleDescription("Enter a valid phone number.");
    expect(screen.queryByText("Review your order")).not.toBeInTheDocument();
  });
});
