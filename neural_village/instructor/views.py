import json

from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from neural_village.auth.decorators import role_required
from neural_village.core.models import (
    AttendanceSession,
    CBT_Quiz,
    CBT_Session,
    Cohort,
    Module,
    NavigationEvent,
    School,
    Student,
)


def _log_instructor_event(request, event_type, target_model='', target_id=None, target_label='', metadata=None):
    if not request.user.is_authenticated:
        return

    profile = getattr(request.user, 'profile', None)
    NavigationEvent.objects.create(
        user=request.user,
        role=getattr(profile, 'role', 'instructor') if profile else 'instructor',
        event_type=event_type,
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        metadata=metadata or {},
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
    )


@role_required('instructor')
def dashboard(request):
    instructor = getattr(request.user, 'instructor_profile', None)
    if instructor is None:
        messages.error(request, 'Instructor profile not found.')
        return redirect('auth:login')

    school = instructor.school
    cohorts = Cohort.objects.filter(instructor=instructor).prefetch_related('students', 'school')
    active_cohorts = cohorts.filter(status='active')
    modules = Module.objects.order_by('code')[:20]
    active_attendance_sessions = AttendanceSession.objects.filter(
        instructor=instructor,
        status='active'
    ).select_related('cohort', 'module').order_by('-activated_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'start':
            cohort_id = request.POST.get('cohort')
            module_id = request.POST.get('module')
            note = request.POST.get('note', '').strip()
            cohort = Cohort.objects.filter(pk=cohort_id, instructor=instructor).first()
            module = Module.objects.filter(pk=module_id).first() if module_id else None

            if cohort is None:
                messages.error(request, 'Unable to start attendance for the selected cohort.')
                return redirect('instructor:dashboard')

            AttendanceSession.objects.filter(cohort=cohort, status='active').update(
                status='closed',
                ended_at=timezone.now(),
            )
            session = AttendanceSession.objects.create(
                cohort=cohort,
                instructor=instructor,
                module=module,
                note=note,
                status='active',
            )
            messages.success(request, f'Attendance session started for {cohort.name}.')
            _log_instructor_event(
                request,
                'attendance_action',
                target_model='AttendanceSession',
                target_id=session.id,
                target_label=f'Started {cohort.name}',
                metadata={'note': note, 'module_id': str(module.id) if module else None},
            )
            return redirect('instructor:dashboard')

        if action == 'close':
            session_id = request.POST.get('session_id')
            session = AttendanceSession.objects.filter(
                pk=session_id,
                instructor=instructor,
                status='active'
            ).first()
            if session:
                session.status = 'closed'
                session.ended_at = timezone.now()
                session.save()
                messages.success(request, 'Attendance session closed.')
                _log_instructor_event(
                    request,
                    'attendance_action',
                    target_model='AttendanceSession',
                    target_id=session.id,
                    target_label=f'Closed {session.cohort.name}',
                )
            else:
                messages.error(request, 'No active attendance session was found to close.')
            return redirect('instructor:dashboard')

    student_count = Student.objects.filter(cohort__in=active_cohorts, is_active=True).count()
    pending_reviews = CBT_Session.objects.filter(student__cohort__in=active_cohorts, status='submitted').count()
    open_attendance_count = active_attendance_sessions.count()
    in_progress_quiz_sessions = CBT_Session.objects.filter(
        student__cohort__in=active_cohorts,
        status='in_progress'
    ).select_related('quiz', 'student').order_by('-updated_at')[:6]

    school_cohorts = school.cohorts.order_by('-start_date')
    total_school_cohorts = school_cohorts.count()
    total_school_students = Student.objects.filter(school=school, is_active=True).count()
    total_school_instructors = school.instructors.filter(is_active=True).count()
    school_pending_reviews = CBT_Session.objects.filter(student__school=school, status='submitted').count()
    school_attendance_open = AttendanceSession.objects.filter(cohort__school=school, status='active').count()

    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'school': school,
        'active_cohort': active_cohorts.first().name if active_cohorts.exists() else 'No active cohort',
        'pending_reviews': pending_reviews,
        'students_in_class': student_count,
        'next_review': 'Synapses Quiz grading by Friday',
        'cohorts': active_cohorts,
        'modules': modules,
        'active_attendance_sessions': active_attendance_sessions,
        'in_progress_quiz_sessions': in_progress_quiz_sessions,
        'total_school_cohorts': total_school_cohorts,
        'total_school_students': total_school_students,
        'total_school_instructors': total_school_instructors,
        'school_pending_reviews': school_pending_reviews,
        'school_attendance_open': school_attendance_open,
        'current_page': 'dashboard',
        'page_name': 'Dashboard',
    }

    _log_instructor_event(request, 'page_view', target_model='InstructorDashboard', target_label='Dashboard')
    response = render(request, 'instructor/dashboard.html', context)
    return response


