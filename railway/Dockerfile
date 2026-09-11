FROM ghcr.io/tirtana888/lms-bench:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      supervisor nginx-light \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's#pid /run/nginx.pid;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && sed -i '/^user /d' /etc/nginx/nginx.conf \
    && mkdir -p /var/log/nginx /var/lib/nginx/body /var/lib/nginx/proxy \
         /var/lib/nginx/fastcgi /var/lib/nginx/scgi /var/lib/nginx/uwsgi \
    && chown -R frappe:frappe /var/log/nginx /var/lib/nginx /etc/nginx

COPY railway/supervisord.conf /etc/supervisor/conf.d/frappe.conf
COPY railway/nginx-app.conf /etc/nginx/conf.d/frappe.conf
COPY railway/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# bench refuses to run as root — drop back to the frappe user frappe_docker's
# base image already created, for the entrypoint and everything supervisord spawns.
USER frappe
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
