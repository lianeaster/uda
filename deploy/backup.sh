#!/usr/bin/env bash
# Щоденний бекап: дамп бази + архів медіа.
#
#   sudo cp deploy/backup.sh /usr/local/bin/uda-backup
#   sudo chmod +x /usr/local/bin/uda-backup
#
# Планує запуск uda-backup.timer (див. deploy/uda-backup.timer). Через cron
# теж можна, але пакета cron на мінімальних образах може не бути — systemd є
# завжди, тож таймер надійніший.
#
# Увага: це локальні копії на тому ж диску. Вони рятують від «видалили не те»,
# але не від втрати інстансу. Автоснапшоти Lightsail треба ввімкнути окремо,
# а найцінніше варто вивозити ще й за межі акаунта AWS.

set -euo pipefail

BACKUP_DIR=/var/backups/uda
KEEP_DAYS=30
STAMP=$(date +%F)

# Звідси беремо DJANGO_DB_* — ті самі, що й застосунок.
set -a
# shellcheck disable=SC1091
source /etc/uda.env
set +a

mkdir -p "$BACKUP_DIR"

# -Fc — стиснутий формат, відновлюється через pg_restore.
PGPASSWORD="$DJANGO_DB_PASSWORD" pg_dump \
    --host="$DJANGO_DB_HOST" \
    --port="$DJANGO_DB_PORT" \
    --username="$DJANGO_DB_USER" \
    --format=c \
    --file="$BACKUP_DIR/db-$STAMP.dump" \
    "$DJANGO_DB_NAME"

# Медіа в git немає, тож без цього архіву фото після втрати диска не повернути.
tar --create --gzip \
    --file="$BACKUP_DIR/media-$STAMP.tar.gz" \
    --directory=/srv/uda media

find "$BACKUP_DIR" -type f -mtime +"$KEEP_DAYS" -delete

echo "Бекап $STAMP готовий:"
ls -lh "$BACKUP_DIR" | tail -2
