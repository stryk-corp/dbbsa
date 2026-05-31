from django.shortcuts import render
from neural_village.auth.decorators import role_required


@role_required('parent')
def dashboard(request):
    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'child_name': 'Ada Okoye',
        'child_progress': 86,
        'upcoming_reports': 2,
        'next_event': 'Parent-Teacher Sync Call',
    }
    return render(request, 'parent/dashboard.html', context)


@role_required('parent')
def students(request):
    context = {
        'children': [
            {'name': 'Ada Okoye', 'cohort': 'Neuro Track 1', 'progress': 86},
            {'name': 'Emeka Bello', 'cohort': 'Neuro Track 2', 'progress': 74},
        ],
    }
    return render(request, 'parent/students.html', context)


@role_required('parent')
def progress(request):
    context = {
        'overview': {
            'attendance': 92,
            'assignments_completed': 18,
            'average_score': 88,
        },
    }
    return render(request, 'parent/progress.html', context)
