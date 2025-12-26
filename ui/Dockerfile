FROM oven/bun:1.1.0 AS base

WORKDIR /app

COPY package.json .
COPY astro.config.mjs .
COPY tailwind.config.cjs .
COPY postcss.config.cjs .
COPY src ./src



FROM base AS build

RUN bun install --production
RUN bun astro build


FROM base AS development

RUN bun install

EXPOSE 4321

