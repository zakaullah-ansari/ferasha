"use client";

import { Check, Loader2 } from "lucide-react";
import { type FormEvent, useRef, useState } from "react";

import { FormField, fieldErrors as drfFieldErrors } from "@/components/FormField";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NumberTicker } from "@/components/ui/number-ticker";
import {
  Stepper,
  StepperContent,
  StepperIndicator,
  StepperItem,
  StepperNav,
  StepperPanel,
  StepperSeparator,
  StepperTitle,
  StepperTrigger,
} from "@/components/ui/stepper";
import { ApiError, api } from "@/lib/api/client";
import type { CheckoutQuote, DeliveryAddress, PlacedOrder } from "@/lib/api/types";
import { formatINR } from "@/lib/format";

/**
 * Checkout: delivery address -> server-priced review -> place order.
 *
 * The browser never computes money. Every figure shown comes from
 * `/checkout/quote/`, and placement sends back the total the customer saw so
 * a price change is refused (409) instead of silently charged.
 */

const STEPS = [
  { step: 1, title: "Delivery" },
  { step: 2, title: "Review" },
] as const;

type AddressField = Exclude<keyof DeliveryAddress, "country_code" | "gstin">;

const FIELDS: ReadonlyArray<{
  readonly name: AddressField;
  readonly label: string;
  readonly autoComplete: string;
  readonly required?: boolean;
  readonly wide?: boolean;
  readonly inputMode?: "tel" | "numeric";
  readonly pattern?: string;
  readonly placeholder?: string;
}> = [
  { name: "recipient_name", label: "Full name", autoComplete: "name", required: true, wide: true },
  { name: "phone", label: "Mobile", autoComplete: "tel", required: true, inputMode: "tel", placeholder: "+91 98200 12345" },
  { name: "line1", label: "Address", autoComplete: "address-line1", required: true, wide: true },
  { name: "line2", label: "Apartment, landmark (optional)", autoComplete: "address-line2", wide: true },
  { name: "city", label: "City", autoComplete: "address-level2", required: true },
  { name: "state_code", label: "State code", autoComplete: "address-level1", required: true, pattern: "[A-Za-z]{2}", placeholder: "MH" },
  { name: "postal_code", label: "PIN code", autoComplete: "postal-code", required: true, inputMode: "numeric", pattern: "[0-9]{6}" },
];

const EMPTY_ADDRESS: DeliveryAddress = {
  recipient_name: "",
  phone: "",
  line1: "",
  line2: "",
  city: "",
  state_code: "",
  postal_code: "",
  // International delivery is not offered yet; the API refuses it.
  country_code: "IN",
};

interface CheckoutStepperProps {
  /** Signed-in only: the session cookie authenticates every call. */
  readonly onPlaced: (order: PlacedOrder) => void;
}

/** Field errors from DRF's `{"address": {"phone": ["..."]}}` shape. */
function addressErrors(error: unknown): Partial<Record<AddressField, string>> {
  if (!(error instanceof ApiError)) return {};
  const nested = error.body?.address;
  return nested && typeof nested === "object"
    ? drfFieldErrors(nested as Record<string, unknown>)
    : {};
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status < 500) return error.message;
  return "Something went wrong on our side. Please try again in a moment.";
}

