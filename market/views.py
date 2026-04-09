from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Order, Product
from .serializers import CategorySerializer, OrderSerializer, ProductSerializer


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


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.select_related("product", "product__category").filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
