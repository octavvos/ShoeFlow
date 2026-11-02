from decimal import Decimal

import factory

from apps.catalog.models import Category, Color, ProductModel, SizeRun, Variant
from apps.customers.models import Customer
from apps.inventory.models import Warehouse
from apps.users.models import Role, User
from common.choices import Region


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = Role.SALES_MANAGER
    password = factory.django.Password("Parol-12345")


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    name = factory.Sequence(lambda n: f"Do'kon {n}")
    phone = factory.Sequence(lambda n: f"+99890{n:07d}")
    region = Region.TASHKENT_CITY
    manager = factory.SubFactory(UserFactory)


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("name",)

    name = "Tufli"


class ColorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Color
        django_get_or_create = ("name",)

    name = factory.Iterator(["Qora", "Jigarrang", "Oq"])


class SizeRunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SizeRun

    name = factory.Sequence(lambda n: f"Erkaklar 39-44 #{n}")
    sizes = factory.LazyFunction(lambda: {str(s): 1 for s in range(39, 45)})


class ProductModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductModel

    article = factory.Sequence(lambda n: f"K-{n:04d}")
    name = "Klassik tufli"
    category = factory.SubFactory(CategoryFactory)
    gender = ProductModel.Gender.MEN
    wholesale_price = Decimal("25.00")
    dealer_price = Decimal("23.00")
    retail_price = Decimal("35.00")


class WarehouseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Warehouse
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Ombor {n}")


class VariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Variant

    product_model = factory.SubFactory(ProductModelFactory)
    color = factory.SubFactory(ColorFactory)
    size = factory.Sequence(lambda n: 36 + n % 10)
