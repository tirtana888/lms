#!/bin/bash
set -e

cd /home/frappe/frappe-bench

if [ -z "$SITE_NAME" ]; then
  echo "SITE_NAME env var belum di-set, keluar." >&2
  exit 1
fi

# The Railway volume mounts as an empty, root-owned dir over sites/, hiding
# what `bench get-app` wrote there at image-build time and blocking writes
# from the non-root frappe user bench insists on running as. Fix ownership
# first (root can always chown), then do everything else as frappe.
mkdir -p sites
chown -R frappe:frappe sites

if [ ! -f sites/apps.txt ]; then
  echo "sites/apps.txt hilang (volume kosong), membuat ulang..."
  su frappe -c "printf 'frappe\npayments\nlms\n' > sites/apps.txt"
fi
if [ ! -f sites/common_site_config.json ]; then
  su frappe -c "echo '{\"socketio_port\": 9000}' > sites/common_site_config.json"
fi

if [ ! -d "sites/$SITE_NAME" ]; then
  echo "Site $SITE_NAME belum ada, membuat baru..."
  su frappe -c "bench new-site '$SITE_NAME' \
    --db-host '$DB_HOST' \
    --db-port '${DB_PORT:-3306}' \
    --mariadb-root-password '$MYSQL_ROOT_PASSWORD' \
    --admin-password '$ADMIN_PASSWORD' \
    --no-mariadb-socket \
    --install-app lms"

  su frappe -c "bench --site '$SITE_NAME' set-config redis_cache '$REDIS_CACHE'"
  su frappe -c "bench --site '$SITE_NAME' set-config redis_queue '$REDIS_QUEUE'"
  su frappe -c "bench --site '$SITE_NAME' set-config redis_socketio '$REDIS_QUEUE'"
else
  echo "Site $SITE_NAME sudah ada, lewati bootstrap."
fi

su frappe -c "bench use '$SITE_NAME'"

exec supervisord -c /etc/supervisor/conf.d/frappe.conf
