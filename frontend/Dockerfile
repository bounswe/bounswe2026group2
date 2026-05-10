FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY forgot-password.html /usr/share/nginx/html/forgot-password.html
COPY register.html /usr/share/nginx/html/register.html
COPY map.html /usr/share/nginx/html/map.html
COPY story-create.html /usr/share/nginx/html/story-create.html
COPY story-detail.html /usr/share/nginx/html/story-detail.html
COPY search.html /usr/share/nginx/html/search.html
COPY admin-panel.html /usr/share/nginx/html/admin-panel.html
COPY profile.html /usr/share/nginx/html/profile.html
COPY edit-profile.html /usr/share/nginx/html/edit-profile.html
COPY saved.html /usr/share/nginx/html/saved.html
COPY profile.js /usr/share/nginx/html/profile.js
COPY edit-profile.js /usr/share/nginx/html/edit-profile.js
COPY login.js /usr/share/nginx/html/login.js
COPY auth.js /usr/share/nginx/html/auth.js
COPY config.js /usr/share/nginx/html/config.js
COPY saves.js /usr/share/nginx/html/saves.js
COPY saved.js /usr/share/nginx/html/saved.js
COPY likes.js /usr/share/nginx/html/likes.js
COPY comments.js /usr/share/nginx/html/comments.js
COPY recording.js /usr/share/nginx/html/recording.js
COPY tags.js /usr/share/nginx/html/tags.js
COPY story-edit.html /usr/share/nginx/html/story-edit.html
COPY docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
