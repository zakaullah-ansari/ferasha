"use client";

import { CheckCircle2 } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

/** The tick after placing an order: it settles in once, calmly; still under reduced motion. */
export function OrderPlacedTick() {
  const reduce = useReducedMotion();
  return (
    <motion.span
      className="mx-auto block w-fit text-primary"
      initial={reduce ? false : { opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <CheckCircle2 aria-hidden="true" className="size-12" />
    </motion.span>
  );
}

/**
 * What happens next, in order. Honest about payment: until it is confirmed
 * the order waits for it. A bespoke order says what the atelier does first.
 */
export function WhatHappensNext({ awaitingPayment, bespoke }: { awaitingPayment: boolean; bespoke: boolean }) {
  const steps = [
    {
      title: awaitingPayment ? "Payment" : "Payment received",
      detail: awaitingPayment
        ? "Your order is confirmed once payment is complete."
        : "Your order is confirmed and with the atelier.",
    },
    {
      title: bespoke ? "Measured, then stitched" : "Prepared in the atelier",
      detail: bespoke
        ? "The atelier checks your measurements before any cloth is cut, then stitches your piece."
        : "Your pieces are checked, pressed and packed by hand.",
    },
    { title: "On its way", detail: "We email you when it ships. You can follow every step from your account." },
  ];
  return (
    <ol className="grid gap-5">
      {steps.map((step, index) => (
        <li key={step.title} className="grid grid-cols-[2rem_1fr] gap-3">
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-full border border-primary/40 text-sm text-primary tabular-nums"
          >
            {index + 1}
          </span>
          <span>
            <span className="block font-medium">{step.title}</span>
            <span className="text-sm text-muted-foreground">{step.detail}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
