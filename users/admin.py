from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from .models import OTP, TelegramOTP, UserDevice
from .services.push_notifications import send_bulk_fcm_notifications

User = get_user_model()


class PushNotificationAdminForm(forms.Form):
    RECIPIENT_SELECTED = "selected"
    RECIPIENT_ALL = "all"
    RECIPIENT_PHONES = "phones"

    recipient_mode = forms.ChoiceField(
        label="Recipients",
        choices=(
            (RECIPIENT_SELECTED, "Selected users"),
            (RECIPIENT_ALL, "All users"),
            (RECIPIENT_PHONES, "By phone list"),
        ),
        initial=RECIPIENT_SELECTED,
    )
    phones = forms.CharField(
        label="Phone list",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "+998901112233\n+998933334455",
            }
        ),
        help_text="One phone per line. Used only for 'By phone list' mode.",
    )
    title = forms.CharField(
        label="Notification title",
        max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Masalan: To'lov eslatmasi"}),
    )
    message = forms.CharField(
        label="Notification message",
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Xabar matnini kiriting..."}),
    )
    selected_user_ids = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("recipient_mode")
        phones = cleaned.get("phones", "")
        selected_ids = cleaned.get("selected_user_ids", "")

        if mode == self.RECIPIENT_SELECTED and not selected_ids.strip():
            raise forms.ValidationError("No selected users found. Select users first or use another mode.")

        if mode == self.RECIPIENT_PHONES:
            phone_lines = [line.strip() for line in phones.splitlines() if line.strip()]
            if not phone_lines:
                raise forms.ValidationError("Please provide at least one phone number.")
            cleaned["phone_list"] = phone_lines

        return cleaned


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["phone", "first_name", "last_name", "is_premium", "is_active"]
    search_fields = ["phone", "first_name", "last_name"]
    change_list_template = "admin/users/user/change_list.html"
    actions = ["open_push_notification_window"]

    @admin.action(description="Open push notification window")
    def open_push_notification_window(self, request, queryset):
        ids = ",".join(str(pk) for pk in queryset.values_list("id", flat=True))
        url = reverse("admin:users_user_send_push")
        if ids:
            url = f"{url}?ids={ids}"
        return HttpResponseRedirect(url)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "send-push/",
                self.admin_site.admin_view(self.send_push_view),
                name="users_user_send_push",
            ),
        ]
        return custom_urls + urls

    def send_push_view(self, request):
        selected_ids = (request.GET.get("ids") or request.POST.get("selected_user_ids") or "").strip()

        if request.method == "POST":
            form = PushNotificationAdminForm(request.POST)
            if form.is_valid():
                recipient_mode = form.cleaned_data["recipient_mode"]
                title = form.cleaned_data["title"].strip()
                body = form.cleaned_data["message"].strip()

                user_qs = User.objects.none()
                if recipient_mode == PushNotificationAdminForm.RECIPIENT_SELECTED:
                    id_list = [int(x) for x in form.cleaned_data["selected_user_ids"].split(",") if x.strip().isdigit()]
                    user_qs = User.objects.filter(id__in=id_list)
                elif recipient_mode == PushNotificationAdminForm.RECIPIENT_ALL:
                    user_qs = User.objects.all()
                elif recipient_mode == PushNotificationAdminForm.RECIPIENT_PHONES:
                    user_qs = User.objects.filter(phone__in=form.cleaned_data["phone_list"])

                tokens = list(
                    UserDevice.objects.filter(user__in=user_qs, notifications_enabled=True)
                    .exclude(fcm_token="")
                    .values_list("fcm_token", flat=True)
                    .distinct()
                )

                if not tokens:
                    self.message_user(
                        request,
                        "No active devices with FCM tokens found for selected recipients.",
                        level=messages.WARNING,
                    )
                else:
                    sent, failed = send_bulk_fcm_notifications(tokens=tokens, title=title, body=body)
                    if failed:
                        self.message_user(
                            request,
                            f"Push sent to {sent} devices, failed for {failed} devices.",
                            level=messages.WARNING,
                        )
                    else:
                        self.message_user(
                            request,
                            f"Push sent successfully to {sent} devices.",
                            level=messages.SUCCESS,
                        )

                return HttpResponseRedirect(reverse("admin:users_user_changelist"))
        else:
            form = PushNotificationAdminForm(initial={"selected_user_ids": selected_ids})

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Send Push Notification",
            "form": form,
            "selected_count": len([x for x in selected_ids.split(",") if x.strip()]),
            "selected_user_ids": selected_ids,
        }
        return render(request, "admin/users/send_push_notification.html", context)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "attempts", "is_used", "created_at", "expires_at")
    search_fields = ("phone", "code")
    list_filter = ("is_used",)


@admin.register(TelegramOTP)
class TelegramOTPAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_user_id",
        "code",
        "attempts",
        "is_used",
        "created_at",
        "expires_at",
    )
    search_fields = ("telegram_user_id", "code")
    list_filter = ("is_used",)


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "platform",
        "device_id",
        "notifications_enabled",
        "app_version",
        "updated_at",
    )
    search_fields = ("device_id", "fcm_token", "user__phone")
    list_filter = ("platform", "notifications_enabled")
    readonly_fields = ("created_at", "updated_at")
