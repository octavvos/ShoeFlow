"""
Ombor qoldiqlarini o'zgartiradigan yagona joy.

Har bir funksiya tranzaksiya ichida ishlaydi va qoldiq qatorlarini `select_for_update` bilan
bloklaydi: bir vaqtda kelgan ikki so'rov bitta korobkani ikki marta sota olmaydi.
Qatorlar har doim (ombor id, variant id) tartibida bloklanadi — shunda deadlock bo'lmaydi.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from django.db import transaction

from apps.catalog.models import Variant
from apps.users.models import User
from common.exceptions import BusinessError

from .models import StockBalance, StockMovement, Warehouse


@dataclass(frozen=True)
class StockLine:
    variant_id: int
    quantity: int


class InsufficientStock(BusinessError):
    def __init__(self, shortages: list[dict]):
        super().__init__("Omborda yetarli mahsulot yo'q.", shortages=shortages)


def _merge(lines: Iterable[StockLine]) -> dict[int, int]:
    merged = Counter()
    for line in lines:
        if line.quantity <= 0:
            raise BusinessError("Soni musbat bo'lishi kerak.")
        merged[line.variant_id] += line.quantity
    return dict(sorted(merged.items()))


def _lock_balances(warehouse: Warehouse, variant_ids: Iterable[int]) -> dict[int, StockBalance]:
    """Qoldiq qatorlarini bloklaydi; hali qatori yo'q variantlar uchun 0 qoldiq bilan yaratadi."""
    variant_ids = sorted(set(variant_ids))
    StockBalance.objects.bulk_create(
        [StockBalance(warehouse=warehouse, variant_id=v) for v in variant_ids],
        ignore_conflicts=True,
    )
    balances = (
        StockBalance.objects.select_for_update(of=("self",))
        .select_related("variant__product_model", "variant__color")
        .filter(warehouse=warehouse, variant_id__in=variant_ids)
        .order_by("variant_id")
    )
    return {b.variant_id: b for b in balances}


def _shortage(balance: StockBalance, requested: int, available: int) -> dict:
    variant = balance.variant
    return {
        "variant": variant.id,
        "article": variant.product_model.article,
        "color": variant.color.name,
        "size": variant.size,
        "requested": requested,
        "available": available,
    }


def _save(balances: Iterable[StockBalance], movements: list[StockMovement]) -> list[StockMovement]:
    StockBalance.objects.bulk_update(balances, ["quantity", "reserved"])
    return StockMovement.objects.bulk_create(movements)


def _movement(balance, type_, delta, user, reference="", comment="") -> StockMovement:
    return StockMovement(
        warehouse_id=balance.warehouse_id,
        variant_id=balance.variant_id,
        type=type_,
        quantity=delta,
        balance_after=balance.quantity,
        reference=reference,
        comment=comment,
        created_by=user,
    )


@transaction.atomic
def receive(
    warehouse: Warehouse,
    lines: Iterable[StockLine],
    *,
    user: User | None,
    reference: str = "",
    comment: str = "",
) -> list[StockMovement]:
    """Omborga kirim (ishlab chiqarishdan, qaytarishdan va h.k.)."""
    merged = _merge(lines)
    balances = _lock_balances(warehouse, merged)
    movements = []
    for variant_id, qty in merged.items():
        balance = balances[variant_id]
        balance.quantity += qty
        movements.append(
            _movement(balance, StockMovement.Type.RECEIPT, qty, user, reference, comment)
        )
    return _save(balances.values(), movements)


@transaction.atomic
def write_off(
    warehouse: Warehouse, lines: Iterable[StockLine], *, user: User | None, comment: str
) -> list[StockMovement]:
    """Brak yoki yo'qotishni hisobdan chiqarish. Rezervdagi mahsulotga tegilmaydi."""
    merged = _merge(lines)
    balances = _lock_balances(warehouse, merged)
    shortages = [
        _shortage(balances[v], qty, balances[v].available)
        for v, qty in merged.items()
        if balances[v].available < qty
    ]
    if shortages:
        raise InsufficientStock(shortages)

    movements = []
    for variant_id, qty in merged.items():
        balance = balances[variant_id]
        balance.quantity -= qty
        movements.append(
            _movement(balance, StockMovement.Type.WRITE_OFF, -qty, user, comment=comment)
        )
    return _save(balances.values(), movements)


