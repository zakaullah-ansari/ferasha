import { getRouter } from "@storybook/nextjs-vite/navigation.mock";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";

import { DashboardSidebar } from "@/components/dashboard/DashboardSidebar";
import { OrderDetailView } from "@/components/dashboard/OrderDetailView";
import { OrdersListView } from "@/components/dashboard/OrdersListView";
import { OverviewView } from "@/components/dashboard/OverviewView";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { orderView } from "@/lib/order-status";

import { BACK_OFFICE_ORDER, QUIET_SUMMARY, RECENT_ORDERS, SUMMARY } from "../tests/fixtures/back-office";
import { mockFetch } from "./mock-fetch";

/** The owner dashboard (/dashboard): overview, orders, one order. */
const meta = {
  title: "Dashboard",
  parameters: { layout: "fullscreen", nextjs: { navigation: { pathname: "/dashboard" } } },
  decorators: [
    (Story) => (
      <TooltipProvider>
        <SidebarProvider>
          <DashboardSidebar user={{ full_name: "Kausar", email: "owner@ferasha.com" }} />
          <SidebarInset>
            <header className="flex h-14 items-center border-b px-4">
              <SidebarTrigger />
            </header>
            <div className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
              <Story />
            </div>
          </SidebarInset>
        </SidebarProvider>
      </TooltipProvider>
    ),
  ],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const FRIDAY = new Date("2026-11-20T04:30:00Z");

export const Overview: Story = {
  render: () => <OverviewView summary={SUMMARY} today={FRIDAY} />,
};

/** Opening day: no sales, nothing waiting. Nothing is invented to fill the space. */
export const OverviewQuiet: Story = {
  render: () => <OverviewView summary={QUIET_SUMMARY} today={FRIDAY} />,
};

export const Orders: Story = {
  parameters: { nextjs: { navigation: { pathname: "/dashboard/orders" } } },
  render: () => (
    <OrdersListView view={orderView("all")} page={1} pageCount={3} count={RECENT_ORDERS.length} orders={RECENT_ORDERS} />
  ),
};

export const OrdersNoMatch: Story = {
  parameters: { nextjs: { navigation: { pathname: "/dashboard/orders" } } },
  render: () => <OrdersListView view={orderView("to-ship")} q="Rukhsar" page={1} pageCount={1} count={0} orders={[]} />,
};

/** A paid bespoke order: the suggested move is the atelier, and confirming it refreshes the page. */
export const Order: Story = {
  parameters: { nextjs: { navigation: { pathname: "/dashboard/orders/FER-260412" } } },
  beforeEach: () =>
    mockFetch([
      { method: "POST", path: "/api/v1/orders/FER-260412/transition/", body: { ...BACK_OFFICE_ORDER, status: "in_atelier" } },
    ]),
  render: () => <OrderDetailView order={BACK_OFFICE_ORDER} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Start in the atelier" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Start in the atelier" }));
    await waitFor(() => expect(getRouter().refresh).toHaveBeenCalled());
  },
};

/** Cancelling asks for a reason first; a refusal from the state machine is shown, not swallowed. */
export const OrderCancelRefused: Story = {
  parameters: { nextjs: { navigation: { pathname: "/dashboard/orders/FER-260412" } } },
  beforeEach: () =>
    mockFetch([
      {
        method: "POST",
        path: "/api/v1/orders/FER-260412/transition/",
        status: 409,
        body: { detail: "Cannot move order FER-260412 from 'stitching' to 'cancelled'." },
      },
    ]),
  render: () => <OrderDetailView order={BACK_OFFICE_ORDER} />,
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "Cancel order" }));
    const dialog = within(await screen.findByRole("dialog"));
    const confirm = dialog.getByRole("button", { name: "Cancel order" });
    await expect(confirm).toBeDisabled();
    await userEvent.type(dialog.getByLabelText("Reason (required)"), "Customer asked to cancel by phone");
    await userEvent.click(confirm);
    await expect(await dialog.findByRole("alert")).toHaveTextContent("Cannot move order FER-260412");
  },
};
