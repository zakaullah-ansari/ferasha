import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { FormField } from "@/components/FormField";

const meta = {
  title: "Components/FormField",
  component: FormField,
  tags: ["autodocs"],
  parameters: { layout: "centered" },
  args: { id: "email", label: "Email", type: "email", placeholder: "you@example.com" },
  decorators: [(Story) => <div className="w-80"><Story /></div>],
} satisfies Meta<typeof FormField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};
export const Filled: Story = { args: { defaultValue: "ayesha@example.com" } };
/** Error text is wired to the input (aria-invalid + aria-describedby). */
export const WithServerError: Story = {
  args: { id: "phone", label: "Mobile", type: "tel", defaultValue: "12345", error: "Enter a valid phone number." },
};
