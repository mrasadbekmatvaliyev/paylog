from django.urls import path

from .views import TelegramOTPSendView, TelegramOTPVerifyView

urlpatterns = [
    path("telegram/otp/send", TelegramOTPSendView.as_view(), name="telegram-otp-send"),
    path("telegram/otp/verify", TelegramOTPVerifyView.as_view(), name="telegram-otp-verify"),
]
