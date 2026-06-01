"""
DBBSA Core Models
Comprehensive data structure for DBBSA ecosystem

This follows a monolithic-first approach with clear internal separation of concerns:
- Schools manage their own cohorts, students, instructors
- Students belong to cohorts and are assigned hardware
- Parents can view multiple children
- Modules contain multiple quizzes/projects
- Hardware is tracked per-student for accountability
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class School(models.Model):
    """Partner schools in the DBBSA ecosystem"""
    TRACK_CHOICES = [
        ('primary', 'Primary (Ages 2-10)'),
        ('secondary', 'Secondary (Ages 11-17)'),
        ('both', 'Both Primary & Secondary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)  # e.g., "Shehu Giwa Academy"
    location = models.CharField(max_length=255)  # City, State
    partner_since = models.DateField(auto_now_add=True)
    primary_contact_email = models.EmailField()
    tracks_offered = models.CharField(max_length=20, choices=TRACK_CHOICES, default='both')
    student_capacity = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)
    
    # Compliance & Audit
    subeb_verified = models.BooleanField(default=False)
    subeb_verified_date = models.DateField(null=True, blank=True)
    hardware_inventory_verified = models.BooleanField(default=False)
    
    # Donation tracking
    total_donations_naira = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['subeb_verified']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.location})"


class Cohort(models.Model):
    """Groups of students within a school (e.g., "KNSB Pilot 2026")"""
    COHORT_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='cohorts')
    name = models.CharField(max_length=255)  # "KNSB Pilot 2026"
    track = models.CharField(max_length=20, choices=School.TRACK_CHOICES)
    status = models.CharField(max_length=20, choices=COHORT_STATUS, default='active')
    
    instructor = models.ForeignKey('Instructor', on_delete=models.SET_NULL, null=True, related_name='cohorts_taught')
    start_date = models.DateField()
    end_date = models.DateField()
    
    max_students = models.IntegerField(default=30)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('school', 'name')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.school.name} - {self.name}"
    
    @property
    def current_enrollment(self):
        return self.students.filter(is_active=True).count()


class User_Profile(models.Model):
    """Extended user profile for role-based access"""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('instructor', 'Instructor'),
        ('school_admin', 'School Administrator'),
        ('super_admin', 'Super Admin (DBBSA)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    digital_id = models.CharField(max_length=20, unique=True)  # e.g., "NV-KNSB-001"
    
    # Domain access control
    allowed_domains = models.CharField(
        max_length=255, 
        help_text="Comma-separated allowed domains: dbbsa.com, admin.dbbsa.com, sys.neuralvillage.com"
    )
    
    is_verified = models.BooleanField(default=False)
    requires_2fa = models.BooleanField(default=False)  # For school admins & super admin
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['digital_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"


class NavigationEvent(models.Model):
    """Track portal clicks, navigation, and instructor actions."""

    EVENT_TYPE_CHOICES = [
        ('page_view', 'Page View'),
        ('navigation', 'Navigation'),
        ('button_click', 'Button Click'),
        ('form_submit', 'Form Submit'),
        ('login', 'Login'),
        ('attendance_action', 'Attendance Action'),
        ('cohort_view', 'Cohort View'),
        ('school_view', 'School View'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='navigation_events')
    role = models.CharField(max_length=20, choices=User_Profile.ROLE_CHOICES, default='instructor')
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    target_model = models.CharField(max_length=64, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    target_label = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.event_type} - {self.target_label or self.target_model}"


class Student(models.Model):
    """Student records linked to schools and cohorts"""
    TRACK_CHOICES = [
        ('primary', 'Primary (Ages 2-10)'),
        ('secondary', 'Secondary (Ages 11-17)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, null=True, related_name='students')
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    track = models.CharField(max_length=20, choices=TRACK_CHOICES)
    
    # Academic tracking
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Brain Skills Score (aggregated from assessments)
    brain_skills_score = models.IntegerField(default=0)  # 0-100
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-enrollment_date']
        indexes = [
            models.Index(fields=['school', 'is_active']),
            models.Index(fields=['cohort']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.school.name})"


class Parent(models.Model):
    """Parent/Guardian records - can have multiple children"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    
    children = models.ManyToManyField(Student, related_name='parents')
    
    # Payment & Notification Preferences
    payment_method = models.CharField(max_length=50, blank=True)  # e.g., "paystack", "transfer"
    notifications_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Guardian: {self.first_name} {self.last_name}"


