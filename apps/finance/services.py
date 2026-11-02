"""
Mijoz hisobini o'zgartiradigan yagona joy.

Qarz faqat LedgerEntry yozuvlaridan hisoblanadi: jo'natish qarzni oshiradi, to'lov kamaytiradi.
Kredit limitini tekshirishda mijoz qatori bloklanadi — bir vaqtda tasdiqlangan ikki buyurtma
limitni ikki marta "sarflay" olmaydi.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.users.models import User
from common.choices import Currency
from common.exceptions import BusinessError

from .models import CurrencyRate, LedgerEntry, Payment

CENT = Decimal("0.01")
CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/{currency}/{date}/"


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _sum(queryset, field_name: str) -> Decimal:
    return queryset.aggregate(total=Sum(field_name))["total"] or Decimal(0)


# --- Valyuta kurslari ---


def latest_rate(currency: str, on_date: date) -> Decimal:
    rate = (
        CurrencyRate.objects.filter(currency=currency, date__lte=on_date)
        .order_by("-date")
        .values_list("rate", flat=True)
        .first()
    )
    if rate is None:
        raise BusinessError(
            f"{on_date} sanasi uchun {currency} kursi topilmadi. Kursni qo'lda kiriting.",
            code="rate_missing",
        )
    return rate


def convert(amount: Decimal, from_currency: str, to_currency: str, rate: Decimal | None) -> Decimal:
    """So'm va valyuta orasida konvertatsiya. rate — 1 birlik valyuta necha so'm."""
    if from_currency == to_currency:
        return _money(amount)
    if not rate or rate <= 0:
        raise BusinessError("Konvertatsiya uchun kurs musbat bo'lishi kerak.")
    if from_currency == Currency.UZS:
        return _money(amount / rate)
    if to_currency == Currency.UZS:
        return _money(amount * rate)
    raise BusinessError("Faqat so'm va valyuta orasida konvertatsiya qilinadi.")


def fetch_cbu_rates(on_date: date | None = None) -> list[CurrencyRate]:
    """
    Markaziy bank (cbu.uz) kurslarini oladi. Shu sanaga qo'lda kiritilgan kurs bo'lsa,
    unga tegilmaydi — firma o'z kursi bilan ishlashi mumkin.
    """
    on_date = on_date or timezone.localdate()
    saved = []
    for currency in Currency.values:
        if currency == Currency.UZS:
            continue
        response = requests.get(
            CBU_URL.format(currency=currency, date=on_date.isoformat()), timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            continue
        item = data[0]
        rate_date = datetime.strptime(item["Date"], "%d.%m.%Y").date()
        rate = Decimal(item["Rate"]) / Decimal(item.get("Nominal") or 1)

        existing = CurrencyRate.objects.filter(currency=currency, date=rate_date).first()
        if existing and existing.source == CurrencyRate.Source.MANUAL:
            continue
        obj, _ = CurrencyRate.objects.update_or_create(
            currency=currency,
            date=rate_date,
            defaults={"rate": rate, "source": CurrencyRate.Source.CBU},
        )
        saved.append(obj)
    return saved


# --- Balans va kredit limiti ---


def customer_balance(customer: Customer) -> Decimal:
    """Mijoz qarzi: musbat — mijoz qarzdor, manfiy — oldindan to'lagan."""
    return _sum(customer.ledger_entries.all(), "amount")


def open_orders_amount(customer: Customer, exclude: Order | None = None) -> Decimal:
    """Tasdiqlangan, lekin hali jo'natilmagan buyurtmalar — yaqin kunlardagi qarz."""
    qs = Order.objects.filter(customer=customer, status=Order.Status.CONFIRMED)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return _sum(qs, "total_amount")


@transaction.atomic
def check_credit_limit(order: Order, *, user: User) -> None:
    """Rahbariyat limitdan oshirib tasdiqlay oladi, qolganlar — yo'q."""
    customer = Customer.objects.select_for_update().get(pk=order.customer_id)
    if user.is_management:
        return
    exposure = customer_balance(customer) + open_orders_amount(customer, exclude=order)
    exposure += order.total_amount
    if exposure > customer.credit_limit:
        raise BusinessError(
            f"Kredit limiti oshib ketadi: limit {customer.credit_limit} {customer.currency}, "
            f"tasdiqlangandan keyingi qarz {exposure} {customer.currency}. "
            "Oldindan to'lov oling yoki rahbariyatga murojaat qiling.",
            code="credit_limit",
            credit_limit=str(customer.credit_limit),
            exposure=str(exposure),
        )


# --- Hisob yozuvlari ---


def _entry(customer: Customer, type_: str, amount: Decimal, user: User | None, **kwargs):
    return LedgerEntry.objects.create(
        customer=customer,
        type=type_,
        amount=_money(amount),
        currency=customer.currency,
        created_by=user,
        **kwargs,
    )


