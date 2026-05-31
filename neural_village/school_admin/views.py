from django.shortcuts import render
from neural_village.auth.decorators import role_required


@role_required('school_admin', 'instructor')
def dashboard(request):
    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'school_name': 'David Bedford Brain Science Academy',
        'active_cohorts': 5,
        'hardware_online': 24,
        'open_tickets': 3,
    }
    return render(request, 'school_admin/dashboard.html', context)


@role_required('school_admin')
def cohorts(request):
    context = {
        'cohorts': [
            {'name': 'Neuro Track 1', 'students': 24, 'status': 'Active'},
            {'name': 'Neuro Track 2', 'students': 18, 'status': 'Preparing'},
        ],
    }
    return render(request, 'school_admin/cohorts.html', context)


@role_required('school_admin')
def hardware(request):
    context = {
        'devices': [
            {'tag': 'DBBSA-IPAD-01', 'status': 'Online', 'last_seen': '2 minutes ago'},
            {'tag': 'DBBSA-BCI-12', 'status': 'Offline', 'last_seen': '27 minutes ago'},
        ],
    }
    return render(request, 'school_admin/hardware.html', context)


@role_required('school_admin')
def onboarding(request):
    context = {
        'new_students': 12,
        'new_instructors': 2,
        'onboarding_progress': 78,
    }
    return render(request, 'school_admin/onboarding.html', context)
