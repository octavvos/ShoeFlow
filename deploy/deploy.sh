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

echo "==> Frontend"
# Frontend'ni CI build qiladi (kichik serverda Node build xotiraga sig'maydi) va Release'ga qo'yadi
repo=$(git config --get remote.origin.url | sed -e 's|\.git$||' -e 's|^git@github.com:|https://github.com/|')
tmp=$(mktemp -d)
if curl -fsSL "$repo/releases/download/frontend-latest/frontend.tar.gz" -o "$tmp/frontend.tar.gz"; then
    mkdir -p "$tmp/dist" && tar -xzf "$tmp/frontend.tar.gz" -C "$tmp/dist"
    rm -rf data/frontend.old && { [ ! -d data/frontend ] || mv data/frontend data/frontend.old; }
    mv "$tmp/dist" data/frontend && chmod 755 data/frontend && rm -rf data/frontend.old
    echo "frontend: $(cat data/frontend/VERSION 2>/dev/null || echo '?')"
else
    echo "Ogohlantirish: frontend build topilmadi, eski versiya qoldi" >&2
fi
rm -rf "$tmp"

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
