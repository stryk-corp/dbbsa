from django.contrib import admin
from django.utils import timezone
import uuid

from .models import (
    School,
    Cohort,
    User_Profile,
    NavigationEvent,
    Student,
    Parent,
    Instructor,
    AttendanceSession,
    AttendanceRecord,
    Module,
    CBT_Quiz,
    CBT_Question,
    CBT_Session,
    HardwareAsset,
    Lab_Project,
    Lab_Submission,
    Invoice,
    TransactionWebhookLog,
    WaitlistEntry,
)


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    readonly_fields = ('recorded_at',)
    fields = ('student', 'status', 'recorded_at')


class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('cohort', 'instructor', 'module', 'status', 'activated_at', 'ended_at')
    list_filter = ('status', 'module', 'cohort__school')
    search_fields = ('cohort__name', 'instructor__first_name', 'instructor__last_name', 'module__code')
    inlines = (AttendanceRecordInline,)
    readonly_fields = ('created_at', 'activated_at', 'ended_at')
    raw_id_fields = ('cohort', 'instructor', 'module')


class InstructorInline(admin.TabularInline):
    model = Instructor
    fields = ('first_name', 'last_name', 'specialization', 'is_active', 'can_grade', 'can_deploy_cbt')
    extra = 0
    readonly_fields = ('first_name', 'last_name', 'specialization', 'is_active', 'can_grade', 'can_deploy_cbt')
    show_change_link = True


class CohortInline(admin.TabularInline):
    model = Cohort
    fields = ('name', 'track', 'status', 'instructor', 'start_date', 'end_date')
    extra = 0
    readonly_fields = ('name', 'track', 'status', 'instructor', 'start_date', 'end_date')
    show_change_link = True


class StudentInline(admin.TabularInline):
    model = Student
    fields = ('first_name', 'last_name', 'cohort', 'track', 'is_active')
    extra = 0
    readonly_fields = ('first_name', 'last_name', 'cohort', 'track', 'is_active')
    show_change_link = True


class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'tracks_offered', 'student_capacity', 'is_active', 'subeb_verified')
    list_filter = ('tracks_offered', 'is_active', 'subeb_verified')
    search_fields = ('name', 'location', 'primary_contact_email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (InstructorInline, CohortInline, StudentInline)


class CohortAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'track', 'status', 'instructor', 'start_date', 'end_date', 'current_enrollment')
    list_filter = ('track', 'status', 'school')
    search_fields = ('name', 'school__name', 'instructor__first_name', 'instructor__last_name')
    raw_id_fields = ('school', 'instructor')
    readonly_fields = ('created_at', 'updated_at')

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.user.is_authenticated and hasattr(request.user, 'instructor_profile'):
            instructor = request.user.instructor_profile
            initial.setdefault('school', instructor.school.pk)
            initial.setdefault('instructor', instructor.pk)
        return initial

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'instructor' and request.user.is_authenticated and hasattr(request.user, 'instructor_profile'):
            instructor = request.user.instructor_profile
            kwargs['queryset'] = Instructor.objects.filter(school=instructor.school, is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if request.user.is_authenticated and hasattr(request.user, 'instructor_profile'):
            current_instructor = request.user.instructor_profile
            if not obj.instructor and obj.school == current_instructor.school:
                obj.instructor = current_instructor
            if obj.instructor and not obj.school:
                obj.school = obj.instructor.school
        if obj.instructor and obj.school != obj.instructor.school:
            obj.school = obj.instructor.school
        super().save_model(request, obj, form, change)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'digital_id', 'is_verified', 'requires_2fa')
    list_filter = ('role', 'is_verified', 'requires_2fa')
    search_fields = ('user__username', 'user__email', 'digital_id')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)


class NavigationEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'event_type', 'target_model', 'target_label', 'ip_address', 'created_at')
    list_filter = ('event_type', 'role')
    search_fields = ('user__username', 'target_model', 'target_label')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)


class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'school', 'cohort', 'track', 'is_active', 'brain_skills_score')
    list_filter = ('school', 'cohort', 'track', 'is_active')
    search_fields = ('first_name', 'last_name', 'user__username', 'user__email')
    raw_id_fields = ('user', 'school', 'cohort')
    readonly_fields = ('created_at', 'updated_at')

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.user.is_authenticated and hasattr(request.user, 'instructor_profile'):
            instructor = request.user.instructor_profile
            initial.setdefault('school', instructor.school.pk)
        return initial

    def save_model(self, request, obj, form, change):
        if obj.cohort and (not obj.school or obj.school != obj.cohort.school):
            obj.school = obj.cohort.school
        super().save_model(request, obj, form, change)


class ParentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'phone', 'notifications_enabled')
    list_filter = ('notifications_enabled',)
    search_fields = ('first_name', 'last_name', 'user__username', 'user__email', 'phone')
    raw_id_fields = ('user', 'children')
    readonly_fields = ('created_at', 'updated_at')


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'payer_user', 'amount', 'currency', 'status', 'due_date')
    list_filter = ('status', 'currency', 'gateway')
    search_fields = (
        'student__first_name',
        'student__last_name',
        'payer_user__username',
        'payer_user__email',
        'reference_code',
    )
    raw_id_fields = ('student', 'payer_user')
    readonly_fields = ('created_at', 'updated_at')


class TransactionWebhookLogAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'gateway', 'reference_code', 'processed_at', 'created_at')
    list_filter = ('gateway',)
    search_fields = ('invoice__id', 'reference_code')
    readonly_fields = ('created_at', 'processed_at', 'payload_dump')
    raw_id_fields = ('invoice',)


class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'role_requested', 'status', 'created_at')
    list_filter = ('status', 'role_requested')
    search_fields = ('email', 'full_name', 'payment_reference')
    readonly_fields = ('created_at', 'processed_at', 'temp_token')
    actions = ('provision_accounts', 'send_credentials_and_remove')

    def provision_accounts(self, request, queryset):
        from django.contrib.auth.models import User
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import User_Profile

        created = 0
        for entry in queryset:
            if entry.status in ('PROVISIONED', 'APPROVED'):
                continue
            username = entry.email.split('@')[0]
            user, created_flag = User.objects.get_or_create(username=username, defaults={'email': entry.email})
            if created_flag:
                user.set_password('dbbsa')
                user.save()

            # Create or update user profile
            up, _ = User_Profile.objects.get_or_create(user=user, defaults={'role': (entry.role_requested or 'student'), 'digital_id': f'NV-{str(uuid.uuid4())[:8]}'})
            if not created_flag:
                up.role = (entry.role_requested or up.role)
                if not up.digital_id:
                    up.digital_id = f'NV-{str(uuid.uuid4())[:8]}'
                up.save()

            entry.status = 'APPROVED'
            entry.processed_at = timezone.now()
            entry.save()
            created += 1

        self.message_user(request, f"Provisioned {created} account(s).")
    provision_accounts.short_description = 'Provision accounts for selected waitlist entries'

    def send_credentials_and_remove(self, request, queryset):
        from django.contrib.auth.models import User
        from django.core.mail import send_mail
        from django.conf import settings

        sent = 0
        for entry in queryset:
            try:
                username = entry.email.split('@')[0]
                user = User.objects.get(username=username)
            except Exception:
                continue

            subject = 'DBBSA — Your account credentials'
            message = (
                f"Hello {entry.full_name or entry.email},\n\n"
                f"Your account has been created.\nUsername: {user.username}\nPassword: dbbsa\n\n"
                "Please login at: https://www.neuroscienceacademy.edu.ng/auth/login/\n\n"
                "Regards,\nDBBSA Team"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@dbbsa.com', [entry.email], fail_silently=True)

            # mark as provisioned and remove from waitlist
            entry.status = 'PROVISIONED'
            entry.processed_at = timezone.now()
            entry.save()
            sent += 1

        self.message_user(request, f"Sent credentials to {sent} applicant(s) and removed them from the waitlist.")
    send_credentials_and_remove.short_description = 'Send credentials to applicants and remove from waitlist'


class CohortInline(admin.TabularInline):
    model = Cohort
    fields = ('name', 'track', 'status', 'start_date', 'end_date')
    extra = 0
    readonly_fields = ('name', 'track', 'status', 'start_date', 'end_date')
    can_delete = False
    show_change_link = True


class InstructorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'school', 'specialization', 'is_active', 'can_grade', 'can_deploy_cbt')
    list_filter = ('school', 'is_active', 'can_grade', 'can_deploy_cbt')
    search_fields = ('first_name', 'last_name', 'user__username', 'user__email', 'specialization')
    raw_id_fields = ('user', 'school')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (CohortInline,)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.user.is_authenticated and hasattr(request.user, 'instructor_profile'):
            initial.setdefault('school', request.user.instructor_profile.school.pk)
        return initial

    def save_model(self, request, obj, form, change):
        if request.user.is_authenticated and hasattr(request.user, 'instructor_profile'):
            if not obj.school:
                obj.school = request.user.instructor_profile.school
        super().save_model(request, obj, form, change)


class ModuleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'track', 'credits', 'duration_weeks', 'is_published')
    list_filter = ('track', 'is_published')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at', 'updated_at')


class CBTQuestionInline(admin.TabularInline):
    model = CBT_Question
    extra = 1
    fields = ('order', 'question_text', 'question_type', 'point_value', 'model_url', 'correct_answer')


class CBTQuizAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'duration_minutes', 'total_questions', 'passing_score', 'is_published')
    list_filter = ('is_published', 'module')
    search_fields = ('name', 'module__name', 'module__code')
    raw_id_fields = ('module',)
    inlines = (CBTQuestionInline,)
    readonly_fields = ('created_at', 'updated_at')


class CBTSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'status', 'score', 'passed', 'start_time', 'end_time', 'updated_at')
    list_filter = ('status', 'passed', 'quiz', 'student__school')
    search_fields = (
        'student__user__username',
        'student__first_name',
        'student__last_name',
        'quiz__name',
    )
    raw_id_fields = ('student', 'quiz')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('mark_as_graded_passed', 'mark_as_graded_failed', 'reset_to_in_progress')

    def mark_as_graded_passed(self, request, queryset):
        updated = queryset.update(status='graded', passed=True)
        self.message_user(request, f"{updated} session(s) marked as graded and passed.")
    mark_as_graded_passed.short_description = 'Mark selected sessions as graded/passed'

    def mark_as_graded_failed(self, request, queryset):
        updated = queryset.update(status='graded', passed=False)
        self.message_user(request, f"{updated} session(s) marked as graded and failed.")
    mark_as_graded_failed.short_description = 'Mark selected sessions as graded/failed'

    def reset_to_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress', passed=None, score=None)
        self.message_user(request, f"{updated} session(s) reset to in progress.")
    reset_to_in_progress.short_description = 'Reset selected sessions to in progress'


class HardwareAssetAdmin(admin.ModelAdmin):
    list_display = ('asset_type', 'mac_address', 'serial_number', 'school', 'status', 'assigned_to', 'is_online')
    list_filter = ('asset_type', 'status', 'school', 'is_online')
    search_fields = ('mac_address', 'serial_number', 'device_id', 'assigned_to__first_name', 'assigned_to__last_name')
    raw_id_fields = ('school', 'assigned_to')
    readonly_fields = ('created_at', 'updated_at')


class LabSubmissionInline(admin.TabularInline):
    model = Lab_Submission
    extra = 0
    fields = ('student', 'status', 'grade', 'graded_by', 'graded_at')
    readonly_fields = ('graded_at',)


class LabProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'due_date', 'required_hardware')
    list_filter = ('module', 'required_hardware')
    search_fields = ('name', 'module__name', 'module__code')
    raw_id_fields = ('module',)
    inlines = (LabSubmissionInline,)
    readonly_fields = ('created_at', 'updated_at')


class LabSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'project', 'status', 'grade', 'graded_by', 'graded_at')
    list_filter = ('status', 'grade', 'project')
    search_fields = ('student__first_name', 'student__last_name', 'project__name', 'graded_by__first_name', 'graded_by__last_name')
    raw_id_fields = ('student', 'project', 'graded_by')
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(School, SchoolAdmin)
admin.site.register(Cohort, CohortAdmin)
admin.site.register(User_Profile, UserProfileAdmin)
admin.site.register(NavigationEvent, NavigationEventAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Parent, ParentAdmin)
admin.site.register(Instructor, InstructorAdmin)
admin.site.register(AttendanceSession, AttendanceSessionAdmin)
admin.site.register(AttendanceRecord)
admin.site.register(Module, ModuleAdmin)
admin.site.register(CBT_Quiz, CBTQuizAdmin)
admin.site.register(CBT_Question)
admin.site.register(CBT_Session, CBTSessionAdmin)
admin.site.register(HardwareAsset, HardwareAssetAdmin)
admin.site.register(Lab_Project, LabProjectAdmin)
admin.site.register(Lab_Submission, LabSubmissionAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(TransactionWebhookLog, TransactionWebhookLogAdmin)
