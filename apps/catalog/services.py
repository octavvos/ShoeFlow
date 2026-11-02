from collections.abc import Iterable

from django.db import transaction

from .models import Color, ProductModel, Variant


@transaction.atomic
def generate_variants(
    product_model: ProductModel, colors: Iterable[Color], sizes: Iterable[int]
) -> list[Variant]:
    """
    Model uchun berilgan ranglar va razmerlarning barcha kombinatsiyalarini yaratadi.
    Mavjud variantlarga tegilmaydi. Faqat yangi yaratilganlarini qaytaradi.
    """
    sizes = sorted(set(sizes))
    existing = set(product_model.variants.values_list("color_id", "size"))

    created = []
    for color in colors:
        for size in sizes:
            if (color.pk, size) in existing:
                continue
            created.append(
                Variant.objects.create(product_model=product_model, color=color, size=size)
            )
    return created
