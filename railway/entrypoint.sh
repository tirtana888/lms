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

# sites/assets (compiled CSS/JS from `bench build`) is also inside the
# volume, so it's wiped empty just like apps.txt was. It's a pure build
# artifact — identical for every instance of this image — backed up
# outside sites/ at build time, so just restore it if missing.
if [ ! -d sites/assets ]; then
  echo "sites/assets hilang (volume kosong), restore dari backup build-time..."
  cp -r /home/frappe/assets-backup sites/assets
  chown -R frappe:frappe sites/assets
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
else
  echo "Site $SITE_NAME sudah ada, lewati bootstrap."
fi

# socketio.js (the Node realtime server) reads its Redis target from the
# bench-wide common_site_config.json, not the per-site config — set-config
# without -g only writes site_config.json, which socketio never reads, so it
# was falling back to 127.0.0.1:6379 and crash-looping. Set these globally,
# every boot (cheap, idempotent), not just on first site creation.
su frappe -c "bench set-config -g redis_cache '$REDIS_CACHE'"
su frappe -c "bench set-config -g redis_queue '$REDIS_QUEUE'"
su frappe -c "bench set-config -g redis_socketio '$REDIS_QUEUE'"

su frappe -c "bench use '$SITE_NAME'"

exec supervisord -c /etc/supervisor/conf.d/frappe.conf
