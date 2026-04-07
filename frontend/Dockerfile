FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY forgot-password.html /usr/share/nginx/html/forgot-password.html
COPY register.html /usr/share/nginx/html/register.html
COPY map.html /usr/share/nginx/html/map.html
COPY story-create.html /usr/share/nginx/html/story-create.html
COPY story-detail.html /usr/share/nginx/html/story-detail.html
COPY profile.html /usr/share/nginx/html/profile.html
COPY edit-profile.html /usr/share/nginx/html/edit-profile.html
COPY profile.js /usr/share/nginx/html/profile.js
COPY edit-profile.js /usr/share/nginx/html/edit-profile.js
COPY login.js /usr/share/nginx/html/login.js
COPY auth.js /usr/share/nginx/html/auth.js
COPY config.js /usr/share/nginx/html/config.js
COPY docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
