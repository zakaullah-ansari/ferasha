import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { Check } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
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

/** @reui/stepper, as checkout uses it. */
const meta = {
  title: "UI/Stepper",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const STEPS = ["Delivery", "Review", "Payment"];

export const Steps: Story = {
  render: function Render() {
    const [step, setStep] = useState(2);
    return (
      <Stepper
        value={step}
        onValueChange={setStep}
        indicators={{ completed: <Check className="size-3.5" /> }}
        className="mx-auto max-w-xl space-y-6"
      >
        <StepperNav>
          {STEPS.map((title, index) => (
            <StepperItem key={title} step={index + 1} completed={step > index + 1} className="relative flex-1 items-start">
              <StepperTrigger className="flex flex-col items-start gap-2">
                <StepperIndicator>{index + 1}</StepperIndicator>
                <StepperTitle>{title}</StepperTitle>
              </StepperTrigger>
              {index < STEPS.length - 1 && <StepperSeparator />}
            </StepperItem>
          ))}
        </StepperNav>
        <StepperPanel>
          {STEPS.map((title, index) => (
            <StepperContent key={title} value={index + 1} className="text-sm text-muted-foreground">
              {title} step content.
            </StepperContent>
          ))}
        </StepperPanel>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setStep((s) => Math.max(1, s - 1))}>Back</Button>
          <Button onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))}>Next</Button>
        </div>
      </Stepper>
    );
  },
};
