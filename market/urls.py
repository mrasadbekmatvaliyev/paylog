from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, OrderViewSet, ProductViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="market-category")
router.register(r"products", ProductViewSet, basename="market-product")
router.register(r"orders", OrderViewSet, basename="market-order")

urlpatterns = [
    path("", include(router.urls)),
]
