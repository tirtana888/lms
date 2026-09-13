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
# artifact backed up outside sites/ at build time — but "restore only if
# missing" left a stale copy in place across image updates (old content
# hashes on disk, new ones in assets.json, everything 404s). It never
# needs to survive a redeploy, so always replace it with this image's copy.
echo "Menyegarkan sites/assets dari backup build-time..."
rm -rf sites/assets
cp -r /home/frappe/assets-backup sites/assets
chown -R frappe:frappe sites/assets

# socketio.js (the Node realtime server) reads its Redis target from the
# bench-wide common_site_config.json, not the per-site config — set-config
# without -g only writes site_config.json, which socketio never reads, so it
# was falling back to 127.0.0.1:6379 and crash-looping. Set these globally,
# every boot (cheap, idempotent), not just on first site creation.
#
# Deliberately BEFORE the new-site/migrate branch below, not after: `bench
# migrate` needs a reachable redis_cache to run at all ("Service redis_cache
# is not running"), and on a from-scratch volume this config has never been
# written yet. Setting it after migrate meant the very first boot's migrate
# path (site already created by a previous, interrupted boot, but this
# config never reached) failed before ever reaching these lines - and
# `set -e` aborted the whole script right there, every restart, forever.
su frappe -c "bench set-config -g redis_cache '$REDIS_CACHE'"
su frappe -c "bench set-config -g redis_queue '$REDIS_QUEUE'"
su frappe -c "bench set-config -g redis_socketio '$REDIS_QUEUE'"

if [ ! -d "sites/$SITE_NAME" ]; then
  echo "Site $SITE_NAME belum ada, membuat baru..."
  # --no-mariadb-socket is deprecated and, on this Frappe version, no longer
  # grants the new DB user a wildcard host scope - the user ends up scoped to
  # whatever container IP happened to be current at creation time, and every
  # later restart (a new IP, since Railway containers don't keep one) then
  # fails migrate with "Access denied ... (using password: YES)". The
  # deprecation warning's own suggested replacement actually grants '%'
  # (any host), which is what a container whose IP can change on every
  # restart genuinely needs. Only touches the create-a-new-site path - an
  # already-existing site (the migrate branch below) never re-runs this.
  su frappe -c "bench new-site '$SITE_NAME' \
    --db-host '$DB_HOST' \
    --db-port '${DB_PORT:-3306}' \
    --mariadb-root-password '$MYSQL_ROOT_PASSWORD' \
    --admin-password '$ADMIN_PASSWORD' \
    --mariadb-user-host-login-scope='%' \
    --install-app lms"
else
  echo "Site $SITE_NAME sudah ada, jalankan bench migrate untuk sinkronkan schema..."
  # new-site only runs once; every later deploy that changes a doctype (new
  # field, new doctype) needs this to actually alter the existing tables —
  # code changes alone never touch the database.
  su frappe -c "bench --site '$SITE_NAME' migrate"
fi

su frappe -c "bench use '$SITE_NAME'"

# nginx ships with a placeholder rather than $host for X-Frappe-Site-Name (see
# nginx-app.conf): this container serves exactly one site, so every hostname
# pointed at it must resolve to that site instead of to a site named after
# whatever domain was typed. Substituted here because the name is only known
# from the environment at boot.
sed -i "s/__FRAPPE_SITE_NAME__/$SITE_NAME/g" /etc/nginx/conf.d/frappe.conf

# get_assets_json() caches assets.json in Redis under a *shared* key
# (frappe.cache.get_value('assets_json', ..., shared=True)) — a namespace
# `bench clear-cache` doesn't touch. A stale value from a previous image
# (different asset hashes) survives file/process changes indefinitely and
# every page loses its CSS/JS until that Redis key is dropped. Clear it on
# every boot, after the site and redis config are in place, so a new
# image's asset hashes always take effect.
su frappe -c "bench --site '$SITE_NAME' execute frappe.cache.delete_value --args \"['assets_json']\" --kwargs \"{'shared': True}\"" || true

exec supervisord -c /etc/supervisor/conf.d/frappe.conf
