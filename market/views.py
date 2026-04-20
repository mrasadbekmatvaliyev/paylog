from decimal import Decimal

from django.db import transaction
from finance.models import VirtualCard
from finance.services import ensure_virtual_card_for_user
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Category, Order, Product
from .serializers import CategorySerializer, OrderSerializer, ProductSerializer
from .services import filter_products


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["get"], url_path="products")
    def products(self, request, pk=None):
        category = self.get_object()
        queryset = Product.objects.select_related("category").filter(category=category)
        serializer = ProductSerializer(queryset, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"list", "retrieve", "search"}:
            return [permissions.AllowAny()]
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        try:
            queryset = filter_products(
                self.get_queryset(),
                q=request.query_params.get("q"),
                category_id=request.query_params.get("category_id"),
                is_available=request.query_params.get("is_available"),
                min_price=request.query_params.get("min_price"),
                max_price=request.query_params.get("max_price"),
            )
        except ValueError as exc:
            raise ValidationError(exc.args[0])

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.select_related(
            "product",
            "product__category",
        ).filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)
        payment_method = serializer.validated_data.get(
            "payment_method",
            Order.PaymentMethod.CASH,
        )

        if payment_method == Order.PaymentMethod.VIRTUAL_CARD:
            ensure_virtual_card_for_user(user)

        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            if not product.is_available:
                raise ValidationError({"product_id": "Product is not available."})
            if product.stock < quantity:
                raise ValidationError({"quantity": "Not enough product stock."})

            unit_price = (
                product.discount_price
                if product.discount_price is not None
                else product.price
            )
            total_price = unit_price * Decimal(quantity)

            if payment_method == Order.PaymentMethod.VIRTUAL_CARD:
                card = VirtualCard.objects.select_for_update().get(user=user)
                if card.balance < total_price:
                    raise ValidationError({"balance": "Insufficient virtual card balance."})

            serializer.save(user=user, product=product)

            product.stock -= quantity
            product_update_fields = ["stock"]
            if product.stock == 0:
                product.is_available = False
                product_update_fields.append("is_available")
            product.save(update_fields=product_update_fields)

            if payment_method == Order.PaymentMethod.VIRTUAL_CARD:
                card.balance -= total_price
                card.save(update_fields=["balance"])
