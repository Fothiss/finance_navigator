FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
# --ignore-scripts: esbuild не требует postinstall, бинарник приходит из @esbuild/*
RUN npm install --ignore-scripts --no-audit --no-fund

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