class Invoice(models.Model):
    GATEWAY_CHOICES = [
        ('PAYSTACK', 'Paystack'),
        ('REMITA', 'Remita'),
    ]
    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payer_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    payer_email = models.EmailField(blank=True, null=True, help_text='Email used for payment when payer is not yet a system user')
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=4500.00)
    currency = models.CharField(max_length=3, default='NGN')
    description = models.CharField(max_length=255, default='KNSB 2026 Term Tuition')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')
    due_date = models.DateField(default=timezone.now)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='PAYSTACK')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['payer_user']),
        ]

    def __str__(self):
        return f"Invoice {self.id} - {self.student} - {self.status}"


class WaitlistEntry(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('AWAITING_DETAILS', 'Awaiting Details'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PROVISIONED', 'Provisioned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    dob = models.DateField(null=True, blank=True)
    role_requested = models.CharField(max_length=32, blank=True)
    target_school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    payment_reference = models.CharField(max_length=150, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='waitlist_entries')
    temp_token = models.UUIDField(default=uuid.uuid4, editable=False)
    temp_token_expires = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['email']),
            models.Index(fields=['payment_reference']),
        ]

    def __str__(self):
        return f"WaitlistEntry {self.email} - {self.status}"


class TransactionWebhookLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='webhook_logs')
    gateway = models.CharField(max_length=20, choices=Invoice.GATEWAY_CHOICES)
    reference_code = models.CharField(max_length=150)
    payload_dump = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gateway']),
            models.Index(fields=['reference_code']),
        ]

    def __str__(self):
        return f"{self.gateway} webhook for Invoice {self.invoice.id}"


class Instructor(models.Model):
    """Instructor/Teacher records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='instructors')
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=255, blank=True)  # e.g., "Neurobiology", "CBT Administration"
    
    is_active = models.BooleanField(default=True)
    can_grade = models.BooleanField(default=True)
    can_deploy_cbt = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Instructor: {self.first_name} {self.last_name} ({self.school.name})"


class AttendanceSession(models.Model):
    """Attendance roll activated by the instructor for a cohort."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='attendance_sessions')
    instructor = models.ForeignKey('Instructor', on_delete=models.CASCADE, related_name='attendance_sessions')
    module = models.ForeignKey('Module', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Attendance for {self.cohort.name} ({self.get_status_display()})"

    @property
    def present_count(self):
        return self.attendance_records.filter(status='present').count()

    @property
    def student_count(self):
        return self.cohort.students.filter(is_active=True).count()


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='attendance_records')
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'student')
        ordering = ['recorded_at']

    def __str__(self):
        return f"{self.student} - {self.get_status_display()} ({self.session.cohort.name})"


class Module(models.Model):
    """STEM-G Curriculum Modules"""
    TRACK_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('both', 'Both'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)  # e.g., "NEU 101"
    name = models.CharField(max_length=255)  # e.g., "Basic Neuroscience"
    description = models.TextField()
    track = models.CharField(max_length=20, choices=TRACK_CHOICES)
    
    # Content & Learning Outcomes
    credits = models.IntegerField(default=3)
    duration_weeks = models.IntegerField(default=8)
    
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class CBT_Quiz(models.Model):
    """Computer-Based Test (CBT) Quizzes"""
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('drag_drop_3d', 'Drag & Drop 3D'),
        ('short_answer', 'Short Answer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes')
    name = models.CharField(max_length=255)  # e.g., "Synapses Quiz"
    
    duration_minutes = models.IntegerField(default=60)
    total_questions = models.IntegerField(default=1)
    passing_score = models.IntegerField(default=70)  # percentage
    
    # Auto-save & Token Refresh Strategy (CRITICAL for mid-test token expiration fix)
    auto_save_interval_seconds = models.IntegerField(default=30)
    token_refresh_before_expiry_seconds = models.IntegerField(default=300)  # Refresh 5 mins before expiry
    
    is_published = models.BooleanField(default=False)
    show_answers_after = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.module.code} - {self.name}"


