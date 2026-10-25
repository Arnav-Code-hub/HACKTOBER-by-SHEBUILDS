/**
 * Shared ESLint flat config for the TypeScript half of the repo.
 *
 * One preset means one place to change a rule, instead of a config per package
 * that drifts until `make lint` and CI disagree.
 */
import js from "@eslint/js";
import tseslint from "typescript-eslint";

/** Base preset: plain TypeScript packages. */
export const base = tseslint.config(
  {
    // Generated output is never linted — the generator owns its style, and
    // lint errors in generated code are unfixable by hand.
    ignores: [
      "**/dist/**",
      "**/.next/**",
      "**/node_modules/**",
      "**/generated/**",
      "**/*.config.*",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Prefer explicit `unknown` and narrowing over `any`.
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
);

export default base;