@transaction.atomic
def adjust(
    warehouse: Warehouse, variant: Variant, counted: int, *, user: User | None, comment: str = ""
) -> StockMovement | None:
    """Inventarizatsiya: qoldiqni sanab chiqilgan songa tenglashtiradi."""
    balance = _lock_balances(warehouse, [variant.id])[variant.id]
    if counted < balance.reserved:
        raise BusinessError(
            f"Sanalgan son ({counted}) rezervdagi sondan ({balance.reserved}) kam bo'lishi "
            "mumkin emas. Avval tegishli buyurtmalarni bekor qiling."
        )
    delta = counted - balance.quantity
    if delta == 0:
        return None
    balance.quantity = counted
    return _save(
        [balance], [_movement(balance, StockMovement.Type.ADJUSTMENT, delta, user, comment=comment)]
    )[0]


@transaction.atomic
def transfer(
    source: Warehouse,
    target: Warehouse,
    lines: Iterable[StockLine],
    *,
    user: User | None,
    comment: str = "",
) -> list[StockMovement]:
    if source.pk == target.pk:
        raise BusinessError("Bir omborning o'ziga ko'chirib bo'lmaydi.")
    merged = _merge(lines)

    # Deadlock bo'lmasligi uchun omborlar ham id tartibida bloklanadi
    first, second = sorted([source, target], key=lambda w: w.pk)
    locked = {first.pk: _lock_balances(first, merged), second.pk: _lock_balances(second, merged)}
    src, dst = locked[source.pk], locked[target.pk]

    shortages = [
        _shortage(src[v], qty, src[v].available)
        for v, qty in merged.items()
        if src[v].available < qty
    ]
    if shortages:
        raise InsufficientStock(shortages)

    reference = f"{source.name} → {target.name}"
    movements = []
    for variant_id, qty in merged.items():
        src[variant_id].quantity -= qty
        dst[variant_id].quantity += qty
        movements += [
            _movement(
                src[variant_id], StockMovement.Type.TRANSFER_OUT, -qty, user, reference, comment
            ),
            _movement(
                dst[variant_id], StockMovement.Type.TRANSFER_IN, qty, user, reference, comment
            ),
        ]
    StockBalance.objects.bulk_update([*src.values(), *dst.values()], ["quantity", "reserved"])
    return StockMovement.objects.bulk_create(movements)


@transaction.atomic
def reserve(warehouse: Warehouse, lines: Iterable[StockLine]) -> None:
    """Buyurtma uchun rezerv. Yetmasa, hech narsa rezerv qilinmaydi (hammasi yoki hech narsa)."""
    merged = _merge(lines)
    balances = _lock_balances(warehouse, merged)
    shortages = [
        _shortage(balances[v], qty, balances[v].available)
        for v, qty in merged.items()
        if balances[v].available < qty
    ]
    if shortages:
        raise InsufficientStock(shortages)

    for variant_id, qty in merged.items():
        balances[variant_id].reserved += qty
    StockBalance.objects.bulk_update(balances.values(), ["reserved"])


@transaction.atomic
def release(warehouse: Warehouse, lines: Iterable[StockLine]) -> None:
    """Rezervni bekor qilish (buyurtma bekor qilinganda)."""
    merged = _merge(lines)
    balances = _lock_balances(warehouse, merged)
    for variant_id, qty in merged.items():
        balance = balances[variant_id]
        if balance.reserved < qty:
            raise BusinessError("Rezervdagi sondan ko'p miqdorni bo'shatib bo'lmaydi.")
        balance.reserved -= qty
    StockBalance.objects.bulk_update(balances.values(), ["reserved"])


@transaction.atomic
def ship(
    warehouse: Warehouse, lines: Iterable[StockLine], *, user: User | None, reference: str
) -> list[StockMovement]:
    """Rezervdagi mahsulotni jo'natish: qoldiq ham, rezerv ham kamayadi."""
    merged = _merge(lines)
    balances = _lock_balances(warehouse, merged)
    movements = []
    for variant_id, qty in merged.items():
        balance = balances[variant_id]
        if balance.reserved < qty:
            raise BusinessError("Jo'natiladigan mahsulot oldindan rezerv qilinmagan.")
        balance.reserved -= qty
        balance.quantity -= qty
        movements.append(
            _movement(balance, StockMovement.Type.SHIPMENT, -qty, user, reference=reference)
        )
    return _save(balances.values(), movements)