export function CheckoutStepper({ onPlaced }: CheckoutStepperProps) {
  const [step, setStep] = useState(1);
  const [address, setAddress] = useState<DeliveryAddress>(EMPTY_ADDRESS);
  const [quote, setQuote] = useState<CheckoutQuote | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<AddressField, string>>>({});
  // One key per priced attempt: a retried request after a dropped connection
  // reuses it and cannot create a second order; a new quote gets a new key.
  const attemptKey = useRef<string>("");

  const setField = (name: AddressField, value: string) =>
    setAddress((current) => ({
      ...current,
      [name]: name === "state_code" ? value.toUpperCase() : value,
    }));

  async function requestQuote(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      const priced = await api.checkout.quote(address);
      setQuote(priced);
      attemptKey.current = crypto.randomUUID();
      setStep(2);
    } catch (caught) {
      setFieldErrors(addressErrors(caught));
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function placeOrder() {
    if (!quote) return;
    setBusy(true);
    setError(null);
    try {
      const order = await api.checkout.placeOrder(address, quote.grand_total, attemptKey.current);
      onPlaced(order);
    } catch (caught) {
      const fresh = caught instanceof ApiError ? caught.body?.quote : undefined;
      if (caught instanceof ApiError && caught.status === 409 && fresh) {
        // Prices moved since the review. Show the new figures; the customer
        // confirms again, as a new attempt.
        setQuote(fresh as CheckoutQuote);
        attemptKey.current = crypto.randomUUID();
      }
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  const tax = quote?.tax;
  const intraState = tax?.supply_type === "intra_state";

  return (
    <Stepper
      value={step}
      onValueChange={setStep}
      indicators={{ completed: <Check className="size-3.5" />, loading: <Loader2 className="size-3.5 animate-spin" /> }}
      className="mx-auto w-full max-w-2xl space-y-8"
    >
      <StepperNav>
        {STEPS.map(({ step: value, title }, index) => (
          <StepperItem
            key={value}
            step={value}
            completed={step > value}
            // Review is reachable only with a live quote for this address.
            disabled={value === 2 && !quote}
            loading={busy && step === value}
            className="relative flex-1 items-start"
          >
            <StepperTrigger className="flex flex-col items-start gap-2">
              <StepperIndicator>{value}</StepperIndicator>
              <StepperTitle>{title}</StepperTitle>
            </StepperTrigger>
            {index < STEPS.length - 1 && <StepperSeparator />}
          </StepperItem>
        ))}
      </StepperNav>

      <StepperPanel>
        <StepperContent value={1}>
          <Card>
            <CardHeader>
              <CardTitle>Where shall we deliver?</CardTitle>
              <CardDescription>Delivery is free within Maharashtra.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={requestQuote} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {FIELDS.map((field) => (
                  <div key={field.name} className={field.wide ? "sm:col-span-2" : undefined}>
                    <FormField
                      id={`checkout-${field.name}`}
                      name={field.name}
                      label={field.label}
                      value={address[field.name] ?? ""}
                      onChange={(event) => setField(field.name, event.target.value)}
                      autoComplete={field.autoComplete}
                      required={field.required}
                      inputMode={field.inputMode}
                      pattern={field.pattern}
                      placeholder={field.placeholder}
                      error={fieldErrors[field.name]}
                    />
                  </div>
                ))}

                {error && step === 1 && (
                  <p role="alert" className="text-sm text-destructive sm:col-span-2">
                    {error}
                  </p>
                )}

                <Button type="submit" size="lg" disabled={busy} className="sm:col-span-2">
                  {busy ? "Pricing your order…" : "Continue to review"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </StepperContent>

        <StepperContent value={2}>
          {quote && tax && (
            <Card>
              <CardHeader>
                <CardTitle>Review your order</CardTitle>
                <CardDescription>
                  {address.recipient_name}, {address.line1}, {address.city} {address.postal_code}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <ul className="divide-y">
                  {quote.lines.map((line) => (
                    <li key={line.variant_id} className="flex justify-between gap-4 py-3 text-sm">
                      <span>
                        {line.product_name}
                        <span className="block text-muted-foreground">
                          {line.variant_label} · Qty {line.quantity}
                        </span>
                      </span>
                      <span className="tabular-nums">{formatINR(line.line_total)}</span>
                    </li>
                  ))}
                </ul>

                <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 text-sm">
                  <dt className="text-muted-foreground">Subtotal</dt>
                  <dd className="tabular-nums">{formatINR(quote.subtotal)}</dd>
                  <dt className="text-muted-foreground">Delivery</dt>
                  <dd className="tabular-nums">
                    {Number(quote.shipping_charge) === 0 ? "Free" : formatINR(quote.shipping_charge)}
                  </dd>
                  {intraState ? (
                    <>
                      <dt className="text-muted-foreground">CGST</dt>
                      <dd className="tabular-nums">{formatINR(tax.cgst_total)}</dd>
                      <dt className="text-muted-foreground">SGST</dt>
                      <dd className="tabular-nums">{formatINR(tax.sgst_total)}</dd>
                    </>
                  ) : (
                    <>
                      <dt className="text-muted-foreground">IGST</dt>
                      <dd className="tabular-nums">{formatINR(tax.igst_total)}</dd>
                    </>
                  )}
                  <dt className="border-t pt-3 font-medium">Total</dt>
                  <dd className="border-t pt-3 font-heading text-2xl">
                    {/* Animated for sighted users; the exact figure is announced. */}
                    <span aria-hidden="true">
                      ₹<NumberTicker value={Number(quote.grand_total)} />
                    </span>
                    <span className="sr-only">{formatINR(quote.grand_total)}</span>
                  </dd>
                </dl>

                {error && (
                  <p role="alert" className="text-sm text-destructive">
                    {error}
                  </p>
                )}

                <div className="flex gap-3">
                  <Button variant="outline" size="lg" onClick={() => setStep(1)} disabled={busy}>
                    Edit address
                  </Button>
                  <Button size="lg" className="flex-1" onClick={placeOrder} disabled={busy}>
                    {busy ? "Placing order…" : `Place order · ${formatINR(quote.grand_total)}`}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </StepperContent>
      </StepperPanel>
    </Stepper>
  );
}
