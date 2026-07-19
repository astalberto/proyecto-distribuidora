def notifications(request):
    """Unread notification count, available in every template without each
    view having to pass it explicitly (US-16: "visible on every page load").
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        'unread_notification_count': user.notifications.filter(is_read=False).count(),
    }
