FROM ghcr.io/tirtana888/lms-bench:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      supervisor nginx-light \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's#pid /run/nginx.pid;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && sed -i 's/^user .*/user frappe;/' /etc/nginx/nginx.conf \
    && mkdir -p /var/log/nginx /var/lib/nginx/body /var/lib/nginx/proxy \
         /var/lib/nginx/fastcgi /var/lib/nginx/scgi /var/lib/nginx/uwsgi \
    && chown -R frappe:frappe /var/log/nginx /var/lib/nginx /etc/nginx

# lms's package.json depends on @framework/ui via `link:../../frappe/ui`,
# a yarn link resolved relative to apps/lms/frontend — valid only once
# apps/frappe/ui already exists as a sibling app. bench_init's --apps_path
# installs every app in one shot before that sibling is reliably linkable,
# so building lms alongside frappe/payments fails with "Rollup failed to
# resolve import @framework/ui/...". Installing it here, after frappe is
# already in place, and pointing the link at frappe/ui directly (as the
# lms repo's own vite.config.js comment prescribes) avoids that ordering
# problem entirely.
USER frappe
WORKDIR /home/frappe/frappe-bench
# lms/frontend/src/socket.js statically imports the `socketio_port` key out
# of common_site_config.json (Vite treats JSON keys as named ES exports), so
# a missing key is a build-time Rollup error, not just an empty runtime
# value — the base image's config is still the bare "{}" bench init wrote.
RUN echo '{"socketio_port": 9000}' > sites/common_site_config.json \
    && bench get-app https://github.com/tirtana888/lms --branch v2.63.0 --skip-assets \
    && ln -sfn /home/frappe/frappe-bench/apps/frappe/ui \
         apps/lms/frontend/node_modules/@framework/ui \
    && bench build \
    && cp -r sites/assets /home/frappe/assets-backup

USER root
COPY railway/supervisord.conf /etc/supervisor/conf.d/frappe.conf
COPY railway/nginx-app.conf /etc/nginx/conf.d/frappe.conf
COPY railway/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Stay root at container start: the Railway volume mounts empty and
# root-owned over sites/, so the entrypoint needs root to chown it before
# bench can write there. supervisord itself then keeps running as root (so
# it can start nginx normally) while each bench-based program below drops
# to user=frappe individually — bench refuses to run as root outright.
USER root
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
