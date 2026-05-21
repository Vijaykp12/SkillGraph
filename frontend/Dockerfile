FROM node:18-alpine

WORKDIR /frontend

COPY package.json ./
RUN npm install

COPY . .

# Run development server to align with sandbox environments
EXPOSE 3000

CMD ["npm", "run", "dev"]
