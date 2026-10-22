import type { NextConfig } from "next";
import path from "node:path";

const config: NextConfig = {
  // Linux images keep the standalone bundle. Windows development uses the
  // regular build because standalone symlinks require extra OS privileges.
  output: process.platform === "win32" ? undefined : "standalone",
  outputFileTracingRoot: path.resolve(__dirname, "../.."),
  reactStrictMode: true,
  // Workspace packages ship TypeScript source rather than a build step.
  transpilePackages: [
    "@janmaang/ui",
    "@janmaang/tokens",
    "@janmaang/contracts",
  ],
  typedRoutes: true,
};

export default config;
