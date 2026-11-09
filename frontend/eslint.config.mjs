import { FlatCompat } from "@eslint/eslintrc";

// Next 15's shareable config is still in the legacy format; FlatCompat is the
// bridge the Next docs prescribe. Core Web Vitals + TypeScript rules.
const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "storybook-static/**",
      "next-env.d.ts",
      // Vendored from shadcn registries (shadcn, magicui, reui): kept as the
      // registry ships them so `shadcn add` can update them cleanly.
      "components/ui/**",
      "hooks/use-mobile.ts",
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default config;
