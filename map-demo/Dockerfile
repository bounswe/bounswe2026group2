# Use the lightweight Nginx Alpine image
FROM nginx:alpine

# Copy the index.html file to the default Nginx public directory
COPY index.html /usr/share/nginx/html/index.html

# Expose port 80 for the server
EXPOSE 80

# Run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
