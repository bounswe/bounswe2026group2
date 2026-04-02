FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY register.html /usr/share/nginx/html/register.html
COPY map.html /usr/share/nginx/html/map.html
COPY story-create.html /usr/share/nginx/html/story-create.html
COPY story-detail.html /usr/share/nginx/html/story-detail.html
COPY login.js /usr/share/nginx/html/login.js

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]