FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY map.html /usr/share/nginx/html/map.html
COPY login.js /usr/share/nginx/html/login.js

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]