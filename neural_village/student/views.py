import json
import asyncio
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils import timezone
from django.db.models import Q
from neural_village.auth.decorators import role_required
from neural_village.core.models import AttendanceRecord, AttendanceSession, CBT_Quiz, CBT_Session, Module, Student
from neural_village.student.models import ChatMessage
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
from av import VideoFrame

# Global peer connection storage for WebRTC sessions
webrtc_peer_connections = {}

class MirrorVideoTrack(VideoStreamTrack):
    """Mirror incoming client video back to the client."""

    def __init__(self, source_track):
        super().__init__()
        self.source_track = source_track

    async def recv(self):
        frame = await self.source_track.recv()
        return frame


class MirrorAudioTrack(AudioStreamTrack):
    """Mirror incoming client audio back to the client."""

    def __init__(self, source_track):
        super().__init__()
        self.source_track = source_track

    async def recv(self):
        frame = await self.source_track.recv()
        return frame



def _base_context(request):
    return {
        'welcome_name': request.user.first_name or request.user.username,
        'active_module': 'NEU 101 – Fundamentals of Brain Science',
        'next_quiz': 'Synapses and Neural Networks',
        'progress_percent': 78,
        'cohort_name': 'KNSB Pilot 2026',
        'upcoming_lab': 'NeuroArt Creative Lab',
    }


@role_required('student')
def home(request):
    student_profile = getattr(request.user, 'student_profile', None)
    context = _base_context(request)

    if student_profile and student_profile.cohort:
        students_in_class = Student.objects.filter(
            cohort=student_profile.cohort
        ).select_related('user').order_by('last_name', 'first_name')
        context.update({
            'students_in_class': students_in_class,
            'class_name': student_profile.cohort.name,
            'school_name': student_profile.school.name,
            'class_size': students_in_class.count(),
            'sneak_peeks': [
                {'title': 'Assignments', 'description': 'Review your upcoming assignments and deadlines.', 'url_name': 'student:assignments'},
                {'title': 'Live Quizzes', 'description': 'Jump into scheduled quizzes and practice sessions.', 'url_name': 'student:live_quizzes'},
                {'title': 'Results', 'description': 'Track your scores and performance trends.', 'url_name': 'student:results'},
                {'title': 'Live Class', 'description': 'Join live sessions from your instructor.', 'url_name': 'student:live_class'},
                {'title': 'Chat', 'description': 'Message your classmates and mentors.', 'url_name': 'student:chat'},
                {'title': 'Courses', 'description': 'Browse your current and upcoming courses.', 'url_name': 'student:courses'},
            ],
        })
    else:
        context.update({
            'students_in_class': [],
            'class_name': 'Unknown Cohort',
            'school_name': 'N/A',
            'class_size': 0,
            'sneak_peeks': [
                {'title': 'Assignments', 'description': 'Review your upcoming assignments and deadlines.', 'url_name': 'student:assignments'},
                {'title': 'Live Quizzes', 'description': 'Jump into scheduled quizzes and practice sessions.', 'url_name': 'student:live_quizzes'},
                {'title': 'Results', 'description': 'Track your scores and performance trends.', 'url_name': 'student:results'},
                {'title': 'Live Class', 'description': 'Join live sessions from your instructor.', 'url_name': 'student:live_class'},
                {'title': 'Chat', 'description': 'Message your classmates and mentors.', 'url_name': 'student:chat'},
                {'title': 'Courses', 'description': 'Browse your current and upcoming courses.', 'url_name': 'student:courses'},
            ],
        })

    return render(request, 'student/dashboard.html', context)


