from django.db.models import Q
from .models import Notification


def notifications_count(request):
    if hasattr(request, "user") and request.user.is_authenticated:
        count = Notification.objects.filter(Q(user=request.user) | Q(user__isnull=True), read=False).count()
    else:
        count = Notification.objects.filter(user__isnull=True, read=False).count()
    return {
        "notifications_count": count
    }
