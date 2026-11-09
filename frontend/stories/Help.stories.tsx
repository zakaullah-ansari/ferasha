import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { DraftNotice, HelpPage, PolicySections } from "@/components/site/PolicyView";
import { policy } from "@/lib/policies";

/** Help pages (/contact, /policies/*): one frame, and a notice until the atelier confirms the text. */
const meta = {
  title: "Help pages",
  parameters: { layout: "fullscreen", nextjs: { navigation: { pathname: "/policies/returns" } } },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const returns = policy("returns")!;

export const ReturnsDraft: Story = {
  render: () => (
    <HelpPage path="/policies/returns" eyebrow={`Updated ${returns.updated}`} title={returns.title} summary={returns.summary} toConfirm={returns.toConfirm}>
      <PolicySections sections={returns.sections} />
    </HelpPage>
  ),
};

/** Once everything is confirmed the notice disappears. */
export const Confirmed: Story = {
  render: () => (
    <HelpPage path="/policies/returns" eyebrow="Updated 9 November 2026" title={returns.title} summary={returns.summary} toConfirm={[]}>
      <p className="text-muted-foreground">Final text.</p>
    </HelpPage>
  ),
};

export const Notice: Story = {
  parameters: { layout: "padded" },
  render: () => <DraftNotice points={returns.toConfirm} />,
};
