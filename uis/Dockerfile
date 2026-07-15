FROM node:20-alpine

WORKDIR /app/uis

# Install dependencies for each Next.js app separately.
COPY website/package*.json /app/uis/website/
COPY backoffice/package*.json /app/uis/backoffice/
RUN cd /app/uis/website && npm install
RUN cd /app/uis/backoffice && npm install

# Copy UI source code and startup script.
COPY . /app/uis
RUN chmod +x /app/uis/start.sh

EXPOSE 3000 3001

CMD ["/app/uis/start.sh"]
