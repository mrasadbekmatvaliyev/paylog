from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AIChatView, DeviceRegisterView, OTPSendView, OTPResendView, OTPVerifyView, ProfileDeleteOTPSendView, ProfileSoftDeleteView, ProfileView

urlpatterns = [
    path("otp/send", OTPSendView.as_view(), name="otp-send"),
    path("otp/resend", OTPResendView.as_view(), name="otp-resend"),
    path("otp/verify", OTPVerifyView.as_view(), name="otp-verify"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("me", ProfileView.as_view(), name="profile"),
    path("me/delete/otp/send", ProfileDeleteOTPSendView.as_view(), name="profile-delete-otp-send"),
    path("me/delete", ProfileSoftDeleteView.as_view(), name="profile-soft-delete"),
    path("ai/chat/", AIChatView.as_view(), name="ai-chat"),
    path("devices/register/", DeviceRegisterView.as_view(), name="device-register"),
]





