# Brevetto frontend — Next.js 14 (App Router) en modo desarrollo
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# La imagen node:alpine trae el usuario sin privilegios "node"; lo usamos
# para no ejecutar la aplicación como root (Security-Analysis §4).
RUN chown -R node:node /app
USER node

EXPOSE 3000

CMD ["npm", "run", "dev"]
