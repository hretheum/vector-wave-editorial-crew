FROM node:20-alpine

ENV NODE_ENV=development \
    HOST=0.0.0.0 \
    PORT=3000

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# Copy the rest of the app
COPY . .

EXPOSE 3000

CMD ["sh", "-c", "npm run dev -- -p ${PORT} -H ${HOST}"]


