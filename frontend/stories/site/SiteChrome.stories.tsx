import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";

import { PrimaryNavLinks } from "@/components/site/PrimaryNavLinks";
import { ThemeToggle } from "@/components/site/ThemeToggle";
import { ThemeProvider } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";

/**
 * The site chrome after Housiq: the floating pill header's category links
 * (underline drawn out on hover, kept under the current section) and the
 * button hover (a slight lift, a deepening green shadow, a press on click).
 * Hover the elements to see them; the footer lives in Home / Footer.
 */
const meta = {
  title: "Site/Chrome",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const NavOnSuits: Story = {
  parameters: { nextjs: { navigation: { pathname: "/products", query: { category: "suits", sort: "new" } } } },
  render: () => (
    <nav aria-label="Primary" className="rounded-full border border-primary/10 bg-background/75 px-6 py-3 shadow-lg shadow-primary/5">
      <PrimaryNavLinks />
    </nav>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("link", { name: "Suits" })).toHaveAttribute("aria-current", "page");
    await expect(canvas.getByRole("link", { name: "Bridal" })).not.toHaveAttribute("aria-current");
  },
};

export const Buttons: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Button>Shop the collection</Button>
      <Button variant="outline">Book a fitting</Button>
      <Button variant="secondary">Save for later</Button>
      <Button variant="sweep">Bespoke</Button>
      <Button variant="link">View all</Button>
    </div>
  ),
};

/** The light/dark switch: the new theme spreads out in a circle from the button. */
export const ThemeSwitch: Story = {
  render: () => (
    <ThemeProvider defaultTheme="light" storageKey="storybook-theme">
      <ThemeToggle />
    </ThemeProvider>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const root = document.documentElement;
    await userEvent.click(await canvas.findByRole("button", { name: "Switch to dark theme" }));
    await waitFor(() => expect(root).toHaveClass("dark"));
    // The toggler ignores clicks while its circle is still drawing, so a
    // double click cannot leave the theme half-switched: let it finish.
    await waitFor(() => expect(root.dataset.magicuiThemeVt).toBeUndefined());
    await userEvent.click(await canvas.findByRole("button", { name: "Switch to light theme" }));
    await waitFor(() => expect(root).not.toHaveClass("dark"));
  },
};
