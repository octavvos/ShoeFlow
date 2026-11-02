# ShoeFlow CRM

[![CI](https://github.com/octavvos/ShoeFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/octavvos/ShoeFlow/actions/workflows/ci.yml)

Oyoq kiyim ishlab chiqaruvchi firma uchun CRM: mijozlar, katalog (model, rang, razmer), buyurtmalar, ishlab chiqarish, ombor va moliya.

**Stek:** Python 3.12 · Django 5.2 · DRF · PostgreSQL 16 · Redis · Celery · JWT · Docker

## Ishga tushirish

```bash
cp .env.example .env          # kerak bo'lsa qiymatlarni o'zgartiring
make up                       # db, redis, web, celery, celery-beat
make seed                     # demo ma'lumotlar (ixtiyoriy)
make superuser                # birinchi admin
```

`make seed` rollar bo'yicha foydalanuvchilar (`direktor`, `menejer1`, `omborchi`, ...), katalog, mijozlar, ikkita ombor va qoldiqlar, har xil holatdagi buyurtmalarni yaratadi. Hammasining paroli: `Demo-12345`.

- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/docs/
- Admin panel: http://localhost:8000/admin/

### Docker'siz (lokal)

```bash
uv sync
# .env'da DATABASE_URL hostini localhost qiling
uv run python manage.py migrate
uv run python manage.py runserver
```

## Testlar va lint

```bash
make up        # testlar compose'dagi Postgres'dan foydalanadi (localhost:5433)
make test
make lint
uv run pre-commit install   # har commitdan oldin ruff avtomatik ishlaydi
```

Har bir push'da GitHub Actions lint, migratsiyalar tekshiruvi va testlarni (coverage bilan) ishga tushiradi.

Boshqa bazada ishlatish uchun: `DATABASE_URL=postgres://... uv run pytest`.

## Ma'lumotlar modeli

```mermaid
erDiagram
    User ||--o{ Customer : "menejer"
    Customer ||--o{ Contact : ""
    Customer ||--o{ Interaction : ""
    User ||--o{ Interaction : "muallif"
    Category ||--o{ ProductModel : ""
    SizeRun |o--o{ ProductModel : "asosiy razmer qatori"
    ProductModel ||--o{ Variant : ""
    Color ||--o{ Variant : ""
    Warehouse ||--o{ StockBalance : ""
    Variant ||--o{ StockBalance : ""
    Warehouse ||--o{ StockMovement : ""
    Variant ||--o{ StockMovement : ""
    Customer ||--o{ Order : ""
    Warehouse ||--o{ Order : "jo'natish ombori"
    Order ||--|{ OrderItem : ""
    Variant ||--o{ OrderItem : ""

    Customer {
        string name
        string type "diler / ulgurji / chakana / marketpleys"
        string region
        string inn
        decimal credit_limit
        string currency
    }
    ProductModel {
        string article
        string gender
        string season
        decimal wholesale_price
        decimal dealer_price
        decimal retail_price
    }
    Variant {
        int size
        string barcode "EAN-13"
    }
    SizeRun {
        json sizes "razmer -> juft soni"
    }
    StockBalance {
        int quantity "joriy qoldiq"
        int reserved "tasdiqlangan buyurtmalar uchun"
    }
    StockMovement {
        string type "kirim / jo'natish / ko'chirish / inventarizatsiya / brak"
        int quantity "+ kirim, - chiqim"
        int balance_after
        string reference
    }
    Order {
        string status "draft -> confirmed -> shipped -> delivered"
        string price_type "ulgurji / diler / chakana"
        decimal discount_percent
        decimal total_amount
    }
    OrderItem {
        int quantity "juft"
        decimal price
    }
```

### Buyurtma holatlari

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> confirmed: confirm (ombordan rezerv)
    draft --> cancelled: cancel
    confirmed --> shipped: ship (qoldiq va rezerv kamayadi)
    confirmed --> cancelled: cancel (rezerv bo'shatiladi)
    shipped --> delivered: deliver
    delivered --> [*]
    cancelled --> [*]
```

## Struktura

```
config/            settings (base/dev/prod/test), urls, celery
common/            umumiy model, ruxsatlar, validatorlar, mixinlar
apps/users/        foydalanuvchi va rollar, JWT
apps/customers/    mijozlar, kontaktlar, muloqotlar tarixi
apps/catalog/      kategoriya, rang, razmer qatori, model (artikul), variant (SKU)
apps/inventory/    omborlar, qoldiqlar, harakatlar jurnali (ledger)
apps/orders/       buyurtmalar, korobka bo'yicha kiritish, holatlar
tests/
```

Biznes-logika `services.py`'da, murakkab so'rovlar `selectors.py`'da turadi, view'larda esa faqat HTTP qismi bo'ladi.

## Rollar

| Rol | Mijozlar | Katalog | Ombor | Buyurtmalar | Foydalanuvchilar |
|---|---|---|---|---|---|
| `admin` | to'liq | to'liq | to'liq | to'liq | to'liq |
| `director` | to'liq | to'liq | to'liq | to'liq | ko'rish |
| `sales_manager` | faqat o'z mijozlari | ko'rish | ko'rish | o'z mijozlariniki: yaratish, tasdiqlash, bekor qilish | — |
| `warehouse` | — | ko'rish | to'liq | ko'rish, jo'natish, yetkazish | — |
| `accountant` | ko'rish | ko'rish | ko'rish | ko'rish | — |
| `production_head` | — | to'liq | ko'rish | — | — |
| `worker` | — | ko'rish | — | — | — |

## Asosiy endpointlar

| Metod | URL | Tavsif |
|---|---|---|
| POST | `/api/v1/auth/token/` | Login (access + refresh) |
| POST | `/api/v1/auth/token/refresh/` | Tokenni yangilash |
| GET | `/api/v1/users/me/` | Joriy foydalanuvchi |
| GET/POST | `/api/v1/customers/` | Mijozlar (`?search=`, `?region=`, `?tag=`, `?type=`) |
| DELETE | `/api/v1/customers/{id}/` | Nofaol qilish (bazadan o'chirilmaydi) |
| POST | `/api/v1/customers/{id}/restore/` | Qayta faollashtirish |
| GET/POST | `/api/v1/contacts/`, `/api/v1/interactions/` | Kontaktlar, muloqotlar (`?customer=`) |
| GET/POST | `/api/v1/size-runs/` | Razmer qatorlari: `{"40": 1, "41": 2, ...}` |
| GET/POST | `/api/v1/product-models/` | Modellar (artikullar) |
| POST | `/api/v1/product-models/{id}/generate-variants/` | Rang × razmer variantlarini yaratish |
| GET | `/api/v1/variants/?barcode=...` | Shtrix-kod bo'yicha qidirish |
| GET | `/api/v1/stock/` | Qoldiqlar (`?warehouse=`, `?available_lte=5` — kam qolganlar) |
| GET | `/api/v1/stock-movements/` | Harakatlar jurnali (faqat o'qiladi) |
| POST | `/api/v1/stock-movements/receive/` | Kirim |
| POST | `/api/v1/stock-movements/write-off/` | Hisobdan chiqarish (brak) |
| POST | `/api/v1/stock-movements/transfer/` | Omborlar orasida ko'chirish |
| POST | `/api/v1/stock-movements/adjust/` | Inventarizatsiya |
| GET/POST | `/api/v1/orders/` | Buyurtmalar (`?status=confirmed&status=shipped`, `?date_from=`) |
| POST | `/api/v1/orders/{id}/items/` | Qator qo'shish (variant + juft soni) |
| POST | `/api/v1/orders/{id}/boxes/` | Korobka bo'yicha qo'shish: model + rang + korobka soni |
| PATCH/DELETE | `/api/v1/orders/{id}/items/{item_id}/` | Qatorni o'zgartirish yoki o'chirish |
| POST | `/api/v1/orders/{id}/confirm/` · `ship/` · `deliver/` · `cancel/` | Holatni o'zgartirish |

## Muhim qarorlar

- **Soft delete:** mijoz, model va variantlar o'chirilmaydi, faqat `is_active=False` qilinadi, shunda buyurtma va to'lov tarixi saqlanib qoladi.
- **Audit:** `Customer` va `ProductModel` o'zgarishlari `django-simple-history` orqali yoziladi (kim, qachon, nima o'zgardi).
- **Shtrix-kod:** variantga shtrix-kod berilmasa, id asosida `200…` prefiksli ichki EAN-13 yaratiladi.
- **Pul:** `DecimalField` bilan saqlanadi, valyutasi alohida maydonda (UZS/USD).
- **Ombor — ledger:** qoldiq hech qachon to'g'ridan-to'g'ri o'zgartirilmaydi. Har bir o'zgarish o'zgarmas `StockMovement` yozuvi bo'ladi, `StockBalance` esa joriy qoldiqni shu tranzaksiya ichida saqlaydi. Tarixni istalgan vaqt tekshirsa bo'ladi.
- **Konkurensiya:** rezerv va jo'natishda qoldiq qatorlari `select_for_update` bilan bloklanadi va har doim bir xil tartibda (ombor id → variant id) olinadi, shuning uchun deadlock bo'lmaydi. [test_order_concurrency.py](tests/test_order_concurrency.py) ikki menejer bir vaqtda oxirgi juftlarni olishga urinishini tekshiradi: faqat bittasi muvaffaqiyatli bo'ladi.
- **Rezerv "hammasi yoki hech narsa":** buyurtmadagi bitta razmer yetmasa ham hech narsa rezerv qilinmaydi, javobda esa nima qancha yetmasligi qaytariladi.
- **Korobka:** `POST /orders/{id}/boxes/` razmer qatorini juftlarga yoyadi. Masalan, `{"40": 1, "41": 2}` qatoridan 3 korobka 40-razmerdan 3 juft, 41-razmerdan 6 juft beradi.
- **Biznes xatolari:** services qatlami DRF'ga bog'liq emas va `BusinessError` ko'taradi. Uni umumiy exception handler 400 javobga aylantiradi.
- **Chegirma:** savdo menejeri ko'pi bilan 10% chegirma bera oladi, undan kattasini faqat rahbariyat beradi.

## Keyingi bosqichlar

1. `finance`: to'lovlar, mijoz balansi, akt-sverka, tasdiqlashda kredit limitini tekshirish
2. `production`: BOM, xomashyo ombori, partiyalar, bosqichlar, donabay ish haqi
3. Celery vazifalari: Markaziy bank kursi, qarz eslatmalari, Excel import
4. Telegram bot (aiogram), hisobotlar, PDF/Excel
