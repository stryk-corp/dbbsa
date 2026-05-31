"""
DBBSA URL Configuration
Multi-domain routing for public, school admin, and super admin portals

Routing Structure:
- dbbsa.com/ → Public landing page + student/instructor/parent portals
- admin.dbbsa.com/ → School admin portal (hidden from public)
- sys.neuralvillage.com/ → Super admin portal (internal system access)
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from .middleware import DomainRoutingMiddleware

# Landing page view (public-facing)
urlpatterns_public = [
    # Public landing page (static HTML)
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    
    # Authentication (Student, Instructor, Parent)
    path('auth/', include('neural_village.auth.urls', namespace='auth')),
    
    # Student Portal
    path('portal/student/', include('neural_village.student.urls', namespace='student')),

    # Instructor Portal
    path('portal/instructor/', include('neural_village.instructor.urls', namespace='instructor')),

    # Parent Portal
    path('portal/parent/', include('neural_village.parent.urls', namespace='parent')),

    # School Portal
    path('portal/school/', include('neural_village.school_admin.urls', namespace='school_admin')),
    # CBT Engine (shared across student/instructor roles)
    path('cbt/', include('neural_village.cbt.urls', namespace='cbt')),
    
    # Public API endpoints
    path('api/v1/', include('neural_village.api.public_urls', namespace='api_public')),
]

# School Admin Portal URLs
urlpatterns_school_admin = [
    # School admin authentication & dashboard
    path('auth/', include('neural_village.auth.urls', namespace='auth_admin')),
    
    # School admin portal
    path('', include('neural_village.school_admin.urls', namespace='school_admin')),
    
    # School admin API
    path('api/v1/', include('neural_village.api.school_admin_urls', namespace='api_school_admin')),
]

# Super Admin Portal URLs (sys.neuralvillage.com)
urlpatterns_super_admin = [
    # Super admin authentication & dashboard
    path('auth/', include('neural_village.auth.urls', namespace='auth_super')),
    
    # Super admin portal
    path('', include('neural_village.super_admin.urls', namespace='super_admin')),
    
    # System API
    path('api/v1/', include('neural_village.api.super_admin_urls', namespace='api_super_admin')),
    
    # Django admin (restricted to super admins)
    path('django-admin/', admin.site.urls),
]

# ============================================
# Domain-Based Routing
# ============================================
def get_urlpatterns_for_domain(host):
    """
    Dynamically select URL patterns based on request domain.
    This is applied via middleware, but patterns are organized here.
    """
    if host.startswith('admin.'):
        return urlpatterns_school_admin
    elif host.startswith('sys.'):
        return urlpatterns_super_admin
    else:
        # Default to public portal
        return urlpatterns_public


# Unified URL patterns with admin and API
urlpatterns = [
    # Admin interface (accessible from any domain to admins only)
    path('admin/', admin.site.urls),
    
    # Include all portal-specific patterns
    *urlpatterns_public,
]

# Add school admin patterns conditionally
# (In production, you'd use separate settings files per domain)
if settings.DEBUG:
    urlpatterns += urlpatterns_school_admin + urlpatterns_super_admin

# ============================================
# ARCHITECTURE NOTE: Multi-Domain Pattern
# ============================================
"""
DEPLOYMENT STRATEGY:

Option 1: Separate Django instances (Recommended for high traffic)
- dbbsa.com → Django instance running urlpatterns_public
- admin.dbbsa.com → Django instance running urlpatterns_school_admin
- sys.neuralvillage.com → Django instance running urlpatterns_super_admin
- All instances share the same database for centralized data

Option 2: Single Django instance with domain routing (Current setup)
- Uses DomainRoutingMiddleware to route requests to appropriate urlpatterns
- Simpler to maintain, slightly less performant
- Scales via horizontal load balancing

Option 3: Microservices (Future expansion)
- Break out CBT engine as separate service
- Hardware sync as separate service
- Student/Parent analytics as separate service
"""

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
