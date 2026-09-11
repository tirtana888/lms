#!/bin/bash
set -e

cd /home/frappe/frappe-bench

if [ -z "$SITE_NAME" ]; then
  echo "SITE_NAME env var belum di-set, keluar." >&2
  exit 1
fi

if [ ! -d "sites/$SITE_NAME" ]; then
  echo "Site $SITE_NAME belum ada, membuat baru..."
  bench new-site "$SITE_NAME" \
    --db-host "$DB_HOST" \
    --db-port "${DB_PORT:-3306}" \
    --mariadb-root-password "$MYSQL_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --no-mariadb-socket \
    --install-app lms

  bench --site "$SITE_NAME" set-config redis_cache "$REDIS_CACHE"
  bench --site "$SITE_NAME" set-config redis_queue "$REDIS_QUEUE"
  bench --site "$SITE_NAME" set-config redis_socketio "$REDIS_QUEUE"
else
  echo "Site $SITE_NAME sudah ada, lewati bootstrap."
fi

bench use "$SITE_NAME"

exec supervisord -c /etc/supervisor/conf.d/frappe.conf
