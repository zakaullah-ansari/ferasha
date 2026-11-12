import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, within } from "storybook/test";

import { Button } from "@/components/ui/button";

/**
 * The forest palette, after the Finvo and Housiq templates: green-black ink,
 * a faint mint ground, green-tinted greys, Kausar green for actions and gold
 * as the accent thread. The dark set is the deep forest of the footer.
 *
 * Every pair here is contrast-tested in tests/preset-contrast.test.ts.
 */
const meta = {
  title: "UI/Palette",
  parameters: { layout: "fullscreen" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const SWATCHES = [
  ["background", "bg-background"],
  ["card", "bg-card"],
  ["muted", "bg-muted"],
  ["accent", "bg-accent"],
  ["border", "bg-border"],
  ["input", "bg-input"],
  ["muted-foreground", "bg-muted-foreground"],
  ["foreground", "bg-foreground"],
  ["primary", "bg-primary"],
  ["gold-500", "bg-gold-500"],
] as const;

function Sheet({ label }: { label: string }) {
  return (
    <section className="space-y-6 bg-background p-8 text-foreground">
      <h2 className="font-display text-3xl">{label}</h2>
      <ul className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {SWATCHES.map(([name, swatch]) => (
          <li key={name} className="space-y-2">
            <div className={`h-16 rounded-xl border ${swatch}`} data-token={name} />
            <p className="text-xs text-muted-foreground">--{name}</p>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-3">
        <Button>Shop the collection</Button>
        <Button variant="outline">Book a fitting</Button>
        <Button variant="secondary">Save for later</Button>
      </div>
    </section>
  );
}

export const Forest: Story = {
  render: () => (
    <>
      <Sheet label="Light: mint ground, forest ink" />
      <div className="dark">
        <Sheet label="Dark: the footer's deep forest" />
      </div>
    </>
  ),
  play: async ({ canvasElement }) => {
    // The ink is green, not neutral: its green channel leads red and blue.
    const ink = within(canvasElement).getAllByText("--foreground")[0]!.previousElementSibling!;
    // Painted through a canvas, so an oklch() computed value reads as sRGB.
    const context = document.createElement("canvas").getContext("2d")!;
    context.fillStyle = getComputedStyle(ink).backgroundColor;
    context.fillRect(0, 0, 1, 1);
    const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
    await expect(g).toBeGreaterThan(r!);
    await expect(g).toBeGreaterThan(b!);
  },
};
