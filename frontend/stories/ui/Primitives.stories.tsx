import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { NumberTicker } from "@/components/ui/number-ticker";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

/** The smaller shadcn primitives, as the storefront uses them. */
const meta = {
  title: "UI/Primitives",
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Badges: Story = {
  render: () => (
    <div className="flex gap-2">
      <Badge>2</Badge>
      <Badge variant="secondary">Awaiting payment</Badge>
      <Badge variant="outline">Bespoke</Badge>
      <Badge variant="destructive">Sold out</Badge>
    </div>
  ),
};

export const CardWithContent: Story = {
  render: () => (
    <Card className="w-96">
      <CardHeader>
        <CardTitle>Where shall we deliver?</CardTitle>
        <CardDescription>Delivery is free within Maharashtra.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">Card body content.</CardContent>
    </Card>
  ),
};

export const TermsCheckbox: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return (
      <div className="flex items-start gap-3">
        <Checkbox id="terms" checked={checked} onCheckedChange={(value) => setChecked(value === true)} />
        <Label htmlFor="terms" className="font-normal">
          I accept the terms of service and privacy policy.
        </Label>
      </div>
    );
  },
};

export const ColourChoice: Story = {
  render: function Render() {
    const [colour, setColour] = useState("Ivory");
    return (
      <ToggleGroup
        aria-label="Colour"
        variant="outline"
        value={[colour]}
        onValueChange={(value) => value[0] && setColour(value[0])}
      >
        {["Ivory", "Sage", "Blush"].map((option) => (
          <ToggleGroupItem key={option} value={option}>
            {option}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    );
  },
};

export const AnimatedTotal: Story = {
  render: () => (
    <p className="font-heading text-3xl">
      ₹<NumberTicker value={14160} />
    </p>
  ),
};