@role_required('student')
def assignments(request):
    student_profile = getattr(request.user, 'student_profile', None)
    context = _base_context(request)

    if student_profile:
        available_quizzes = CBT_Quiz.objects.filter(
            is_published=True,
        ).filter(
            Q(module__track=student_profile.track) | Q(module__track='both')
        ).select_related('module').order_by('-created_at')

        sessions = CBT_Session.objects.filter(
            student=student_profile,
            quiz__in=available_quizzes,
        ).select_related('quiz')
        session_map = {session.quiz_id: session for session in sessions}

        assignment_rows = []
        for quiz in available_quizzes:
            session = session_map.get(quiz.id)
            status = 'Not started'
            result_text = 'Ready to begin'
            if session:
                if session.status == 'in_progress':
                    status = 'In progress'
                    result_text = 'Resume your CBT session'
                elif session.status == 'submitted':
                    status = 'Submitted'
                    result_text = 'Awaiting review'
                elif session.status == 'graded':
                    status = 'Graded'
                    result_text = f"Score: {session.score}%" if session.score is not None else 'Graded'
                elif session.status == 'expired':
                    status = 'Expired'
                    result_text = 'Session expired'

            assignment_rows.append({
                'quiz_name': quiz.name,
                'module_code': quiz.module.code,
                'module_name': quiz.module.name,
                'duration': quiz.duration_minutes,
                'passing_score': quiz.passing_score,
                'status': status,
                'result_text': result_text,
            })

        context.update({
            'assignments': assignment_rows,
            'assignment_message': 'CBT assignments are set by your instructor and can be submitted any time before the deadline once released.',
        })
    else:
        context.update({
            'assignments': [],
            'assignment_message': 'Your student profile is not connected yet. Sign in with your student account to view CBT assignments.',
        })

    return render(request, 'student/assignments.html', context)


@role_required('student')
def live_quizzes(request):
    student_profile = getattr(request.user, 'student_profile', None)
    context = _base_context(request)

    if student_profile:
        available_quizzes = CBT_Quiz.objects.filter(
            is_published=True,
        ).filter(
            Q(module__track=student_profile.track) | Q(module__track='both')
        ).select_related('module').order_by('created_at')

        sessions = CBT_Session.objects.filter(
            student=student_profile,
            quiz__in=available_quizzes,
        ).select_related('quiz')
        session_map = {session.quiz_id: session for session in sessions}

        live_quizzes = []
        active_count = 0
        completed_count = 0
        available_count = 0

        for quiz in available_quizzes:
            session = session_map.get(quiz.id)
            status = 'Ready'
            status_key = 'available'
            action_text = 'Start'
            action_url = reverse('student:start_live_quiz', args=[quiz.id])
            action_hint = 'Begin this live quiz when you are ready.'

            if session:
                if session.status == 'in_progress':
                    status = 'In progress'
                    status_key = 'active'
                    action_text = 'Resume'
                    action_hint = f"{int(session.time_remaining_minutes)} minutes remaining"
                    active_count += 1
                elif session.status == 'submitted':
                    status = 'Submitted'
                    status_key = 'submitted'
                    action_text = 'Review'
                    action_hint = 'Your answers are awaiting grading.'
                elif session.status == 'graded':
                    status = 'Completed'
                    status_key = 'passed' if session.passed else 'failed'
                    action_text = 'View results'
                    action_hint = f"Final score: {session.score}%" if session.score is not None else 'Score pending review.'
                    completed_count += 1
                elif session.status == 'expired':
                    status = 'Expired'
                    status_key = 'expired'
                    action_text = 'Review'
                    action_hint = 'This session expired. Contact your instructor for a retake.'
                else:
                    status = 'Ready'
                    status_key = 'available'
                    action_text = 'Start'
                    action_hint = 'This live quiz is set up and ready.'
                    available_count += 1
            else:
                available_count += 1

            live_quizzes.append({
                'quiz_name': quiz.name,
                'module_code': quiz.module.code,
                'module_name': quiz.module.name,
                'duration': quiz.duration_minutes,
                'passing_score': quiz.passing_score,
                'status': status,
                'status_key': status_key,
                'action_text': action_text,
                'action_url': action_url,
                'action_hint': action_hint,
            })

        context.update({
            'live_quizzes': live_quizzes,
            'live_message': 'Jump into your live quiz practice and resume active CBT sessions.',
            'active_count': active_count,
            'available_count': available_count,
            'completed_count': completed_count,
        })
    else:
        context.update({
            'live_quizzes': [],
            'live_message': 'Your student profile is not connected yet. Sign in to see live quizzes.',
            'active_count': 0,
            'available_count': 0,
            'completed_count': 0,
        })

    return render(request, 'student/live_quizzes.html', context)