@role_required('instructor')
def cohorts(request):
    instructor = getattr(request.user, 'instructor_profile', None)
    if instructor is None:
        messages.error(request, 'Instructor profile not found.')
        return redirect('auth:login')

    school = instructor.school
    cohorts = Cohort.objects.filter(instructor=instructor).prefetch_related('students')
    for cohort in cohorts:
        cohort.pending_reviews = CBT_Session.objects.filter(student__cohort=cohort, status='submitted').count()
        cohort.active_attendance = AttendanceSession.objects.filter(cohort=cohort, status='active').count()

    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'school': school,
        'cohorts': cohorts,
        'current_page': 'cohorts',
        'page_name': 'Your Cohorts',
    }

    _log_instructor_event(request, 'page_view', target_model='InstructorCohorts', target_label='Cohorts')
    return render(request, 'instructor/cohorts.html', context)


@role_required('instructor')
def students(request):
    instructor = getattr(request.user, 'instructor_profile', None)
    if instructor is None:
        messages.error(request, 'Instructor profile not found.')
        return redirect('auth:login')

    cohorts = Cohort.objects.filter(instructor=instructor)
    cohort_id = request.GET.get('cohort')
    students = Student.objects.filter(cohort__in=cohorts, is_active=True).select_related('cohort').order_by('last_name', 'first_name')
    if cohort_id:
        students = students.filter(cohort__id=cohort_id)

    for student in students:
        student.pending_reviews = student.cbt_sessions.filter(status='submitted').count()

    active_cohorts = cohorts.filter(status='active')
    total_pending_reviews = CBT_Session.objects.filter(student__cohort__in=cohorts, status='submitted').count()

    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'school': instructor.school,
        'students': students,
        'active_cohorts': active_cohorts,
        'total_pending_reviews': total_pending_reviews,
        'current_page': 'students',
        'page_name': 'Students',
    }

    _log_instructor_event(request, 'page_view', target_model='InstructorStudents', target_label='Students')
    return render(request, 'instructor/students.html', context)


