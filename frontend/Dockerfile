# --- Etapa 1: Build ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

# IMPORTANTE: El nombre debe coincidir con el --build-arg del main.yml
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- Etapa 2: Production ---
FROM nginx:1.25-alpine

# Copiamos los archivos generados por Vite
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]