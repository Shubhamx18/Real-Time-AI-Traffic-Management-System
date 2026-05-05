# ═══════════════════════════════════════════════════════
# Frontend Dockerfile — React Traffic Dashboard
# Multi-stage: build + nginx serve
# ═══════════════════════════════════════════════════════

# Stage 1: Build
FROM node:18-alpine AS build

WORKDIR /app

# Install dependencies first (cached layer)
COPY package.json package-lock.json* ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built React app
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config (separate file avoids heredoc escaping issues)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
