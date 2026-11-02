import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Category, Color, ProductModel, SizeRun, Variant
from apps.catalog.services import generate_variants
from apps.customers.models import Customer, Interaction
from apps.inventory import services as inventory
from apps.inventory.models import Warehouse
from apps.inventory.services import StockLine
from apps.orders import services as orders
from apps.orders.models import Order
from apps.users.models import Role, User
from common.choices import Currency, Region

DEMO_PASSWORD = "Demo-12345"

USERS = [
    ("direktor", "Bobur", "Karimov", Role.DIRECTOR),
    ("menejer1", "Dilshod", "Rahimov", Role.SALES_MANAGER),
    ("menejer2", "Nilufar", "Saidova", Role.SALES_MANAGER),
    ("omborchi", "Jasur", "Tursunov", Role.WAREHOUSE),
    ("hisobchi", "Madina", "Yusupova", Role.ACCOUNTANT),
    ("sex", "Rustam", "Aliyev", Role.PRODUCTION_HEAD),
    ("usta1", "Akmal", "Nazarov", Role.WORKER),
]

COLORS = [
    ("Qora", "#000000"),
    ("Jigarrang", "#6B3E26"),
    ("Oq", "#FFFFFF"),
    ("Kulrang", "#808080"),
    ("To'q ko'k", "#1F2A44"),
]

SIZE_RUNS = {
    "Erkaklar 40-45": {"40": 1, "41": 1, "42": 2, "43": 2, "44": 1, "45": 1},
    "Ayollar 36-40": {"36": 1, "37": 2, "38": 2, "39": 2, "40": 1},
    "Bolalar 28-33": {"28": 1, "29": 1, "30": 1, "31": 1, "32": 1, "33": 1},
}

# artikul, nomi, kategoriya, jins, mavsum, razmer qatori, ulgurji narx (USD), ranglar
PRODUCT_MODELS = [
    (
        "T-101",
        "Klassik tufli",
        "Tufli",
        "men",
        "all",
        "Erkaklar 40-45",
        "28",
        ["Qora", "Jigarrang"],
    ),
    ("T-102", "Ofis tufli", "Tufli", "women", "all", "Ayollar 36-40", "24", ["Qora", "Oq"]),
    (
        "K-201",
        "Yengil krossovka",
        "Krossovka",
        "men",
        "summer",
        "Erkaklar 40-45",
        "19",
        ["Oq", "Kulrang"],
    ),
    (
        "K-202",
        "Sport krossovka",
        "Krossovka",
        "women",
        "demi",
        "Ayollar 36-40",
        "21",
        ["Oq", "To'q ko'k"],
    ),
    (
        "E-301",
        "Qishki etik",
        "Etik",
        "men",
        "winter",
        "Erkaklar 40-45",
        "42",
        ["Qora", "Jigarrang"],
    ),
    ("E-302", "Teri etik", "Etik", "women", "winter", "Ayollar 36-40", "39", ["Qora"]),
    (
        "B-401",
        "Bolalar botinkasi",
        "Botinka",
        "kids",
        "demi",
        "Bolalar 28-33",
        "14",
        ["Jigarrang", "To'q ko'k"],
    ),
    (
        "S-501",
        "Yozgi shippak",
        "Shippak",
        "unisex",
        "summer",
        "Erkaklar 40-45",
        "7",
        ["Qora", "Kulrang"],
    ),
]

CUSTOMERS = [
    ("Ipak Yo'li Savdo MChJ", Customer.Type.DEALER, Region.TASHKENT_CITY, ["vip"]),
    ("Chorsu bozori, 14-do'kon", Customer.Type.WHOLESALE, Region.TASHKENT_CITY, []),
    ("Siyob Poyabzal", Customer.Type.WHOLESALE, Region.SAMARKAND, ["doimiy"]),
    ("Registon Savdo", Customer.Type.DEALER, Region.SAMARKAND, ["vip"]),
    ("Buxoro Oyoq Kiyim", Customer.Type.WHOLESALE, Region.BUKHARA, []),
    ("Farg'ona Trade", Customer.Type.DEALER, Region.FERGANA, ["doimiy"]),
    ("Andijon Markaz", Customer.Type.WHOLESALE, Region.ANDIJAN, []),
    ("Namangan Bozor", Customer.Type.WHOLESALE, Region.NAMANGAN, ["yangi"]),
    ("Qarshi Poyabzal", Customer.Type.RETAIL, Region.KASHKADARYA, []),
    ("Uzum Market", Customer.Type.MARKETPLACE, Region.TASHKENT_CITY, ["marketpleys"]),
    ("Xorazm Savdo Uyi", Customer.Type.WHOLESALE, Region.KHOREZM, ["yangi"]),
    ("Nukus Oyoq Kiyim", Customer.Type.RETAIL, Region.KARAKALPAKSTAN, []),
]

INTERACTION_NOTES = [
    (Interaction.Type.CALL, "Yangi qishki kolleksiya haqida gaplashdik, katalog yuborildi."),
    (Interaction.Type.MEETING, "Do'konga bordik, vitrinadagi modellarni ko'rdik."),
    (Interaction.Type.MESSAGE, "Telegramda narxlar ro'yxati yuborildi."),
    (Interaction.Type.NOTE, "To'lovni oy oxirigacha qilishga va'da berdi."),
]

WAREHOUSES = [
    ("Asosiy ombor", "Toshkent sh., Sergeli tumani"),
    ("Samarqand filiali", "Samarqand sh., Siyob bozori yonida"),
]

