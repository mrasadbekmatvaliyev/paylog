from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatViewSet, DebtorViewSet

router = DefaultRouter()
router.register(r"chats", ChatViewSet, basename="chat")
router.register(r"debtors", DebtorViewSet, basename="debtor")

urlpatterns = [
    path("", include(router.urls)),
]
