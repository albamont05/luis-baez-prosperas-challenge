# --- Etapa 1: Build ---
# Actualizado de node:18-alpine a node:20-alpine
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Ahora este comando funcionará correctamente
RUN npm run build

# --- Etapa 2: Production ---
FROM nginx:1.25-alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]