from django.shortcuts import render
from neural_village.auth.decorators import role_required


@role_required('super_admin')
def dashboard(request):
    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'partner_schools': 12,
        'total_students': 812,
        'platform_health': 'Excellent',
        'next_system_audit': 'June 03, 2026',
    }
    return render(request, 'super_admin/dashboard.html', context)
