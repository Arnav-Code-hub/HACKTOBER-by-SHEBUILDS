import base from "@janmaang/config/eslint";
import nextPlugin from "@next/eslint-plugin-next";

export default [
  ...base,
  {
    // `next build` detects the plugin by resolving the config for this file;
    // the shared preset ignores *.config.*, which hid the plugin from it.
    ignores: ["!eslint.config.mjs"],
  },
  {
    plugins: { "@next/next": nextPlugin },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
      // Evidence photos are Cloudinary delivery URLs that are already sized
      // and optimised (f_auto, q_auto) and server-signed. next/image would
      // re-process them through the Next.js optimiser and need every
      // Cloudinary host allow-listed, so plain <img> is deliberate here.
      "@next/next/no-img-element": "off",
    },
  },
  {
    // Next.js injects React into scope and owns the JSX runtime.
    languageOptions: {
      globals: { React: "readonly", process: "readonly" },
    },
  },
];
