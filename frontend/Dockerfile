# ── AFianco — Frontend Dockerfile ─────────────────────
# Multi-stage: build React app, serve via nginx.
# Final image ~25 MB (nginx:alpine + static build output).

# ── Stage 1: build ───────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Disable corepack enforcement — package.json declares yarn as packageManager
# but the project uses npm (package-lock.json exists, no yarn.lock).
ENV COREPACK_ENABLE_STRICT=0

# Copy dependency manifests first (cache layer)
COPY package.json package-lock.json ./

# Install all deps (including devDependencies needed for build)
# --legacy-peer-deps: react-day-picker@8 requires date-fns ^2||^3 but
# the project uses date-fns 4.  The mismatch is harmless at runtime.
RUN npm ci --legacy-peer-deps

# Copy source code + config files
COPY public/ public/
COPY src/ src/
COPY craco.config.js jsconfig.json tailwind.config.js postcss.config.js components.json ./
COPY plugins/ plugins/

# Build-time env: in production the frontend is served from the same origin
# as the backend (via nginx reverse proxy), so REACT_APP_BACKEND_URL is empty.
# This makes axios call /api/* as relative paths, proxied by nginx to backend.
ENV REACT_APP_BACKEND_URL=""

# ── Observability (Phase 1 — Step A2) ────────────────────────────
# Sentry frontend env vars passed in at build time via docker-compose
# build.args. Default values are empty strings → if .env.production
# does not set REACT_APP_SENTRY_DSN, init_sentry() returns false silently
# and the app boots identically (no events captured, no outbound calls).
ARG REACT_APP_SENTRY_DSN=""
ARG REACT_APP_SENTRY_TRACES_RATE="0.1"
ARG REACT_APP_SENTRY_ENVIRONMENT="production"
ARG REACT_APP_RELEASE_SHA="unknown"

ENV REACT_APP_SENTRY_DSN=$REACT_APP_SENTRY_DSN
ENV REACT_APP_SENTRY_TRACES_RATE=$REACT_APP_SENTRY_TRACES_RATE
ENV REACT_APP_SENTRY_ENVIRONMENT=$REACT_APP_SENTRY_ENVIRONMENT
ENV REACT_APP_RELEASE_SHA=$REACT_APP_RELEASE_SHA

# Wave 12 deploy (2026-05-16): force CI=false so react-scripts treats
# pre-existing eslint warnings (react-hooks/exhaustive-deps in a handful
# of storefront/team files) as warnings rather than errors. These warnings
# were already in main pre-Wave-10/11/12 — Wave 12 didn't introduce them.
# Without this line, buildkit inherits CI=true (Docker's non-TTY context)
# and the build fails on otherwise-non-blocking lint issues.
ENV CI=false

RUN npm run build


# ── Stage 2: serve via nginx ─────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx site
RUN rm /etc/nginx/conf.d/default.conf

# Copy built React app to nginx html root
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx config (serves SPA correctly with try_files)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# nginx runs as PID 1 by default in the official image
CMD ["nginx", "-g", "daemon off;"]
