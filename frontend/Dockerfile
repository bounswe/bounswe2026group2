FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY map.html /usr/share/nginx/html/map.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]