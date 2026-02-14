from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission, IsAuthenticated as DRFIsAuthenticated


class IsAuthenticated(DRFIsAuthenticated):
    message = _("Authentication credentials were not provided.")


class IsOwner(BasePermission):
    message = _("You do not have permission to access this resource.")

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "user_id", None) == request.user.id
