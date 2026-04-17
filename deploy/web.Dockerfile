FROM node:22-alpine

WORKDIR /app/apps/web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web /app/apps/web

ENV NEXT_TELEMETRY_DISABLED=1

# RU: Web image держим на Node 22, потому что локальный стек уже на Node 22 и часть зависимостей предупреждает/ожидает runtime не ниже 22-й ветки.
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
