import { getRouter } from "@storybook/nextjs-vite/navigation.mock";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";

import { SearchDialog } from "@/components/site/SearchDialog";

import { PRODUCT } from "../tests/fixtures/commerce";
import { mockFetch } from "./mock-fetch";

/** Header search: matches as you type, every result on Enter, suggestions when nothing matches. */
const meta = {
  title: "Search",
  parameters: { layout: "centered" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const GHARARAS = [
  { ...PRODUCT, id: "g1", slug: "velvet-gharara", name: "Velvet Gharara Set - Emerald", base_price: "64500.00" },
  { ...PRODUCT, id: "g2", slug: "farshi-gharara", name: "Farshi Gharara - Ivory & Gold", base_price: "42000.00" },
];

export const AsYouType: Story = {
  beforeEach: () => mockFetch([{ path: "/api/v1/catalog/products/", body: { count: 2, next: null, previous: null, results: GHARARAS } }]),
  render: () => <SearchDialog />,
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Search" }));
    const dialog = within(await screen.findByRole("dialog"));
    await userEvent.type(dialog.getByRole("searchbox", { name: "Search the collection" }), "gharra");
    await expect(await dialog.findByRole("link", { name: /Velvet Gharara Set/ })).toHaveAttribute("href", "/products/velvet-gharara");
    await expect(dialog.getByRole("link", { name: /See all 2 results/ })).toHaveAttribute("href", "/products?search=gharra");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(getRouter().push).toHaveBeenLastCalledWith("/products?search=gharra"));
  },
};

export const NothingFound: Story = {
  beforeEach: () => mockFetch([{ path: "/api/v1/catalog/products/", body: { count: 0, next: null, previous: null, results: [] } }]),
  render: () => <SearchDialog />,
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Search" }));
    const dialog = within(await screen.findByRole("dialog"));
    await userEvent.type(dialog.getByRole("searchbox", { name: "Search the collection" }), "xyzzy");
    await expect(await dialog.findByText(/Nothing matches/)).toBeInTheDocument();
    await userEvent.click(dialog.getByRole("button", { name: "Chikankari" }));
    await expect(dialog.getByRole("searchbox", { name: "Search the collection" })).toHaveValue("Chikankari");
  },
};
