import uuid

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Student, Instructor, Parent, User_Profile


def _ensure_allowed_domains(role):
    if role in ('school_admin', 'super_admin'):
        return 'admin.dbbsa.com,sys.neuralvillage.com,portal.lvh.me,lvh.me'
    return 'portal.lvh.me,lvh.me,dbbsa.com'


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
