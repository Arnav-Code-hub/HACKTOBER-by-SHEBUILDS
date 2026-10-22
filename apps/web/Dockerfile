# syntax=docker/dockerfile:1
# Build context is the REPO ROOT, not apps/web — the app depends on workspace
# packages under packages/, which must be inside the context.
#   docker build -f apps/web/Dockerfile .

FROM node:20-alpine AS base
RUN corepack enable
WORKDIR /repo

FROM base AS deps
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/contracts/package.json ./packages/contracts/
COPY packages/tokens/package.json ./packages/tokens/
COPY packages/ui/package.json ./packages/ui/
COPY packages/config/package.json ./packages/config/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# Sources plus the generated design tokens. dist/tokens.css is gitignored and
# globals.css imports it, so every stage that compiles the app needs it built.
FROM deps AS src
COPY . .
RUN pnpm --filter @janmaang/tokens build

FROM src AS development
EXPOSE 3000
CMD ["pnpm", "--filter", "@janmaang/web", "dev"]

FROM src AS builder
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @janmaang/web build

FROM base AS production
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup -g 10001 nodejs && adduser -S -u 10001 -G nodejs nextjs
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/public ./apps/web/public
USER nextjs
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