@role_required('student')
def start_live_quiz(request, quiz_id):
    student_profile = getattr(request.user, 'student_profile', None)
    if not student_profile:
        messages.error(request, 'Your student profile must be connected to start this quiz.')
        return redirect('student:live_quizzes')

    quiz = get_object_or_404(
        CBT_Quiz.objects.filter(is_published=True).select_related('module'),
        id=quiz_id,
        module__track__in=[student_profile.track, 'both']
    )

    session, created = CBT_Session.objects.get_or_create(
        student=student_profile,
        quiz=quiz,
        defaults={'status': 'in_progress', 'start_time': timezone.now()}
    )

    if not created:
        if session.status in ['not_started', 'expired']:
            session.status = 'in_progress'
            session.start_time = timezone.now()
            session.save()

    if session.status == 'in_progress':
        messages.success(request, f'"{quiz.name}" is ready. Resume it from the assignments dashboard.')
    elif session.status == 'submitted':
        messages.info(request, f'"{quiz.name}" has been submitted and is awaiting grading.')
    elif session.status == 'graded':
        messages.info(request, f'"{quiz.name}" is graded. See your results in the results dashboard.')
    else:
        messages.success(request, f'"{quiz.name}" is ready in your assignments dashboard.')

    return redirect('student:assignments')


@role_required('student')
def results(request):
    student_profile = getattr(request.user, 'student_profile', None)
    context = _base_context(request)

    if student_profile:
        sessions = CBT_Session.objects.filter(
            student=student_profile
        ).select_related('quiz__module').order_by('-updated_at')

        scored_sessions = [s for s in sessions if s.score is not None]
        graded_sessions = [s for s in sessions if s.status == 'graded']
        passed_count = sum(1 for s in scored_sessions if s.passed)
        failed_count = sum(1 for s in scored_sessions if s.passed is False)

        average_score = None
        pass_rate = None
        if scored_sessions:
            average_score = sum(s.score for s in scored_sessions if s.score is not None) / len(scored_sessions)
            pass_rate = int(round(100 * passed_count / len(scored_sessions)))

        result_rows = []
        for session in sessions:
            quiz = session.quiz
            module = quiz.module
            status_label = session.status.replace('_', ' ').title()
            if session.status == 'graded':
                status_label = 'Passed' if session.passed else 'Failed'

            if session.status == 'graded':
                result_text = f"Score: {session.score}%" if session.score is not None else 'Awaiting score'
            elif session.status == 'submitted':
                result_text = 'Awaiting grading'
            elif session.status == 'in_progress':
                result_text = 'Resume your quiz'
            elif session.status == 'expired':
                result_text = 'Session expired'
            else:
                result_text = 'Not started yet'

            result_rows.append({
                'quiz_name': quiz.name,
                'module_code': module.code,
                'module_name': module.name,
                'score': f"{session.score}%" if session.score is not None else '—',
                'score_numeric': session.score if session.score is not None else None,
                'passing_score': quiz.passing_score,
                'status': status_label,
                'status_key': 'passed' if session.status == 'graded' and session.passed else 'failed' if session.status == 'graded' else session.status,
                'result_text': result_text,
                'updated_at': session.updated_at,
            })

        context.update({
            'results': result_rows,
            'total_quizzes': sessions.count(),
            'graded_count': len(graded_sessions),
            'passed_count': passed_count,
            'failed_count': failed_count,
            'average_score': f"{average_score:.0f}%" if average_score is not None else '—',
            'pass_rate': f"{pass_rate}%" if pass_rate is not None else '—',
            'pass_rate_raw': pass_rate if pass_rate is not None else 0,
            'results_message': 'Review your graded quizzes, score trends, and next steps.',
        })
    else:
        context.update({
            'results': [],
            'total_quizzes': 0,
            'graded_count': 0,
            'passed_count': 0,
            'failed_count': 0,
            'average_score': '—',
            'pass_rate': '—',
            'results_message': 'Your results will appear here once your student profile is connected.',
        })

    return render(request, 'student/results.html', context)