# Buyurtmalar qaysi holatgacha olib boriladi
ORDER_STATUSES = [
    Order.Status.DELIVERED,
    Order.Status.DELIVERED,
    Order.Status.DELIVERED,
    Order.Status.SHIPPED,
    Order.Status.SHIPPED,
    Order.Status.CONFIRMED,
    Order.Status.CONFIRMED,
    Order.Status.DRAFT,
    Order.Status.DRAFT,
    Order.Status.CANCELLED,
]


class Command(BaseCommand):
    help = "Tizimni sinab ko'rish uchun demo ma'lumotlar yaratadi."

    def handle(self, *args, **options):
        if User.objects.filter(username="direktor").exists():
            self.stdout.write(self.style.WARNING("Demo ma'lumotlar allaqachon mavjud."))
            return

        self.rnd = random.Random(42)
        with transaction.atomic():
            users = self.create_users()
            self.create_catalog()
            self.create_customers(users)
            warehouses = self.create_stock(users)
            self.create_orders(users, warehouses[0])

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar yaratildi."))
        self.stdout.write(f"Foydalanuvchilar: {', '.join(u[0] for u in USERS)}")
        self.stdout.write(f"Parol (hammasi uchun): {DEMO_PASSWORD}")

    def create_users(self) -> dict[str, User]:
        return {
            username: User.objects.create_user(
                username=username,
                password=DEMO_PASSWORD,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )
            for username, first_name, last_name, role in USERS
        }

    def create_catalog(self):
        colors = {
            name: Color.objects.get_or_create(name=name, defaults={"hex_code": hex_code})[0]
            for name, hex_code in COLORS
        }
        size_runs = {
            name: SizeRun.objects.get_or_create(name=name, defaults={"sizes": sizes})[0]
            for name, sizes in SIZE_RUNS.items()
        }
        for article, name, category, gender, season, run, price, color_names in PRODUCT_MODELS:
            wholesale = Decimal(price)
            model = ProductModel.objects.create(
                article=article,
                name=name,
                category=Category.objects.get_or_create(name=category)[0],
                gender=gender,
                season=season,
                default_size_run=size_runs[run],
                currency=Currency.USD,
                wholesale_price=wholesale,
                dealer_price=(wholesale * Decimal("0.92")).quantize(Decimal("0.01")),
                retail_price=(wholesale * Decimal("1.4")).quantize(Decimal("0.01")),
            )
            generate_variants(model, [colors[c] for c in color_names], size_runs[run].size_list)

    def create_customers(self, users: dict[str, User]):
        managers = [users["menejer1"], users["menejer2"]]
        for i, (name, type_, region, tags) in enumerate(CUSTOMERS):
            manager = managers[i % len(managers)]
            customer = Customer.objects.create(
                name=name,
                type=type_,
                region=region,
                phone=f"+99890{1000000 + i * 7919:07d}",
                currency=Currency.USD,
                credit_limit=Decimal(self.rnd.choice([0, 1000, 3000, 5000, 10000])),
                manager=manager,
                tags=tags,
            )
            customer.contacts.create(
                full_name=f"{name.split()[0]} rahbari",
                position="Direktor",
                phone=f"+99891{2000000 + i * 6007:07d}",
            )
            for days_ago in self.rnd.sample(range(1, 60), k=self.rnd.randint(1, 3)):
                type_, body = self.rnd.choice(INTERACTION_NOTES)
                Interaction.objects.create(
                    customer=customer,
                    author=manager,
                    type=type_,
                    body=body,
                    occurred_at=timezone.now() - timedelta(days=days_ago),
                )

    def create_stock(self, users: dict[str, User]) -> list[Warehouse]:
        warehouses = [
            Warehouse.objects.create(name=name, address=address) for name, address in WAREHOUSES
        ]
        main, branch = warehouses
        variants = list(Variant.objects.order_by("id"))
        inventory.receive(
            main,
            [StockLine(v.id, self.rnd.randint(40, 80)) for v in variants],
            user=users["omborchi"],
            reference="Boshlang'ich qoldiq",
        )
        inventory.transfer(
            main,
            branch,
            [StockLine(v.id, 10) for v in self.rnd.sample(variants, k=len(variants) // 3)],
            user=users["omborchi"],
            comment="Filialni to'ldirish",
        )
        return warehouses

    def create_orders(self, users: dict[str, User], warehouse: Warehouse):
        customers = list(Customer.objects.select_related("manager").order_by("id"))
        models = list(ProductModel.objects.prefetch_related("variants").order_by("id"))

        for target in ORDER_STATUSES:
            customer = self.rnd.choice(customers)
            manager = customer.manager
            order = orders.create_order(
                customer=customer,
                warehouse=warehouse,
                user=manager,
                discount_percent=Decimal(self.rnd.choice([0, 0, 3, 5])),
            )
            for product_model in self.rnd.sample(models, k=self.rnd.randint(1, 3)):
                color = self.rnd.choice(product_model.variants.all()).color
                orders.add_boxes(
                    order,
                    product_model,
                    color,
                    product_model.default_size_run,
                    self.rnd.randint(1, 3),
                )

            if target == Order.Status.DRAFT:
                continue
            orders.confirm_order(order, user=manager)
            if target == Order.Status.CANCELLED:
                orders.cancel_order(order, user=manager)
                continue
            if target in (Order.Status.SHIPPED, Order.Status.DELIVERED):
                orders.ship_order(order, user=users["omborchi"])
            if target == Order.Status.DELIVERED:
                orders.deliver_order(order, user=users["omborchi"])
