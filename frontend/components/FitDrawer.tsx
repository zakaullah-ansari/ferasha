"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import {
  type GarmentType,
  type MeasurementName,
  fitProfileSchema,
  rangeIn,
  requiredFor,
} from "@/lib/api/fit-schema";
import { cn } from "@/lib/cn";
import { type Unit, fromDisplay, toDisplay } from "@/lib/units";

/**
 * The FitDrawer — standard sizing or full bespoke measurement entry.
 *
 * Design notes that matter:
 *
 *  - **Canonical inches.** Every value in state is inches, matching the
 *    backend contract. The cm toggle converts at the display boundary only,
 *    so switching units repeatedly cannot erode a measurement.
 *  - **Shared validation.** Ranges come from the generated contract, so the
 *    drawer cannot accept something the API will reject.
 *  - **Drafts persist.** Measuring yourself is tedious; losing the form to an
 *    accidental navigation is the kind of thing that loses an order.
 *  - **Focus is trapped and restored.** Implemented directly rather than
 *    pulled from a library, so the behaviour is visible and testable.
 */

const STANDARD_SIZES = ["XS", "S", "M", "L", "XL", "XXL"] as const;

/**
 * Measurements are stored in the unit the backend contract declares
 * (`fit-contract.json` -> "unit": "inch"). Named once, here, and threaded
 * through every conversion so the display unit can never be mistaken for the
 * storage unit.
 */
const STORAGE_UNIT: Unit = "inch";

/**
 * Is this element a usable tab stop?
 *
 * Deliberately *not* `offsetParent !== null`, the usual shorthand. That
 * returns null for any element inside a `position: fixed` subtree — which is
 * exactly what a drawer is — so the shorthand silently reports "no focusable
 * elements" and the focus trap quietly stops working. It also returns null
 * in any non-layout environment, so the bug is invisible to jsdom tests.
 *
 * Checking the attributes that actually remove an element from the tab order
 * is both correct in a fixed subtree and testable.
 */
function isFocusable(element: HTMLElement): boolean {
  if (element.hasAttribute("disabled")) return false;
  if (element.getAttribute("aria-hidden") === "true") return false;
  if (element.closest("[aria-hidden='true']")) return false;
  if (element.hidden) return false;
  const style = element.ownerDocument.defaultView?.getComputedStyle(element);
  if (style && (style.display === "none" || style.visibility === "hidden")) {
    return false;
  }
  return true;
}
const DRAFT_KEY = "ferasha:fit-draft:v1";

export interface FitSelection {
  readonly mode: "standard" | "bespoke";
  readonly size?: string;
  /** Canonical inches. */
  readonly measurements?: Readonly<Partial<Record<MeasurementName, number>>>;
  readonly fullLining?: boolean;
  readonly notes?: string;
}

interface FitDrawerProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly garment: GarmentType;
  readonly productName: string;
  readonly supportsBespoke: boolean;
  readonly onSubmit: (selection: FitSelection) => void;
}

