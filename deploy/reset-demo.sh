#!/usr/bin/env bash
# Ochiq demo server uchun: bazani tozalab, demo ma'lumotlarni qayta yaratadi.
# Demo login/parollar hammaga ma'lum — kimdir ma'lumotlarni buzsa ham, ertasi kuni tiklanadi.
# Haqiqiy firma ma'lumotlari turgan serverda ISHLATMANG.
set -euo pipefail

cd "$(dirname "$0")/.."
docker compose -f docker-compose.prod.yml exec -T web sh -c \
    "python manage.py flush --noinput && python manage.py seed_demo"
echo "$(date '+%F %T') demo ma'lumotlar tiklandi"
