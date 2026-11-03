import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { DigitalMannequin } from "@/components/digital-mannequin/DigitalMannequin";

/** Fit guide: marks where the active measurement is taken. */
const meta = {
  title: "Commerce/DigitalMannequin",
  component: DigitalMannequin,
  parameters: { layout: "centered" },
  argTypes: {
    activeMeasurement: {
      control: "select",
      options: [undefined, "shoulder", "bust", "waist", "hip", "sleeve", "length"],
    },
  },
} satisfies Meta<typeof DigitalMannequin>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Idle: Story = {};
export const MeasuringBust: Story = { args: { activeMeasurement: "bust" } };
export const MeasuringSleeve: Story = { args: { activeMeasurement: "sleeve", coveredNeckline: true } };
