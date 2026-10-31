# syntax=docker/dockerfile:1.7
#
# Frontend dev image. docker-compose bind-mounts the source over /app and keeps
# node_modules and .next in anonymous volumes, so the dependencies installed
# here (Linux binaries) are not shadowed by the host's Windows node_modules.

FROM node:22-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Corepack reads the "packageManager" pin in package.json, so the container
# runs the same pnpm version as the host.
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 3000

CMD ["pnpm", "dev"]
