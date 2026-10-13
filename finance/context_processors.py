from .models import Cycle


def active_cycle(request):
    """The signed-in user's current cycle, shown in the sidebar on every page."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    return {'active_cycle': Cycle.objects.filter(user=user).first()}
