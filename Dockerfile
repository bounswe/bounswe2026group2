# Base image
FROM node:18

# App directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies (varsa)
RUN npm install

# App port
EXPOSE 3000

# Start application
CMD ["npm", "start"]
