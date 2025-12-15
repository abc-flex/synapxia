FROM oven/bun:1.1.0

WORKDIR /app

COPY package.json .
COPY astro.config.mjs .
COPY tailwind.config.cjs .
COPY postcss.config.cjs .
COPY src ./src

RUN bun install
RUN bun astro build

EXPOSE 4321
CMD ["bun", "astro", "preview", "--host", "0.0.0.0", "--port", "4321"]
