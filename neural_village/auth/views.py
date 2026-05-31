from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import redirect, render
from django.urls import reverse
from .forms import LoginForm
from neural_village.core.models import NavigationEvent, User_Profile


ROLE_REDIRECTS = {
    'student': 'student:dashboard',
    'instructor': 'instructor:dashboard',
    'parent': 'parent:dashboard',
    'school_admin': 'school_admin:dashboard',
    'super_admin': 'super_admin:dashboard',
}


def _log_auth_event(request, event_type, target_model='', target_id=None, target_label='', metadata=None):
    if not request.user.is_authenticated:
        return

    profile = getattr(request.user, 'profile', None)
    NavigationEvent.objects.create(
        user=request.user,
        role=getattr(profile, 'role', 'unknown') if profile else 'unknown',
        event_type=event_type,
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        metadata=metadata or {},
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
    )


def get_dashboard_redirect(profile):
    if profile is None:
        return reverse('auth:login')
    return reverse(ROLE_REDIRECTS.get(profile.role, 'auth:login'))


def login_view(request):
    # Determine selected role: prefer explicit `role` query param, otherwise infer from host.
    selected_role = request.GET.get('role')
    if not selected_role:
        host = request.get_host().split(':')[0].lower()
        # If we're on the portal domain choose student/instructor based on query param only
        if host.startswith('admin.'):
            selected_role = 'school_admin'
        elif host in ('portal.lvh.me', 'portal.neuralvillage.com', 'lvh.me'):
            selected_role = 'student'
        else:
            selected_role = 'student'
    else:
        if selected_role not in dict(LoginForm.base_fields['role'].choices):
            selected_role = 'student'

    # Allow forcing the login page even when a user is already authenticated.
    # Use `?force=1` to sign out the current session and view the portal login.
    force_show = request.GET.get('force') == '1'
    if request.user.is_authenticated and force_show:
        auth_logout(request)

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        return redirect(get_dashboard_redirect(profile))

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            user = authenticate(request, username=username, password=password)
            if user is None:
                messages.error(request, 'Invalid username or password. Please try again.')
            else:
                profile = getattr(user, 'profile', None)
                if profile is None:
                    messages.error(request, 'Your account is missing an assigned role profile. Contact support.')
                elif profile.role != role:
                    messages.error(request, 'Please sign in with the correct portal for your role.')
                else:
                    auth_login(request, user)

                    # Respect "remember me" from the form to set session persistence.
                    remember = form.cleaned_data.get('remember_me') if hasattr(form, 'cleaned_data') else False
                    try:
                        if remember:
                            request.session.set_expiry(1209600)  # 2 weeks
                        else:
                            request.session.set_expiry(0)  # expire on browser close
                    except Exception:
                        pass

                    _log_auth_event(
                        request,
                        'login',
                        target_model='User',
                        target_label=user.username,
                        metadata={
                            'role': role,
                            'next': request.POST.get('next'),
                        },
                    )
                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                    next_url = request.POST.get('next')
                    redirect_key = ROLE_REDIRECTS.get(role)
                    # Always reverse named routes to concrete URLs to avoid ambiguity.
                    try:
                        redirect_url = reverse(redirect_key) if redirect_key else reverse('auth:login')
                    except Exception:
                        redirect_url = reverse('auth:login')
                    if next_url:
                        return redirect(next_url)
                    return redirect(redirect_url)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm(initial={'role': selected_role})

    return render(request, 'auth/login.html', {
        'form': form,
        'selected_role': selected_role,
        'available_roles': form.fields['role'].choices,
    })


def logout_view(request):
    auth_logout(request)
    return redirect(reverse('auth:login'))


def unauthorized_view(request):
    return render(request, 'auth/unauthorized.html')
