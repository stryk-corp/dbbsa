"""
DBBSA - Multi-Domain Middleware & Authentication

Routing Strategy:
- dbbsa.com → Public landing page + Student/Instructor/Parent portals
- admin.dbbsa.com → School Admin Portal (hidden from public)
- sys.neuralvillage.com → Super Admin Portal (internal only)
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from .models import User_Profile


class DomainRoutingMiddleware(MiddlewareMixin):
    """
    Routes requests to appropriate portal based on domain.
    Enforces role-based domain access control.
    """
    
    DOMAIN_MAPPING = {
        # Specific local/dev subdomains first so they take precedence
        'portal.lvh.me': {
            'portal': 'public',
            'allowed_roles': ['student', 'parent', 'instructor', 'school_admin'],
            'path_prefix': '/'
        },
        'lvh.me': {
            'portal': 'public',
            'allowed_roles': ['student', 'parent', 'instructor'],
            'path_prefix': '/'
        },
        # Production domains
        'portal.neuralvillage.com': {
            'portal': 'public',
            'allowed_roles': ['student', 'parent', 'instructor', 'school_admin'],
            'path_prefix': '/'
        },
        'dbbsa.com': {
            'portal': 'public',
            'allowed_roles': ['student', 'parent', 'instructor'],
            'path_prefix': '/'
        },
        'www.neuralvillage.com': {
            'portal': 'public',
            'allowed_roles': ['student', 'parent', 'instructor'],
            'path_prefix': '/'
        },
        'admin.dbbsa.com': {
            'portal': 'school_admin',
            'allowed_roles': ['school_admin'],
            'path_prefix': '/admin'
        },
        'sys.neuralvillage.com': {
            'portal': 'super_admin',
            'allowed_roles': ['super_admin'],
            'path_prefix': '/system'
        },
    }
    
    def process_request(self, request):
        """Determine which portal based on domain"""
        host = request.get_host().split(':')[0]  # Remove port if present
        
        # Set portal info on request
        request.current_domain = host
        request.portal_config = None
        
        # Match domain to portal
        for domain, config in self.DOMAIN_MAPPING.items():
            if host == domain or host.endswith('.' + domain):
                request.portal_config = config
                request.portal_name = config['portal']
                break
        
        # Allow Django admin paths for staff/superusers and unauthenticated users (for login)
        if request.path.startswith('/admin/'):
            if request.user.is_authenticated:
                if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
                    return None  # Allow staff/superusers
                # Non-staff authenticated user trying to access admin
                return redirect('auth:unauthorized')
            # Unauthenticated user can see admin login page
            return None

        # If user is authenticated, verify they have access to this domain
        # Allow Django staff/superusers to use the admin domain regardless of profile
        if request.user.is_authenticated and request.portal_config and request.portal_config.get('portal') == 'school_admin':
            if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
                return None

        if request.user.is_authenticated and request.portal_config:
            try:
                profile = request.user.profile
                if profile.role not in request.portal_config['allowed_roles']:
                    # User trying to access portal they're not authorized for
                    return redirect('auth:unauthorized')
            except User_Profile.DoesNotExist:
                pass

        # Redirect root of admin domain to Django admin login to avoid loops
        if request.portal_config and request.portal_config.get('portal') == 'school_admin':
            if request.path in ['', '/']:
                return redirect('/admin/login/')


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Enforces role-based access control at the view level.
    Handles 2FA requirement for school admins & super admins.
    """
    
    def process_request(self, request):
        """Check if user needs 2FA verification"""
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                
                # Require 2FA for sensitive roles
                if profile.requires_2fa and not request.session.get('2fa_verified'):
                    # Allow only 2FA verification views
                    if not request.path.startswith(('/auth/verify-2fa', '/api/verify-2fa')):
                        return redirect('auth:verify_2fa')
            except User_Profile.DoesNotExist:
                pass


def require_role(*allowed_roles):
    """
    Decorator to restrict views to specific roles.
    
    Usage:
        @require_role('student', 'parent')
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('auth:login')
            
            try:
                profile = request.user.profile
                if profile.role not in allowed_roles:
                    return redirect('auth:unauthorized')
            except User_Profile.DoesNotExist:
                return redirect('auth:login')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_domain(required_domain):
    """
    Decorator to restrict views to specific domains.
    
    Usage:
        @require_domain('admin.dbbsa.com')
        def admin_dashboard(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.current_domain != required_domain:
                return redirect('auth:unauthorized')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class SilentTokenRefreshMiddleware(MiddlewareMixin):
    """
    Handles JWT token refresh during CBT sessions.
    Prevents mid-test token expiration issues.
    """
    
    def process_request(self, request):
        """Check if CBT session needs token refresh"""
        if request.user.is_authenticated and request.path.startswith('/cbt/'):
            try:
                # Find active CBT session
                from .models import CBT_Session, Student
                student = request.user.student_profile
                active_session = CBT_Session.objects.filter(
                    student=student,
                    status='in_progress'
                ).first()
                
                if active_session and active_session.should_refresh_token:
                    # Silently refresh token
                    from rest_framework_simplejwt.tokens import RefreshToken
                    refresh = RefreshToken(active_session.jwt_token)
                    active_session.jwt_token = str(refresh.access_token)
                    active_session.token_expires_at = timezone.now() + timedelta(hours=1)
                    active_session.save()
                    
                    # Attach new token to response
                    request.new_jwt_token = str(refresh.access_token)
            except Exception as e:
                # Silently fail - don't interrupt CBT session
                pass
