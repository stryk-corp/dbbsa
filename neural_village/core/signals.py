import uuid

from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Student, Instructor, Parent, User_Profile, WaitlistEntry


def _ensure_allowed_domains(role):
    if role in ('school_admin', 'super_admin'):
        return 'admin.dbbsa.com,sys.neuralvillage.com,portal.lvh.me,lvh.me'
    return 'portal.lvh.me,lvh.me,dbbsa.com'


def _normalize_role(role_value):
    if not role_value:
        return 'student'
    normalized = role_value.strip().lower().replace(' ', '_')
    valid_roles = {choice[0] for choice in User_Profile.ROLE_CHOICES}
    return normalized if normalized in valid_roles else 'student'


def _generate_username(email):
    if not email or '@' not in email:
        return f'user_{uuid.uuid4().hex[:8]}'
    base_username = email.split('@')[0]
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exclude(email=email).exists():
        username = f"{base_username}{suffix}"
        suffix += 1
    return username


def _create_waitlist_portal_user(entry):
    username = _generate_username(entry.email)
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': entry.email}
    )

    if created:
        user.set_password('dbbsa')
        user.save()
    elif user.email != entry.email:
        user.email = entry.email
        user.save(update_fields=['email'])

    role = _normalize_role(entry.role_requested)
    profile = _ensure_profile(user, role)
    if not profile.digital_id:
        profile.digital_id = f'NV-{uuid.uuid4().hex[:8].upper()}'
    profile.save(update_fields=['digital_id'])

    if not entry.processed_at:
        entry.processed_at = timezone.now()

    return user


@receiver(pre_save, sender=WaitlistEntry)
def auto_provision_waitlist_user(sender, instance, **kwargs):
    if instance.status != 'APPROVED':
        return

    if not instance.pk:
        return

    try:
        previous = WaitlistEntry.objects.get(pk=instance.pk)
    except WaitlistEntry.DoesNotExist:
        previous_status = None
    else:
        previous_status = previous.status

    if previous_status == 'APPROVED':
        return

    _create_waitlist_portal_user(instance)


def _ensure_profile(user, role):
    defaults = {
        'role': role,
        'digital_id': f'NV-{uuid.uuid4().hex[:12].upper()}',
        'allowed_domains': _ensure_allowed_domains(role),
        'is_verified': True,
    }
    profile, _ = User_Profile.objects.get_or_create(user=user, defaults=defaults)
    updated = False
    if profile.role != role:
        profile.role = role
        updated = True
    if profile.allowed_domains != defaults['allowed_domains']:
        profile.allowed_domains = defaults['allowed_domains']
        updated = True
    if updated:
        profile.save(update_fields=['role', 'allowed_domains'])
    return profile


@receiver(post_save, sender=Student)
def sync_student_profile(sender, instance, created, **kwargs):
    if instance.user:
        profile = _ensure_profile(instance.user, 'student')
        if instance.cohort and instance.school != instance.cohort.school:
            instance.school = instance.cohort.school
            instance.save(update_fields=['school'])


@receiver(post_save, sender=Instructor)
def sync_instructor_profile(sender, instance, created, **kwargs):
    if instance.user:
        _ensure_profile(instance.user, 'instructor')


@receiver(post_save, sender=Parent)
def sync_parent_profile(sender, instance, created, **kwargs):
    if instance.user:
        _ensure_profile(instance.user, 'parent')


@receiver(post_save, sender=User_Profile)
def sync_user_staff_status(sender, instance, created, **kwargs):
    user = instance.user
    if instance.role in ('school_admin', 'super_admin') and not user.is_staff:
        user.is_staff = True
        user.save(update_fields=['is_staff'])
    if instance.role == 'super_admin' and not user.is_superuser:
        user.is_superuser = True
        user.save(update_fields=['is_superuser'])
