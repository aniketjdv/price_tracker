from .models import Notification


def notifications_count(request):
    return {
        "notifications_count": Notification.objects.filter(read=False).count()
    }
