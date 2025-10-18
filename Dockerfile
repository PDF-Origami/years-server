# Stage 1: Build the application (if you need to compile/build assets)
FROM node:20-alpine AS builder

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (or yarn.lock) to leverage Docker cache
COPY package*.json ./

# Install application dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

RUN npm run build

# Stage 2: Create the final production image
FROM node:20-alpine

# Set the working directory for the final image
WORKDIR /usr/src/app

# Copy only the necessary files from the build stage
COPY --from=builder /usr/src/app/node_modules ./node_modules
COPY --from=builder /usr/src/app/package*.json ./
COPY --from=builder /usr/src/app/build ./build
COPY --from=builder /usr/src/app/db.* ./

# Expose the port the Node.js app runs on (e.g., 3000)
EXPOSE 8000

# Define the command to run your server
CMD [ "npm", "run", "start" ]