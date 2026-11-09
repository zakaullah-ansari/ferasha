import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { normalizePath } from "vite";
import { defineConfig } from "vitest/config";
import path from 'node:path';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
import { playwright } from '@vitest/browser-playwright';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Forward slashes: Storybook's next/image plugin writes this path into
      // generated source unescaped; on Windows the "\f" of "\ferasha" became a form feed.
      "@": normalizePath(fileURLToPath(new URL("./", import.meta.url)))
    }
  },
  test: {
    projects: [{
      extends: true,
      test: {
        name: "unit",
        environment: "jsdom",
        globals: true,
        setupFiles: ["./tests/setup.ts"],
        include: ["tests/**/*.test.{ts,tsx}"]
      }
    }, {
      extends: true,
      plugins: [
      // The plugin will run tests for the stories defined in your Storybook config
      // See options at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon#storybooktest
      storybookTest({
        configDir: path.join(dirname, '.storybook')
      })],
      test: {
        name: 'storybook',
        browser: {
          enabled: true,
          headless: true,
          // The default 30 s is too short for the first bundle on a busy dev machine
          // (Docker, the dev server and the API all running): runs died before any
          // story executed. A failing story still fails; this only stops the
          // runner giving up before it starts.
          connectTimeout: 180_000,
          provider: playwright(),
          instances: [{
            browser: 'chromium'
          }]
        }
      }
    }]
  }
});