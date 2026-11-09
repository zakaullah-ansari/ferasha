"use client"

import { Checkbox as CheckboxPrimitive } from "@animate-ui/react/primitives/base-ui/checkbox"
import { cn } from "cn"
import { CheckIcon } from "lucide-react"
import { motion, useAnimationControls, useReducedMotion } from "motion/react"

/**
 * A tick that answers back: the box dips and springs past its size when
 * checked, a smaller rebound when cleared (440 ms). Theme colours; the
 * box stays still under prefers-reduced-motion.
 */
const BOUNCE = {
  checked: { scale: [1, 0.8, 1.22, 0.94, 1], times: [0, 0.25, 0.55, 0.75, 1] },
  cleared: { scale: [1, 1.14, 0.93, 1], times: [0, 0.3, 0.65, 1] },
} as const

function Checkbox({ className, onCheckedChange, ...props }: CheckboxPrimitive.Root.Props) {
  const reduce = useReducedMotion()
  const controls = useAnimationControls()

  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      render={<motion.span animate={controls} />}
      onCheckedChange={(checked, details) => {
        if (!reduce) {
          const { scale, times } = checked ? BOUNCE.checked : BOUNCE.cleared
          void controls.start({ scale: [...scale], transition: { duration: 0.44, times: [...times], ease: "easeOut" } })
        }
        onCheckedChange?.(checked, details)
      }}
      className={cn(
        "peer relative flex size-4 shrink-0 items-center justify-center rounded-[6px] border border-input transition-[box-shadow,background-color,border-color] duration-200 outline-none group-has-disabled/field:opacity-50 group-has-[:focus-visible]/field-label:ring-0 group-has-[:focus-visible]/field-label:not-data-checked:border-input after:absolute after:-inset-x-3 after:-inset-y-2 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-[3px] aria-invalid:ring-destructive/20 aria-invalid:aria-checked:border-primary dark:bg-input/30 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 data-checked:border-primary data-checked:bg-primary data-checked:text-primary-foreground group-has-[:focus-visible]/field-label:data-checked:border-primary dark:data-checked:bg-primary",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="grid place-content-center text-current transition-none [&>svg]:size-3.5"
      >
        <CheckIcon />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
