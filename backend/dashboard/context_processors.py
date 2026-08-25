def notifications(request):
    """
    Makes unread DashboardNotification data available on every page that
    extends base.html, so the navbar bell reflects real data everywhere,
    not just on the main dashboard view.
    """
    if not request.user.is_authenticated:
        return {}

    from dashboard.models import DashboardNotification

    unread = DashboardNotification.objects.filter(
        user=request.user, is_read=False
    ).order_by('-created_at')[:5]

    return {
        'unread_notifications': unread,
        'notifications_count': DashboardNotification.objects.filter(
            user=request.user, is_read=False
        ).count(),
    }
