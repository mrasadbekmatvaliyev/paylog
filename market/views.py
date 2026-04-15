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
        serializer.save(user=self.request.user)
