/**
 * Shared Tailwind preset.
 *
 * Colours resolve to the CSS custom properties emitted by @janmaang/tokens, so
 * a brand colour is defined once in tokens.json and never hard-coded here.
 */
export default {
  theme: {
    extend: {
      colors: {
        surface: "var(--jm-surface)",
        "on-surface": "var(--jm-on-surface)",
        density: {
          1: "var(--jm-density-tier1)",
          2: "var(--jm-density-tier2)",
          3: "var(--jm-density-tier3)",
          4: "var(--jm-density-tier4)",
          5: "var(--jm-density-tier5)",
        },
      },
      fontFamily: {
        sans: ["var(--jm-font-sans)"],
      },
    },
  },
};
