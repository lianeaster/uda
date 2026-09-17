# Деплой на AWS Lightsail

Покрокова інструкція для чистого інстансу. Робиться один раз; оновлення
версії — в кінці, окремим коротким розділом.

Домен у прикладах — `uda.org.ua`, шлях до проєкту — `/srv/uda`,
користувач — `uda`. Замінити на свої.

---

## 0. Що ми розгортаємо

| | |
|---|---|
| Інстанс | Lightsail, Frankfurt (eu-central-1), Ubuntu 24.04 LTS, план 4 GB / 2 vCPU / 80 GB |
| База | PostgreSQL на тому ж інстансі |
| Застосунок | gunicorn під systemd, сокет у `/run/uda/` |
| Фронт | nginx: TLS, статика, медіа |
| Медіа | локальний диск (бакет — пізніше, код до цього готовий) |

---

## 1. Інстанс у консолі Lightsail

1. **Create instance** → регіон **Frankfurt (eu-central-1)**.
2. **Linux/Unix** → **OS Only** → **Ubuntu 24.04 LTS**.
   Не брати готовий Django/Bitnami образ: там нестандартна структура каталогів.
3. План **$20/міс (4 GB RAM, 2 vCPU, 80 GB SSD)**.
4. Імʼя: `uda-prod`. Create.
5. **Networking → Create static IP** → прикріпити до інстансу.
   Поки прикріплений — безкоштовний. Без нього IP злетить при перезапуску.
6. **Networking → IPv4 Firewall**: лишити SSH (22), HTTP (80), HTTPS (443).
   Більше нічого не відкривати — Postgres назовні не потрібен.
7. **Snapshots → Enable automatic snapshots**.
8. У реєстратора домену: A-запис `uda.org.ua` → статичний IP.
   Те саме для `www`. Дочекатися поширення: `dig +short uda.org.ua`.

---

## 2. Базова підготовка сервера

Зайти: консольний SSH у Lightsail або `ssh -i ключ.pem ubuntu@<IP>`.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-dev build-essential \
                    postgresql postgresql-contrib libpq-dev \
                    nginx git certbot python3-certbot-nginx
sudo timedatectl set-timezone Europe/Kyiv
```

**Swap.** Образи Lightsail ідуть без нього. Це різниця між «gunicorn на мить
вперся в памʼять» і «OOM killer убив процес»:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

**Автоматичні оновлення безпеки:**

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 3. Користувач і каталоги

Застосунок не має ходити від `ubuntu` чи `root`:

```bash
sudo adduser --system --group --home /srv/uda uda
sudo usermod -a -G www-data uda
```

---

## 4. PostgreSQL

```bash
sudo -u postgres psql
```

У psql (пароль підставити свій, згенерований, не з прикладу):

```sql
CREATE USER uda WITH PASSWORD 'СЮДИ_ДОВГИЙ_ПАРОЛЬ';
CREATE DATABASE uda OWNER uda ENCODING 'UTF8';
-- Дрібні оптимізації Django: не питати часовий пояс у кожної сесії.
ALTER ROLE uda SET client_encoding TO 'utf8';
ALTER ROLE uda SET default_transaction_isolation TO 'read committed';
ALTER ROLE uda SET timezone TO 'UTC';
\q
```

Postgres слухає лише `localhost` за замовчуванням — так і лишаємо.

---

## 5. Код і віртуальне середовище

```bash
sudo -u uda git clone <URL_РЕПО> /srv/uda
cd /srv/uda
sudo -u uda python3 -m venv .venv
sudo -u uda .venv/bin/pip install --upgrade pip
sudo -u uda .venv/bin/pip install -r requirements.txt
```

---

## 6. Оточення

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # ключ
sudo cp /srv/uda/.env.example /etc/uda.env
sudo nano /etc/uda.env      # заповнити ключ, домени, пароль до бази
                            # значення — у подвійних лапках, як у зразку

# Читати має лише root і застосунок: усередині пароль до бази й секретний ключ.
sudo chown root:uda /etc/uda.env
sudo chmod 640 /etc/uda.env
```

Далі всі команди `manage.py` йдуть через обгортку `deploy/manage.sh` — вона
сама підхоплює `/etc/uda.env` і працює з каталогом проєкту. Перевірити конфіг:

```bash
sudo -u uda /srv/uda/deploy/manage.sh check --deploy
```

Має бути `System check identified no issues`. Якщо скаржиться на
`DJANGO_SECRET_KEY` — ключ не заповнено.

---

## 7. База: міграції і дані

```bash
sudo -u uda /srv/uda/deploy/manage.sh migrate
```

### Перенести наявні дані з локальної SQLite

Якщо в локальній базі є потрібний контент (картки «Про мене», викладачі,
групи), то **на своїй машині**:

```bash
.venv/bin/python manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.Permission \
    --exclude admin.logentry --exclude sessions \
    --indent 2 > dump.json
```

Виключення обовʼязкові: `contenttypes` і `auth.Permission` Django створює сам
під час `migrate`, і без `--exclude` вони конфліктують при завантаженні.

Залити на сервер і прийняти:

