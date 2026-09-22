# Brevetto frontend — Next.js 14 (App Router) en modo desarrollo
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
