# Frontend Dockerfile - Development Mode
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code (will be overwritten by volume mount in dev)
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Default command (overridden in docker-compose for dev)
CMD ["npm", "run", "dev", "--", "--host"]