```bash
scp dump.json ubuntu@<IP>:/tmp/dump.json
sudo mv /tmp/dump.json /srv/uda/dump.json && sudo chown uda:uda /srv/uda/dump.json
sudo -u uda /srv/uda/deploy/manage.sh loaddata dump.json
sudo rm /srv/uda/dump.json
```

### Медіа копіюється окремо

Каталог `media/` у `.gitignore`, тож з клоном репозиторію фото **не приїдуть**.
Зараз це 19 файлів, десь мегабайт. З локальної машини:

```bash
rsync -avz --rsync-path="sudo rsync" media/ ubuntu@<IP>:/srv/uda/media/
ssh ubuntu@<IP> "sudo chown -R uda:www-data /srv/uda/media"
```

### Суперкористувач

```bash
sudo -u uda /srv/uda/deploy/manage.sh createsuperuser
```

Якщо дані заливалися через `loaddata`, адміністратор уже може бути серед них —
тоді цей крок пропустити.

---

## 8. Статика

```bash
sudo -u uda /srv/uda/deploy/manage.sh collectstatic --noinput
```

---

## 9. gunicorn під systemd

```bash
sudo cp /srv/uda/deploy/uda.service /etc/systemd/system/uda.service
sudo systemctl daemon-reload
sudo systemctl enable --now uda
systemctl status uda
```

Має бути `active (running)`. Якщо ні — `journalctl -u uda -n 50`.

---

## 10. nginx

```bash
sudo cp /srv/uda/deploy/nginx.conf /etc/nginx/sites-available/uda
sudo nano /etc/nginx/sites-available/uda        # підставити свої домени
sudo ln -s /etc/nginx/sites-available/uda /etc/nginx/sites-enabled/uda
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

nginx має читати сокет — дати йому право зайти в каталог проєкту:

```bash
sudo chmod o+x /srv/uda
sudo chown -R uda:www-data /srv/uda/staticfiles /srv/uda/media
```

---

## 11. HTTPS

**Порядок важливий.** У `config/settings.py` при `DJANGO_DEBUG=0` увімкнено
`SECURE_SSL_REDIRECT`, тож до отримання сертифіката сайт по http піде в
нескінченний редирект. Тому:

```bash
sudo certbot --nginx -d uda.org.ua -d www.uda.org.ua
```

Certbot сам допише блок 443, редирект з 80 і шляхи до сертифікатів, зберігши
location-и зі свого конфігу. Перевірити автопродовження:

```bash
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

Тепер відкрити `https://uda.org.ua` — має бути сайт зі стилями,
логін працює, фото профілів видно.

---

## 12. Бекапи

```bash
sudo cp /srv/uda/deploy/backup.sh /usr/local/bin/uda-backup
sudo chmod +x /usr/local/bin/uda-backup
sudo /usr/local/bin/uda-backup        # прогнати руками, переконатися що працює
sudo crontab -e
```

Рядок у crontab:

```
17 3 * * * /usr/local/bin/uda-backup >> /var/log/uda-backup.log 2>&1
```

Раз на квартал — тестове відновлення. Бекап, який жодного разу не
відновлювали, бекапом вважати не можна.

---

## Оновлення версії

```bash
cd /srv/uda
sudo -u uda git pull
sudo -u uda .venv/bin/pip install -r requirements.txt
sudo -u uda /srv/uda/deploy/manage.sh migrate
sudo -u uda /srv/uda/deploy/manage.sh collectstatic --noinput
sudo systemctl reload uda
```

`reload` замість `restart` — gunicorn піднімає нових воркерів і гасить старих,
поточні запити не обриваються.

---

## Якщо щось не працює

| Симптом | Куди дивитися |
|---|---|
| 502 Bad Gateway | `journalctl -u uda -n 50` — застосунок не піднявся або nginx не дістає сокет |
| 400 Bad Request | домен не вписаний у `DJANGO_ALLOWED_HOSTS` |
| Сайт без стилів | не робили `collectstatic`, або права на `staticfiles/` |
| Фото 404 | права на `media/`, або файли не скопійовані (крок 7) |
| 403 на формах | `DJANGO_CSRF_TRUSTED_ORIGINS` — але зазвичай виводиться сам з `ALLOWED_HOSTS` |
| Нескінченний редирект | сертифіката ще немає, а `DEBUG=0` вже увімкнено — доробити крок 11 |
| 500 без пояснень | `journalctl -u uda -n 100` — трейсбеки пишуться в журнал |
| Сайт раптом «задумався» | `free -h` і графік CPU у Lightsail: могли скінчитися burst-кредити |

---

## Що далі

Коли дійде до бібліотеки — медіа переїжджає в Lightsail bucket. Код до цього
готовий: у базі лежать відносні шляхи, шаблони ходять через `.photo.url`,
жорстких `/media/` ніде немає. Міграція = синхронізувати файли в бакет,
змінити `STORAGES`, прибрати `location /media/` з nginx.

Головне правило до того моменту: **книжки на диск інстансу не заливати**.
Фото профілів там можуть жити роками, бібліотека — ні.
