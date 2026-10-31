import type { Meta, StoryObj } from '@storybook/nextjs-vite';

import { ModestyBadgeList } from '@/components/ModestyBadge';

const meta = {
  title: 'Components/ModestyBadge',
  component: ModestyBadgeList,
  tags: ['autodocs'],
  parameters: { layout: 'centered' },
} satisfies Meta<typeof ModestyBadgeList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const HighCoverage: Story = {
  args: {
    modesty: {
      coverage_score: 85,
      badges: [
        { code: 'full_sleeve', label: 'Full Sleeves' },
        { code: 'high_neck', label: 'High Neck' },
        { code: 'opaque', label: 'Opaque' },
      ],
      advisories: [],
    },
  },
};

export const WithAdvisories: Story = {
  args: {
    modesty: {
      coverage_score: 45,
      badges: [{ code: 'breathable', label: 'Breathable' }],
      advisories: [
        { code: 'sheer_shoulders', label: 'Sheer Shoulders' },
        { code: 'low_back', label: 'Low Back' },
      ],
    },
  },
};

export const LimitedBadges: Story = {
  args: {
    limit: 1,
    modesty: {
      coverage_score: 60,
      badges: [
        { code: 'natural_fiber', label: 'Natural Fiber' },
        { code: 'eco_dye', label: 'Eco Dye' },
        { code: 'hand_loomed', label: 'Hand Loomed' },
      ],
      advisories: [],
    },
  },
};