export function FitDrawer({
  open,
  onClose,
  garment,
  productName,
  supportsBespoke,
  onSubmit,
}: FitDrawerProps) {
  const headingId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  const [mode, setMode] = useState<"standard" | "bespoke">("standard");
  const [size, setSize] = useState<string>("M");
  const [unit, setUnit] = useState<Unit>("inch");
  const [fullLining, setFullLining] = useState(false);
  const [values, setValues] = useState<Partial<Record<MeasurementName, number>>>({});
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
  const [submitted, setSubmitted] = useState(false);

  const required = useMemo(() => requiredFor(garment), [garment]);

  /* ---------------------------------------------------------------- draft */

  useEffect(() => {
    if (!open) return;
    try {
      const raw = window.localStorage.getItem(DRAFT_KEY);
      if (!raw) return;
      const draft = JSON.parse(raw) as {
        values?: Partial<Record<MeasurementName, number>>;
        unit?: Unit;
        fullLining?: boolean;
      };
      if (draft.values) setValues(draft.values);
      if (draft.unit) setUnit(draft.unit);
      if (draft.fullLining !== undefined) setFullLining(draft.fullLining);
    } catch {
      // A corrupt draft must never block the drawer from opening.
      window.localStorage.removeItem(DRAFT_KEY);
    }
  }, [open]);

  useEffect(() => {
    if (!open || mode !== "bespoke") return;
    const id = window.setTimeout(() => {
      try {
        window.localStorage.setItem(
          DRAFT_KEY,
          JSON.stringify({ values, unit, fullLining }),
        );
      } catch {
        // Private browsing or a full quota. Losing the draft is acceptable;
        // crashing the drawer is not.
      }
    }, 300);
    return () => window.clearTimeout(id);
  }, [open, mode, values, unit, fullLining]);

  /* ------------------------------------------------------- focus & escape */

  useEffect(() => {
    if (!open) return;

    previouslyFocused.current = document.activeElement as HTMLElement | null;

    // Lock scroll without the layout shift that removing the scrollbar causes.
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const { overflow, paddingRight } = document.body.style;
    document.body.style.overflow = "hidden";
    if (scrollbar > 0) document.body.style.paddingRight = `${scrollbar}px`;

    const focusables = () =>
      Array.from(
        panelRef.current?.querySelectorAll<HTMLElement>(
          'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])',
        ) ?? [],
      ).filter(isFocusable);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const items = focusables();
      if (items.length === 0) return;
      const first = items[0]!;
      const last = items[items.length - 1]!;

      // Wrap at both ends so focus can never escape to the page behind.
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    const timer = window.setTimeout(() => focusables()[0]?.focus(), 0);

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(timer);
      document.body.style.overflow = overflow;
      document.body.style.paddingRight = paddingRight;
      previouslyFocused.current?.focus();
    };
  }, [open, onClose]);

  /* ------------------------------------------------------------ handlers */

  const setMeasurement = useCallback(
    (name: MeasurementName, raw: string) => {
      setValues((current) => {
        if (raw.trim() === "") {
          const next = { ...current };
          delete next[name];
          return next;
        }
        const parsed = Number.parseFloat(raw);
        if (!Number.isFinite(parsed)) return current;
        // Store canonical inches regardless of the unit on screen.
        return { ...current, [name]: fromDisplay(parsed, unit, STORAGE_UNIT) };
      });
    },
    [unit],
  );

  const validate = useCallback(() => {
    const result = fitProfileSchema(garment).safeParse(values);
    if (result.success) {
      setErrors({});
      return true;
    }
    const found: Record<string, string> = {};
    for (const issue of result.error.issues) {
      const key = String(issue.path[0] ?? "form");
      found[key] ??= issue.message;
    }
    setErrors(found);
    return false;
  }, [garment, values]);

  const handleSubmit = useCallback(() => {
    setSubmitted(true);
    if (mode === "standard") {
      onSubmit({ mode: "standard", size });
      onClose();
      return;
    }
    if (!validate()) return;
    onSubmit({ mode: "bespoke", measurements: values, fullLining });
    try {
      window.localStorage.removeItem(DRAFT_KEY);
    } catch {
      /* non-fatal */
    }
    onClose();
  }, [mode, size, values, fullLining, validate, onSubmit, onClose]);

  if (!open) return null;

  const unitLabel = unit === "inch" ? "in" : "cm";

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop. aria-hidden because the dialog below is the accessible
          surface; clicking it is a convenience, Escape is the contract. */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 bg-foreground/40 backdrop-blur-[2px]"
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        className={cn(
          "relative flex h-full w-full flex-col bg-background shadow-2xl",
          // Bottom sheet on phones, side drawer from md up.
          "max-md:mt-auto max-md:h-[92vh] max-md:rounded-t-2xl",
          "md:max-w-lg",
        )}
      >
        <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            <h2 id={headingId} className="font-display text-xl text-foreground">
              Select your fit
            </h2>
            <p className="mt-0.5 text-sm text-muted-foreground">{productName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close fit selection"
            className="rounded-full p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </header>

        {/* Mode switch */}
        <div
          role="tablist"
          aria-label="Fit mode"
          className="flex gap-1 border-b border-border px-5 py-3"
        >
          {(["standard", "bespoke"] as const).map((value) => {
            const disabled = value === "bespoke" && !supportsBespoke;
            return (
              <button
                key={value}
                role="tab"
                type="button"
                aria-selected={mode === value}
                disabled={disabled}
                onClick={() => setMode(value)}
                className={cn(
                  "min-h-11 rounded-full px-4 text-sm font-medium capitalize transition-colors",
                  mode === value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  disabled && "cursor-not-allowed opacity-40",
                )}
              >
                {value}
                {disabled && <span className="sr-only"> (not available)</span>}
              </button>
            );
          })}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {mode === "standard" ? (
            <fieldset>
              <legend className="mb-3 text-sm font-medium text-foreground">
                Standard size
              </legend>
              <div className="grid grid-cols-3 gap-2">
                {STANDARD_SIZES.map((option) => (
                  <label
                    key={option}
                    className={cn(
                      "flex min-h-11 cursor-pointer items-center justify-center rounded-lg border text-sm",
                      size === option
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input text-foreground hover:border-ring",
                    )}
                  >
                    <input
                      type="radio"
                      name="standard-size"
                      value={option}
                      checked={size === option}
                      onChange={() => setSize(option)}
                      className="sr-only"
                    />
                    {option}
                  </label>
                ))}
              </div>
              <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                Unsure? Bespoke tailoring uses your own measurements and is cut
                to order.
              </p>
            </fieldset>
          ) : (
            <>
              {/* Unit toggle */}
              <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-medium text-foreground">
                  Measurements
                </span>
                <div
                  role="group"
                  aria-label="Measurement unit"
                  className="flex rounded-full border border-input p-0.5"
                >
                  {(["inch", "cm"] as const).map((option) => (
                    <button
                      key={option}
                      type="button"
                      aria-pressed={unit === option}
                      onClick={() => setUnit(option)}
                      className={cn(
                        "min-h-9 rounded-full px-3 text-xs font-medium",
                        unit === option
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground",
                      )}
                    >
                      {option === "inch" ? "Inches" : "Centimetres"}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                {required.map((name) => {
                  const range = rangeIn(name, unit);
                  const raw = values[name];
                  const shown =
                    raw === undefined
                      ? ""
                      : String(toDisplay(raw, STORAGE_UNIT, unit));
                  const error = submitted ? errors[name] : undefined;
                  const fieldId = `fit-${name}`;
                  const errorId = `${fieldId}-error`;

                  return (
                    <div key={name}>
                      <label
                        htmlFor={fieldId}
                        className="mb-1 block text-sm text-foreground"
                      >
                        {range.label}
                        <span className="ml-1 text-destructive" aria-hidden="true">
                          *
                        </span>
                        <span className="sr-only">(required)</span>
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          id={fieldId}
                          type="number"
                          inputMode="decimal"
                          step="0.25"
                          value={shown}
                          onChange={(e) => setMeasurement(name, e.target.value)}
                          aria-invalid={error ? true : undefined}
                          aria-describedby={error ? errorId : undefined}
                          className={cn(
                            "min-h-11 w-full rounded-lg border bg-background px-3 text-foreground",
                            error
                              ? "border-destructive"
                              : "border-input focus:border-ring",
                          )}
                        />
                        <span className="w-8 text-sm text-muted-foreground">
                          {unitLabel}
                        </span>
                      </div>
                      {error && (
                        <p
                          id={errorId}
                          role="alert"
                          className="mt-1 text-xs text-destructive"
                        >
                          {error}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              <label className="mt-5 flex min-h-11 items-center gap-2.5 text-sm text-foreground">
                <input
                  type="checkbox"
                  checked={fullLining}
                  onChange={(e) => setFullLining(e.target.checked)}
                  className="size-4 accent-primary"
                />
                Add full lining
              </label>
            </>
          )}
        </div>

        <footer className="border-t border-border px-5 py-4">
          {/* aria-live so validation failure is announced, not just shown. */}
          <p aria-live="polite" className="sr-only">
            {submitted && Object.keys(errors).length > 0
              ? `${Object.keys(errors).length} measurements need attention.`
              : ""}
          </p>
          <button
            type="button"
            onClick={handleSubmit}
            className="min-h-12 w-full rounded-full bg-primary text-sm font-medium tracking-wide text-primary-foreground hover:bg-primary/95"
          >
            {mode === "standard" ? "Confirm size" : "Save measurements"}
          </button>
        </footer>
      </div>
    </div>
  );
}