@transaction.atomic
def record_shipment(order: Order, *, user: User | None) -> LedgerEntry:
    customer = order.customer
    if order.currency != customer.currency:
        raise BusinessError("Buyurtma valyutasi mijoz hisobi valyutasiga mos emas.")
    return _entry(
        customer,
        LedgerEntry.Type.SHIPMENT,
        order.total_amount,
        user,
        order=order,
        description=f"{order.number} buyurtma jo'natildi",
    )


@transaction.atomic
def register_payment(
    *,
    customer: Customer,
    amount: Decimal,
    currency: str,
    method: str,
    user: User | None,
    paid_at: date | None = None,
    order: Order | None = None,
    rate: Decimal | None = None,
    comment: str = "",
) -> Payment:
    paid_at = paid_at or timezone.localdate()
    if order is not None and order.customer_id != customer.pk:
        raise BusinessError("Buyurtma boshqa mijozga tegishli.")

    if currency == customer.currency:
        rate = None
    else:
        foreign = currency if currency != Currency.UZS else customer.currency
        rate = rate or latest_rate(foreign, paid_at)
    settlement = convert(amount, currency, customer.currency, rate)

    payment = Payment.objects.create(
        customer=customer,
        order=order,
        amount=amount,
        currency=currency,
        method=method,
        rate=rate,
        settlement_amount=settlement,
        paid_at=paid_at,
        comment=comment,
        created_by=user,
    )
    _entry(
        customer,
        LedgerEntry.Type.PAYMENT,
        -settlement,
        user,
        payment=payment,
        order=order,
        date=paid_at,
        description=f"To'lov ({payment.get_method_display()})",
    )
    return payment


@transaction.atomic
def cancel_payment(payment: Payment, *, user: User, reason: str) -> Payment:
    """To'lov o'chirilmaydi: qarama-qarshi yozuv qo'shiladi, tarix saqlanib qoladi."""
    payment = Payment.objects.select_for_update().select_related("customer").get(pk=payment.pk)
    if payment.is_cancelled:
        raise BusinessError("To'lov allaqachon bekor qilingan.")
    payment.is_cancelled = True
    payment.cancelled_at = timezone.now()
    payment.cancelled_by = user
    payment.cancel_reason = reason
    payment.save(update_fields=["is_cancelled", "cancelled_at", "cancelled_by", "cancel_reason"])
    _entry(
        payment.customer,
        LedgerEntry.Type.PAYMENT_CANCEL,
        payment.settlement_amount,
        user,
        payment=payment,
        order=payment.order,
        description=f"To'lov bekor qilindi: {reason}",
    )
    return payment


@transaction.atomic
def add_adjustment(
    customer: Customer,
    amount: Decimal,
    *,
    user: User,
    description: str,
    entry_date: date | None = None,
    opening: bool = False,
) -> LedgerEntry:
    """Qo'lda tuzatish yoki boshlang'ich qoldiq (eski tizimdan o'tkazilgan qarzlar)."""
    if amount == 0:
        raise BusinessError("Summa noldan farq qilishi kerak.")
    type_ = LedgerEntry.Type.OPENING if opening else LedgerEntry.Type.ADJUSTMENT
    return _entry(
        customer,
        type_,
        amount,
        user,
        description=description,
        date=entry_date or timezone.localdate(),
    )


# --- Akt-sverka ---


@dataclass
class ReconciliationRow:
    date: date
    type: str
    type_display: str
    reference: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


@dataclass
class Reconciliation:
    customer: Customer
    date_from: date
    date_to: date
    opening_balance: Decimal
    rows: list[ReconciliationRow] = field(default_factory=list)

    @property
    def currency(self) -> str:
        return self.customer.currency

    @property
    def debit_total(self) -> Decimal:
        return sum((r.debit for r in self.rows), Decimal(0))

    @property
    def credit_total(self) -> Decimal:
        return sum((r.credit for r in self.rows), Decimal(0))

    @property
    def closing_balance(self) -> Decimal:
        return self.opening_balance + self.debit_total - self.credit_total


def _reference(entry: LedgerEntry) -> str:
    if entry.payment_id:
        return f"T-{entry.payment_id:06d}"
    if entry.order_id:
        return entry.order.number
    return ""


def reconciliation(customer: Customer, date_from: date, date_to: date) -> Reconciliation:
    if date_from > date_to:
        raise BusinessError("Boshlanish sanasi tugash sanasidan keyin bo'lishi mumkin emas.")
    entries = customer.ledger_entries.select_related("order")
    result = Reconciliation(
        customer=customer,
        date_from=date_from,
        date_to=date_to,
        opening_balance=_sum(entries.filter(date__lt=date_from), "amount"),
    )
    balance = result.opening_balance
    for entry in entries.filter(date__range=(date_from, date_to)).order_by("date", "id"):
        balance += entry.amount
        result.rows.append(
            ReconciliationRow(
                date=entry.date,
                type=entry.type,
                type_display=entry.get_type_display(),
                reference=_reference(entry),
                description=entry.description,
                debit=entry.amount if entry.amount > 0 else Decimal(0),
                credit=-entry.amount if entry.amount < 0 else Decimal(0),
                balance=balance,
            )
        )
    return result
