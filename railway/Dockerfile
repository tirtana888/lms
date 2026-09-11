FROM ghcr.io/tirtana888/lms-bench:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor nginx \
    && rm -rf /var/lib/apt/lists/*

COPY railway/supervisord.conf /etc/supervisor/conf.d/frappe.conf
COPY railway/nginx-app.conf /etc/nginx/conf.d/frappe.conf
COPY railway/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
