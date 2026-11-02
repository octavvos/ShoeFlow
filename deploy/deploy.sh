#!/usr/bin/env bash
# Serverda kodni yangilash va qayta ishga tushirish (qo'lda yoki GitHub Actions'dan).
set -euo pipefail

cd "$(dirname "$0")/.."
compose="docker compose -f docker-compose.prod.yml"

git pull --ff-only
# static/media — nginx o'qiydi, konteyner (uid 1000) yozadi
install -d -o 1000 -g 1000 -m 755 data/static data/media
$compose up -d --build --remove-orphans
docker image prune -f >/dev/null

echo "==> Health check"
for _ in $(seq 1 30); do
    if $compose exec -T web python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" 2>/dev/null; then
        echo "OK: $(git log -1 --format='%h %s')"
        exit 0
    fi
    sleep 2
done
echo "Xato: web servis javob bermayapti" >&2
$compose logs --tail 50 web >&2
exit 1