@role_required('student')
def live_class(request):
    student_profile = getattr(request.user, 'student_profile', None)
    context = _base_context(request)

    if student_profile and student_profile.cohort:
        active_attendance = AttendanceSession.objects.filter(
            cohort=student_profile.cohort,
            status='active'
        ).select_related('module', 'instructor').first()

        attendance_record = None
        attendance_present_count = 0
        if active_attendance:
            attendance_record = AttendanceRecord.objects.filter(
                session=active_attendance,
                student=student_profile
            ).first()
            attendance_present_count = active_attendance.present_count

        camera_on = False
        mic_on = False
        participation_percent = 0

        if request.method == 'POST' and active_attendance:
            camera_on = request.POST.get('camera_on') == 'true'
            mic_on = request.POST.get('mic_on') == 'true'
            participation_percent = 60 if camera_on or mic_on else 0

            if attendance_record is None:
                if not camera_on and not mic_on:
                    messages.error(request, 'You must have either camera or microphone active to sign attendance.')
                else:
                    AttendanceRecord.objects.create(
                        session=active_attendance,
                        student=student_profile,
                        status='present'
                    )
                    messages.success(request, 'Your attendance has been marked present for this session.')
                    return redirect('student:live_class')
            else:
                messages.info(request, 'Your attendance has already been recorded.')

        context.update({
            'active_attendance': active_attendance,
            'attendance_record': attendance_record,
            'attendance_present_count': attendance_present_count,
            'attendance_total_count': student_profile.cohort.students.filter(is_active=True).count(),
            'cohort_name': student_profile.cohort.name,
            'camera_on': camera_on,
            'mic_on': mic_on,
            'participation_percent': participation_percent,
        })
    else:
        context.update({
            'active_attendance': None,
            'attendance_record': None,
            'attendance_present_count': 0,
            'attendance_total_count': 0,
            'cohort_name': 'Unknown Cohort',
        })

    return render(request, 'student/live_class.html', context)


@role_required('student')
def chat_view(request):
    student = request.user.student_profile
    cohort = student.cohort

    chat_messages = (
        ChatMessage.objects
        .filter(cohort=cohort)
        .select_related('sender', 'sender__user')
        .order_by('created_at')
    )
    chat_classmates = (
        cohort.students
        .exclude(pk=student.pk)
        .select_related('user')
        .order_by('last_name', 'first_name')
    )

    return render(request, 'student/chat.html', {
        'welcome_name': student.first_name or student.user.username,
        'cohort_name': cohort.name,
        'chat_guide': 'Connect with your cohort in real time.',
        'chat_messages': chat_messages,
        'chat_classmates': chat_classmates,
    })


@role_required('student')
@require_POST
def chat_send(request):
    student = request.user.student_profile
    content = request.POST.get('message', '').strip()

    if not content:
        return JsonResponse({'status': 'error', 'detail': 'Empty message.'}, status=400)

    msg = ChatMessage.objects.create(
        sender=student,
        cohort=student.cohort,
        content=content,
        message_type='text',
    )

    return JsonResponse({
        'status': 'ok',
        'message': _serialize_message(msg),
    })


@role_required('student')
@require_GET
def chat_poll(request):
    student = request.user.student_profile
    after_pk = int(request.GET.get('after', 0))

    messages_qs = (
        ChatMessage.objects
        .filter(cohort=student.cohort, pk__gt=after_pk)
        .select_related('sender', 'sender__user')
        .order_by('created_at')
    )

    return JsonResponse({
        'messages': [_serialize_message(msg) for msg in messages_qs]
    })


def _serialize_message(msg):
    return {
        'pk': msg.pk,
        'sender_pk': msg.sender.pk,
        'sender_name': f'{msg.sender.first_name} {msg.sender.last_name}',
        'sender_username': msg.sender.user.username,
        'content': msg.content,
        'time': timezone.localtime(msg.created_at).strftime('%H:%M'),
    }


@role_required('student')
def courses(request):
    student_profile = getattr(request.user, 'student_profile', None)
    context = _base_context(request)

    if student_profile and student_profile.cohort:
        modules = Module.objects.filter(
            is_published=True,
        ).filter(
            Q(track=student_profile.track) | Q(track='both')
        ).order_by('code')

        quizzes = CBT_Quiz.objects.filter(
            module__in=modules,
            is_published=True,
        ).select_related('module')

        sessions = CBT_Session.objects.filter(
            student=student_profile,
            quiz__in=quizzes,
        ).select_related('quiz')
        session_map = {session.quiz_id: session for session in sessions}

        module_rows = []
        for module in modules:
            module_quizzes = [quiz for quiz in quizzes if quiz.module_id == module.id]
            progress_count = sum(1 for quiz in module_quizzes if session_map.get(quiz.id) and session_map[quiz.id].status == 'graded')
            module_rows.append({
                'code': module.code,
                'name': module.name,
                'description': module.description,
                'credits': module.credits,
                'duration_weeks': module.duration_weeks,
                'quiz_count': len(module_quizzes),
                'graded_quizzes': progress_count,
                'track': module.get_track_display(),
            })

        context.update({
            'course_modules': module_rows,
            'course_message': 'Your current curriculum modules are listed here with CBT quiz progress and class links.',
            'courses_cta': {
                'assignments': 'student:assignments',
                'live_quizzes': 'student:live_quizzes',
                'chat': 'student:chat',
            },
            'cohort_name': student_profile.cohort.name,
        })
    else:
        context.update({
            'course_modules': [],
            'course_message': 'Your student profile is not fully linked yet. Courses will appear once your cohort is assigned.',
            'courses_cta': {},
            'cohort_name': 'Unknown Cohort',
        })

    return render(request, 'student/courses.html', context)


