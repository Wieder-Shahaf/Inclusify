# Inclusify Frontend Dockerfile
# Multi-stage build for Next.js application with standalone output

# ============================================
# Stage 1: Dependencies - Install npm packages
# ============================================
FROM node:22-slim AS deps

WORKDIR /app

# Copy package.json only (skip lockfile to avoid platform mismatch)
COPY frontend/package.json ./

# Install dependencies (--force bypasses platform checks for optional deps)
RUN npm cache clean --force && npm install --legacy-peer-deps --force

# ============================================
# Stage 2: Development - Hot-reload enabled
# ============================================
FROM node:22-slim AS development

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application code
COPY frontend/ .

# In dev mode with volume mounts, run as root to avoid permission issues
# Production stage still uses non-root user for security

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Development with hot-reload
CMD ["npm", "run", "dev"]

# ============================================
# Stage 3: Builder - Build Next.js application
# ============================================
FROM node:22-slim AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application code
COPY frontend/ .

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN npm run build

# ============================================
# Stage 4: Runner - Production optimized
# ============================================
FROM node:22-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Create non-root user
RUN groupadd --gid 1001 nextjs \
    && useradd --uid 1001 --gid 1001 --shell /bin/bash nextjs

# Copy public assets (PITFALL #3: must copy explicitly)
COPY --from=builder /app/public ./public

# Copy standalone output
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
