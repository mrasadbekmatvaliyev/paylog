import re
from decimal import Decimal

from market.models import Product
from market.services import filter_products

BUDGET_UNIT_PATTERN = re.compile(
    r"(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>k|ming|mln|million|m)\b",
    re.IGNORECASE,
)
BUDGET_CURRENCY_PATTERN = re.compile(
    r"(?P<amount>[\d\s.,]+)\s*(so'm|som|soum|uzs|sum)\b",
    re.IGNORECASE,
)
STOP_WORDS = {
    "menga",
    "kerak",
    "qidir",
    "qidirib",
    "ber",
    "bormi",
    "haqida",
    "zormi",
    "please",
    "iltimos",
}


def _normalize(text):
    return (
        text.lower()
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("`", "'")
        .replace("\u02bb", "'")
    )


def _extract_budget(raw_text):
    text = _normalize(raw_text)

    unit_match = BUDGET_UNIT_PATTERN.search(text)
    if unit_match:
        amount = Decimal(unit_match.group("amount").replace(",", "."))
        unit = unit_match.group("unit").lower()
        if unit in {"k", "ming"}:
            return amount * Decimal("1000")
        return amount * Decimal("1000000")

    currency_match = BUDGET_CURRENCY_PATTERN.search(text)
    if currency_match:
        digits = re.sub(r"[^\d]", "", currency_match.group("amount"))
        if digits:
            return Decimal(digits)

    return None


def _extract_query(raw_text):
    text = _normalize(raw_text)
    text = BUDGET_UNIT_PATTERN.sub(" ", text)
    text = BUDGET_CURRENCY_PATTERN.sub(" ", text)
    text = re.sub(r"[^\w\s]", " ", text)

    parts = [part for part in text.split() if part and part not in STOP_WORDS and not part.isdigit()]
    if not parts:
        return raw_text.strip()

    return " ".join(parts)


def find_best_product_from_message(raw_text):
    query_text = _extract_query(raw_text)
    max_price = _extract_budget(raw_text)

    base_queryset = Product.objects.select_related("category").all()

    filtered = filter_products(
        base_queryset,
        q=query_text,
        is_available="true",
        max_price=str(max_price) if max_price is not None else None,
    )

    best = filtered.order_by("-price", "-id").first()
    if best is not None:
        return best

    fallback = filter_products(
        base_queryset,
        q=query_text,
        is_available="true",
    )
    return fallback.order_by("price", "id").first()


def serialize_product(product):
    if product is None:
        return None

    return {
        "id": product.id,
        "name": product.name,
        "price": str(product.price),
        "description": product.description,
        "image_url": product.image_url,
    }


def format_product_reply(product):
    if product is None:
        return "Mos product topilmadi."

    description = (product.description or "").strip() or "Tavsif yo'q"
    image_url = product.image_url or "Rasm mavjud emas"

    return (
        f"Nomi: {product.name}\n"
        f"Narxi: {product.price} so'm\n"
        f"Tavsif: {description}\n"
        f"Rasm: {image_url}"
    )