# ============================================================================
# WebRTC Signaling Endpoints
# ============================================================================

@role_required('student')
@require_http_methods(['POST'])
def webrtc_offer(request):
    """
    Handle WebRTC offer from client.
    Receives SDP offer, creates peer connection, and returns SDP answer.
    """
    student_profile = getattr(request.user, 'student_profile', None)
    if not student_profile or not student_profile.cohort:
        return JsonResponse({'error': 'Student profile not found'}, status=400)

    try:
        data = json.loads(request.body)
        offer_sdp = data.get('sdp')
        offer_type = data.get('type')
        session_id = data.get('session_id')

        if not offer_sdp or not session_id:
            return JsonResponse({'error': 'Missing SDP or session_id'}, status=400)

        # Check if attendance session is active
        attendance_session = AttendanceSession.objects.filter(
            pk=session_id,
            status='active'
        ).first()
        if not attendance_session:
            return JsonResponse({'error': 'Attendance session not active'}, status=400)

        # Create or retrieve peer connection for this student
        peer_key = f"{student_profile.id}_{session_id}"
        
        if peer_key not in webrtc_peer_connections:
            pc = RTCPeerConnection()
            webrtc_peer_connections[peer_key] = {
                'pc': pc,
                'student': student_profile,
                'session': attendance_session,
                'created_at': timezone.now(),
            }
        else:
            pc = webrtc_peer_connections[peer_key]['pc']

        @pc.on('track')
        def on_track(track):
            if track.kind == 'video':
                pc.addTrack(MirrorVideoTrack(track))
            elif track.kind == 'audio':
                pc.addTrack(MirrorAudioTrack(track))

            @track.on('ended')
            async def on_ended():
                print(f'Track {track.kind} ended')

        # Handle async offer processing synchronously
        async def process_offer():
            offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            while pc.iceGatheringState != 'complete':
                await asyncio.sleep(0.1)

            return {
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type,
            }

        loop = asyncio.new_event_loop()
        try:
            answer_data = loop.run_until_complete(process_offer())
        finally:
            loop.close()

        return JsonResponse(answer_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required('student')
@require_http_methods(['POST'])
def webrtc_ice_candidate(request):
    """
    Handle ICE candidate from client for NAT traversal.
    """
    student_profile = getattr(request.user, 'student_profile', None)
    if not student_profile:
        return JsonResponse({'error': 'Student profile not found'}, status=400)

    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        candidate = data.get('candidate')

        peer_key = f"{student_profile.id}_{session_id}"
        
        if peer_key in webrtc_peer_connections:
            pc = webrtc_peer_connections[peer_key]['pc']
            
            async def add_candidate():
                if candidate:
                    await pc.addIceCandidate(candidate)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(add_candidate())
            finally:
                loop.close()

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@role_required('student')
@require_http_methods(['POST'])
def webrtc_close(request):
    """
    Close WebRTC peer connection and cleanup.
    """
    student_profile = getattr(request.user, 'student_profile', None)
    if not student_profile:
        return JsonResponse({'error': 'Student profile not found'}, status=400)

    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')

        peer_key = f"{student_profile.id}_{session_id}"
        
        if peer_key in webrtc_peer_connections:
            pc = webrtc_peer_connections[peer_key]['pc']
            
            async def close_pc():
                await pc.close()

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(close_pc())
            finally:
                loop.close()
            
            del webrtc_peer_connections[peer_key]

        return JsonResponse({'status': 'closed'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
