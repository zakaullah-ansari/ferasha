import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { expect, userEvent, waitFor, within } from "storybook/test";

import { ChaseLoader } from "@/components/ChaseLoader";
import { ResponsivePanel } from "@/components/ResponsivePanel";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/cn";
import { GLASS } from "@/lib/glass";

import suit from "../assets/kausar-lawn-suit.jpg";

/** Frosted glass, the sweep button, the bouncing checkbox, the chasing loader and the phone drawer. */
const meta = {
  title: "UI/Glass & feedback",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

/** Glass is for what floats over imagery; each strength keeps body-text contrast. */
export const GlassOverPhotography: Story = {
  render: () => (
    <div className="relative grid max-w-3xl place-items-center overflow-hidden rounded-[2rem] bg-cover bg-center p-10" style={{ backgroundImage: `url(${suit.src})` }}>
      <div className="grid w-full max-w-sm gap-4">
        <div className={cn("rounded-2xl px-5 py-4", GLASS.float)}>
          <p className="text-xs tracking-[0.2em] text-muted-foreground uppercase">Tailored by</p>
          <p className="mt-1 font-display text-lg">Kausar Dezine Studio</p>
        </div>
        <div className={cn("rounded-3xl p-5 text-sm", GLASS.panel)}>
          A panel: drawers, sheets and dialogs. Long text stays readable because enough of the theme background remains.
        </div>
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary">Glass (secondary)</Button>
          <Button variant="sweep" size="lg">
            Book a bespoke fitting
          </Button>
        </div>
      </div>
    </div>
  ),
};

/** The box dips and springs past its size on check; it still toggles like any checkbox. */
export const BouncingCheckbox: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      <Checkbox id="glass-story-check" />
      <Label htmlFor="glass-story-check">Fully covered</Label>
    </div>
  ),
  play: async ({ canvasElement }) => {
    const box = within(canvasElement).getByRole("checkbox", { name: "Fully covered" });
    await userEvent.click(box);
    await expect(box).toHaveAttribute("aria-checked", "true");
    await userEvent.click(box);
    await expect(box).toHaveAttribute("aria-checked", "false");
  },
};

export const Loader: Story = {
  render: () => (
    <div className="flex items-center gap-8 text-primary">
      <ChaseLoader className="text-xl" />
      <ChaseLoader className="text-4xl" />
      <ChaseLoader className="text-7xl text-foreground" label="Placing your order" />
    </div>
  ),
};

function BagPanelDemo() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Open the bag</Button>
      <ResponsivePanel
        open={open}
        onOpenChange={setOpen}
        title="Your bag"
        description="2 pieces"
        footer={<Button size="lg" className="w-full">Proceed to checkout</Button>}
      >
        <p className="py-6 text-sm text-muted-foreground">Bag contents.</p>
      </ResponsivePanel>
    </>
  );
}

/** On a phone: a drawer from the bottom that swipes away, its footer always on screen. */
export const PhoneDrawer: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
  render: () => <BagPanelDemo />,
};

/**
 * From tablet up: the same rounded, floating drawer, sliding in from the
 * right - never a sharp-edged slab. Mouse and keyboard close it with the X.
 */
export const DesktopDrawer: Story = {
  render: () => <BagPanelDemo />,
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Open the bag" }));
    const body = within(canvasElement.ownerDocument.body);
    const dialog = await body.findByRole("dialog", { name: "Your bag" });
    const popup = dialog.closest<HTMLElement>('[data-slot="drawer-popup"]') ?? dialog;
    await expect(popup.dataset.swipeDirection).toBe("right");
    await expect(parseFloat(getComputedStyle(popup).borderTopLeftRadius)).toBeGreaterThan(16);
    await userEvent.click(body.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(body.queryByRole("dialog", { name: "Your bag" })).not.toBeInTheDocument());
  },
};