class CBT_Question(models.Model):
    """Individual CBT questions"""
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('drag_drop_3d', 'Drag & Drop 3D'),
        ('short_answer', 'Short Answer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(CBT_Quiz, on_delete=models.CASCADE, related_name='questions')
    
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    
    # For 3D drag-drop: 3D model reference
    model_url = models.URLField(blank=True)  # Figma/3D model link
    
    correct_answer = models.JSONField()  # Flexible format for different question types
    point_value = models.IntegerField(default=1)
    
    order = models.IntegerField(default=0)  # Question sequence
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['quiz', 'order']
    
    def __str__(self):
        return f"Q{self.order}: {self.quiz.name}"


class CBT_Session(models.Model):
    """Student CBT test sessions with auto-save checkpoints"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='cbt_sessions')
    quiz = models.ForeignKey(CBT_Quiz, on_delete=models.CASCADE, related_name='sessions')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    last_auto_save = models.DateTimeField(null=True, blank=True)
    
    # Auto-save of answers (JSON format)
    auto_saved_answers = models.JSONField(default=dict)
    
    # Final submission
    final_answers = models.JSONField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    
    # Token management (for silent refresh)
    jwt_token = models.CharField(max_length=500, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('student', 'quiz')  # One session per quiz per student
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['student', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.quiz.name} ({self.status})"
    
    @property
    def time_remaining_minutes(self):
        """Calculate remaining time for the quiz"""
        if not self.start_time:
            return self.quiz.duration_minutes
        elapsed = (timezone.now() - self.start_time).total_seconds() / 60
        return max(0, self.quiz.duration_minutes - elapsed)
    
    @property
    def should_refresh_token(self):
        """Check if token should be silently refreshed"""
        if not self.token_expires_at:
            return False
        seconds_until_expiry = (self.token_expires_at - timezone.now()).total_seconds()
        return seconds_until_expiry < self.quiz.token_refresh_before_expiry_seconds


class HardwareAsset(models.Model):
    """iPad, OpenBCI, Laptop assignments"""
    ASSET_TYPE_CHOICES = [
        ('ipad', 'iPad (NeuroArt)'),
        ('openbci_kit', 'OpenBCI Hardware Kit'),
        ('laptop', 'Laptop (Core i7)'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Maintenance'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='hardware_assets')
    
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES)
    mac_address = models.CharField(max_length=17, unique=True)  # For iPads, laptops
    device_id = models.CharField(max_length=50, blank=True)  # For BCI kits
    serial_number = models.CharField(max_length=100)
    
    assigned_to = models.OneToOneField(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_hardware')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Tracking
    is_online = models.BooleanField(default=False)  # Last known connectivity status
    last_sync = models.DateTimeField(null=True, blank=True)
    
    # Override for instructors (if hardware offline but student needs to work)
    instructor_override_reason = models.TextField(blank=True)
    override_active_until = models.DateTimeField(null=True, blank=True)
    
    purchased_date = models.DateField()
    purchase_cost_naira = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'status']),
            models.Index(fields=['assigned_to']),
        ]
    
    def __str__(self):
        return f"{self.asset_type} ({self.mac_address}) - {self.status}"


class Lab_Project(models.Model):
    """NeuroArt or other lab submissions"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lab_projects')
    name = models.CharField(max_length=255)  # e.g., "NeuroArt: Synaptic Plasticity"
    
    description = models.TextField()
    due_date = models.DateField()
    
    required_hardware = models.CharField(max_length=50, blank=True)  # e.g., "ipad"
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.module.code} - {self.name}"


class Lab_Submission(models.Model):
    """Student lab submissions"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='lab_submissions')
    project = models.ForeignKey(Lab_Project, on_delete=models.CASCADE, related_name='submissions')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    submission_content_url = models.URLField(blank=True)  # Link to NeuroArt, file upload URL, etc.
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    grade = models.IntegerField(null=True, blank=True)  # 0-100
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('student', 'project')
        indexes = [
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student} - {self.project.name}"
