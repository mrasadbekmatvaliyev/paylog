from decimal import Decimal, InvalidOperation

from django.db.models import Q


def parse_bool_param(raw_value, field_name):
    if raw_value is None:
        return None

    normalized = str(raw_value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError({field_name: f"{field_name} must be true/false, 1/0, or yes/no."})


def parse_decimal_param(raw_value, field_name):
    if raw_value in (None, ""):
        return None

    try:
        return Decimal(str(raw_value).strip())
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError({field_name: f"{field_name} must be a valid number."})


def filter_products(
    queryset,
    *,
    q=None,
    category_id=None,
    is_available=None,
    min_price=None,
    max_price=None,
):
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    parsed_is_available = parse_bool_param(is_available, "is_available")
    if parsed_is_available is not None:
        queryset = queryset.filter(is_available=parsed_is_available)

    parsed_min_price = parse_decimal_param(min_price, "min_price")
    if parsed_min_price is not None:
        queryset = queryset.filter(price__gte=parsed_min_price)

    parsed_max_price = parse_decimal_param(max_price, "max_price")
    if parsed_max_price is not None:
        queryset = queryset.filter(price__lte=parsed_max_price)

    return queryset.distinct()
