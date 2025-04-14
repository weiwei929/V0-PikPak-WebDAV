# Build stage for JavaScript
FROM node:16-alpine AS js-build
WORKDIR /app
COPY package.json webpack.config.js ./
COPY static/js ./static/js
RUN npm install && npm run build

# Python application stage
FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Copy built JavaScript from the build stage
COPY --from=js-build /app/static/dist ./static/dist

# Update index.html to use bundled JavaScript
RUN sed -i 's|<script src="js/main.js"></script>|<script src="dist/main.bundle.js"></script>|g' static/index.html

EXPOSE 5000

CMD ["python", "app.py"]
