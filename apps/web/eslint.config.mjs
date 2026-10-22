import base from "@janmaang/config/eslint";

export default [
  ...base,
  {
    // Next.js injects React into scope and owns the JSX runtime.
    languageOptions: {
      globals: { React: "readonly", process: "readonly" },
    },
  },
];
