# ---- build ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Adjust if your build script differs
RUN npm run build

# ---- serve ----
FROM nginx:alpine
# If Angular outputs to dist/<app-name>, change path accordingly
COPY --from=build /app/dist/food-analyzer-ui /usr/share/nginx/html
# Basic Nginx for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
