#!/usr/bin/env bash
# Ubuntu serverga birinchi marta o'rnatish (root sifatida). Serverda boshqa saytlar bo'lsa ham
# ularga tegmaydi: mavjud nginx'ga faqat yangi sayt qo'shadi.
#   bash server-setup.sh <domen>
set -euo pipefail

DOMAIN=${1:?"Foydalanish: bash server-setup.sh <domen>"}
APP_DIR=/opt/shoeflow
REPO=https://github.com/octavvos/ShoeFlow.git
WEB_PORT=${WEB_PORT:-8010}

echo "==> Paketlar (faqat yo'qlari — mavjud nginx yangilanmaydi)"
missing=()
for pkg in ca-certificates curl git openssl nginx certbot python3-certbot-nginx; do
    dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
done
if [ ${#missing[@]} -gt 0 ]; then
    apt-get update -q
    apt-get install -y -q "${missing[@]}"
fi

if ! command -v docker >/dev/null; then
    echo "==> Docker"
    curl -fsSL https://get.docker.com | sh
elif ! docker compose version >/dev/null 2>&1; then
    # Ubuntu'ning docker.io paketida compose yo'q; daemon'ni qayta ishga tushirmasdan faqat plagin
    echo "==> docker compose plagini"
    apt-get install -y -q docker-compose-v2
fi

echo "==> Kod: $APP_DIR"
[ -d "$APP_DIR/.git" ] || git clone "$REPO" "$APP_DIR"
cd "$APP_DIR"

if [ ! -f .env ]; then
    echo "==> .env (tasodifiy parollar bilan)"
    secret=$(openssl rand -base64 48 | tr -d '\n/+=')
    db_password=$(openssl rand -hex 24)
    sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$secret|" \
        -e "s|CHANGE_ME|$db_password|g" \
        -e "s|api.example.uz|$DOMAIN|g" \
        -e "s|^WEB_PORT=.*|WEB_PORT=$WEB_PORT|" \
        -e "s|^DJANGO_HTTPS=.*|DJANGO_HTTPS=False|" \
        -e "s|https://$DOMAIN|http://$DOMAIN|" \
        .env.prod.example > .env
    chmod 600 .env
fi

echo "==> nginx: $DOMAIN"
sed -e "s|__DOMAIN__|$DOMAIN|g" -e "s|__APP_DIR__|$APP_DIR|g" -e "s|__WEB_PORT__|$WEB_PORT|g" \
    deploy/nginx.conf > /etc/nginx/sites-available/shoeflow
ln -sf /etc/nginx/sites-available/shoeflow /etc/nginx/sites-enabled/shoeflow
if ! nginx -t; then
    # Serverdagi boshqa saytlar buzilgan konfiguratsiya bilan qolmasin
    rm -f /etc/nginx/sites-enabled/shoeflow
    echo "nginx konfiguratsiyasida xato — shoeflow sayti o'chirildi" >&2
    exit 1
fi
systemctl reload nginx

echo "==> Demo ma'lumotlarni har kuni 03:00 da tiklash"
echo "0 3 * * * root $APP_DIR/deploy/reset-demo.sh >> /var/log/shoeflow-demo-reset.log 2>&1" \
    > /etc/cron.d/shoeflow-demo-reset

./deploy/deploy.sh
./deploy/reset-demo.sh

echo "==> HTTPS"
server_ip=$(curl -fsS https://api.ipify.org || true)
if getent hosts "$DOMAIN" | grep -q "^$server_ip "; then
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect
    # Sertifikat bor — endi Django ham HTTPS rejimiga o'tadi
    sed -i -e "s|^DJANGO_HTTPS=.*|DJANGO_HTTPS=True|" -e "s|http://$DOMAIN|https://$DOMAIN|" .env
    docker compose -f docker-compose.prod.yml up -d
else
    echo "DNS hali $DOMAIN -> $server_ip emas. A-yozuv qo'shilgach: certbot --nginx -d $DOMAIN"
fi

echo "Tayyor: https://$DOMAIN/api/docs/"
