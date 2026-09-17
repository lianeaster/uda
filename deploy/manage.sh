#!/usr/bin/env bash
# Обгортка навколо manage.py для сервера.
#
# Піднімає оточення з /etc/uda.env і запускає команду в потрібному каталозі,
# щоб не тягати довгий рядок зі змінними щоразу. Запускати від користувача uda:
#
#   sudo -u uda /srv/uda/deploy/manage.sh migrate
#   sudo -u uda /srv/uda/deploy/manage.sh collectstatic --noinput
#   sudo -u uda /srv/uda/deploy/manage.sh createsuperuser
#
# Щоб це працювало, /etc/uda.env має бути читабельним для групи uda:
#   sudo chown root:uda /etc/uda.env && sudo chmod 640 /etc/uda.env

set -euo pipefail

ENV_FILE=${UDA_ENV_FILE:-/etc/uda.env}
APP_DIR=${UDA_APP_DIR:-/srv/uda}

if [[ ! -r "$ENV_FILE" ]]; then
    echo "Не читається $ENV_FILE — перевірте права (має бути root:uda, 640)." >&2
    exit 1
fi

# set -a експортує все, що прочитається з файлу; так значення з пробілами
# і спецсимволами не ламаються, на відміну від env $(grep ... | xargs).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

cd "$APP_DIR"
exec .venv/bin/python manage.py "$@"
