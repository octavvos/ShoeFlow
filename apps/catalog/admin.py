from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Category, Color, ProductModel, SizeRun, Variant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name", "hex_code")
    search_fields = ("name",)


@admin.register(SizeRun)
class SizeRunAdmin(admin.ModelAdmin):
    list_display = ("name", "sizes", "total_pairs")


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    readonly_fields = ("barcode",)


@admin.register(ProductModel)
class ProductModelAdmin(SimpleHistoryAdmin):
    list_display = (
        "article",
        "name",
        "category",
        "gender",
        "season",
        "wholesale_price",
        "is_active",
    )
    list_filter = ("category", "gender", "season", "is_active")
    search_fields = ("article", "name")
    inlines = (VariantInline,)


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("product_model", "color", "size", "barcode", "is_active")
    list_filter = ("color", "size", "is_active")
    search_fields = ("product_model__article", "barcode")