@role_required('instructor')
def insights(request):
    instructor = getattr(request.user, 'instructor_profile', None)
    if instructor is None:
        messages.error(request, 'Instructor profile not found.')
        return redirect('auth:login')

    cohorts = Cohort.objects.filter(instructor=instructor).prefetch_related('students')
    active_cohorts = cohorts.filter(status='active')
    active_students = Student.objects.filter(cohort__in=active_cohorts, is_active=True).count()
    pending_reviews = CBT_Session.objects.filter(student__cohort__in=active_cohorts, status='submitted').count()
    open_attendance_count = AttendanceSession.objects.filter(cohort__in=active_cohorts, status='active').count()

    cohort_pressure = []
    for cohort in cohorts:
        cohort.pending_reviews = CBT_Session.objects.filter(student__cohort=cohort, status='submitted').count()
        cohort.active_attendance = AttendanceSession.objects.filter(cohort=cohort, status='active').count()
        cohort_pressure.append(cohort)

    recommendation_cards = [
        {'label': 'Review submissions', 'value': pending_reviews, 'hint': 'Mark and return CBT results quickly.'},
        {'label': 'Open attendance', 'value': open_attendance_count, 'hint': 'Close or update active sessions.'},
        {'label': 'Cohorts ready', 'value': active_cohorts.count(), 'hint': 'Check which groups are live.'},
        {'label': 'Total students', 'value': active_students, 'hint': 'Monitor active learners across your cohorts.'},
    ]

    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'school': instructor.school,
        'active_cohorts': active_cohorts,
        'active_students': active_students,
        'pending_reviews': pending_reviews,
        'open_attendance_count': open_attendance_count,
        'recommendation_cards': recommendation_cards,
        'cohort_pressure': cohort_pressure,
        'current_page': 'insights',
        'page_name': 'Insights',
    }

    _log_instructor_event(request, 'page_view', target_model='InstructorInsights', target_label='Insights')
    return render(request, 'instructor/insights.html', context)


@role_required('instructor')
def cohort_detail(request, cohort_id):
    instructor = getattr(request.user, 'instructor_profile', None)
    cohort = get_object_or_404(Cohort, pk=cohort_id, instructor=instructor)
    students = cohort.students.select_related('user').order_by('last_name', 'first_name')
    attendance_sessions = cohort.attendance_sessions.order_by('-created_at').select_related('module', 'instructor')
    quiz_sessions = CBT_Session.objects.filter(student__cohort=cohort).select_related('quiz', 'student').order_by('-updated_at')
    status_breakdown = quiz_sessions.values('status').annotate(count=Count('id'))

    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'cohort': cohort,
        'students': students,
        'attendance_sessions': attendance_sessions,
        'quiz_sessions': quiz_sessions,
        'status_breakdown': {item['status']: item['count'] for item in status_breakdown},
        'current_page': 'cohort_detail',
        'page_name': cohort.name,
    }

    _log_instructor_event(
        request,
        'cohort_view',
        target_model='Cohort',
        target_id=cohort.id,
        target_label=cohort.name,
    )
    return render(request, 'instructor/cohort_detail.html', context)


@role_required('instructor')
def school_overview(request):
    instructor = getattr(request.user, 'instructor_profile', None)
    school = getattr(instructor, 'school', None)
    if school is None:
        messages.error(request, 'Unable to determine your school affiliation.')
        return redirect('instructor:dashboard')

    school_cohorts = school.cohorts.order_by('-start_date')
    active_cohorts = school_cohorts.filter(status='active')
    total_students = Student.objects.filter(school=school, is_active=True).count()
    pending_reviews = CBT_Session.objects.filter(student__school=school, status='submitted').count()
    open_attendance_sessions = AttendanceSession.objects.filter(cohort__school=school, status='active').count()

    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'school': school,
        'active_cohorts': active_cohorts,
        'total_cohorts': school_cohorts.count(),
        'total_students': total_students,
        'total_instructors': school.instructors.filter(is_active=True).count(),
        'pending_reviews': pending_reviews,
        'open_attendance_sessions': open_attendance_sessions,
        'school_cohorts': school_cohorts,
        'current_page': 'school_overview',
        'page_name': 'School Overview',
    }

    _log_instructor_event(
        request,
        'school_view',
        target_model='School',
        target_id=school.id,
        target_label=school.name,
    )
    return render(request, 'instructor/school_overview.html', context)


@role_required('instructor')
@require_POST
def log_event(request):
    payload = {}
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        pass

    event_type = payload.get('event_type', 'navigation')
    target_model = payload.get('target_model', '')
    target_id = payload.get('target_id')
    target_label = payload.get('target_label', '')
    metadata = payload.get('metadata', {})

    _log_instructor_event(
        request,
        event_type,
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        metadata=metadata,
    )
    return JsonResponse({'success': True})
