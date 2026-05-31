from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='/auth/login/')
        def _wrapped_view(request, *args, **kwargs):
            profile = getattr(request.user, 'profile', None)
            if profile is None or profile.role not in allowed_roles:
                return redirect('auth:unauthorized')
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
