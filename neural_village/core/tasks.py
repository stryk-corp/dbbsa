from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

try:
    from celery import shared_task
except ImportError:
    def shared_task(func):
        return func

from .models import Invoice


@shared_task
def send_payment_receipt_email(invoice_id):
    try:
        invoice = Invoice.objects.select_related('payer_user', 'student').get(id=invoice_id)
    except Invoice.DoesNotExist:
        return None

    recipient = invoice.payer_user.email
    if not recipient:
        return None

    subject = 'DBBSA Payment Receipt — KNSB Term Tuition'
    message = (
        f"Thank you for your payment.\n\n"
        f"Invoice ID: {invoice.id}\n"
        f"Student: {invoice.student.first_name} {invoice.student.last_name}\n"
        f"Amount: ₦{invoice.amount}\n"
        f"Status: {invoice.status}\n"
        f"Date: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Your payment has been received and your child is now cleared for the current KNSB term."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@dbbsa.com',
        [recipient],
        fail_silently=True,
    )
    return True
