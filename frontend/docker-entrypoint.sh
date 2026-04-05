#!/bin/sh
set -e

# Replace placeholder in config.js with the actual API_BASE_URL env var
sed -i "s|__API_BASE_URL__|${API_BASE_URL}|g" /usr/share/nginx/html/config.js

exec "$@"
