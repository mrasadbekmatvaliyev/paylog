from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CurrencyViewSet, TransactionViewSet, DebtorTransactionViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"currencies", CurrencyViewSet, basename="currency")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(
    r"debtor-transactions",
    DebtorTransactionViewSet,
    basename="debtor-transaction",
)

urlpatterns = [
    path("", include(router.urls)),
]
