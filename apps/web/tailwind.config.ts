import preset from "@janmaang/config/tailwind";
import type { Config } from "tailwindcss";

/**
 * Colours come from the shared preset, which maps them to the CSS custom
 * properties emitted by @janmaang/tokens. A brand hex is never written here.
 */
export default {
  presets: [preset],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
} satisfies Config;
