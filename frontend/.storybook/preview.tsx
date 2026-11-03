import type { Preview } from "@storybook/nextjs-vite";
import { useEffect } from "react";

import { fontVariables } from "../lib/fonts";

// The storefront's real theme: shadcn Maia tokens, Kausar green, fonts.
// Without this every story rendered in browser defaults.
import "../app/globals.css";

const preview: Preview = {
  parameters: {
    // Components use the App Router (useRouter, usePathname, Link).
    nextjs: { appDirectory: true },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      // 'todo' - show a11y violations in the test UI only
      // 'error' - fail CI on a11y violations
      // 'off' - skip a11y checks entirely
      test: "todo",
    },
  },
  globalTypes: {
    theme: {
      description: "Colour scheme",
      toolbar: {
        title: "Theme",
        icon: "mirror",
        items: [
          { value: "light", title: "Light" },
          { value: "dark", title: "Dark (as the footer)" },
        ],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { theme: "light" },
  decorators: [
    (Story, context) => {
      const dark = context.globals.theme === "dark";
      // On <html>, not a wrapper div: Sheet and dialogs portal to <body>
      // and must inherit the fonts and colour scheme too.
      useEffect(() => {
        const root = document.documentElement;
        root.classList.add(...fontVariables.split(" "));
        root.classList.toggle("dark", dark);
        document.body.classList.add("bg-background", "text-foreground", "antialiased");
      }, [dark]);
      return <Story />;
    },
  ],
};

export default preview;
