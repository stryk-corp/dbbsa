import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from neural_village.core.models import Invoice, TransactionWebhookLog
from neural_village.core.tasks import send_payment_receipt_email


def _verify_paystack_signature(request):
    received_signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
    if not received_signature:
        return False

    secret = settings.PAYSTACK_SECRET_KEY or ''
    computed = hmac.new(secret.encode('utf-8'), request.body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, received_signature)


@csrf_exempt
def payment_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Webhook endpoint only accepts POST requests.')

    if not _verify_paystack_signature(request):
        return HttpResponseBadRequest('Invalid signature.')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return HttpResponseBadRequest('Invalid JSON payload.')

    event = payload.get('event')
    data = payload.get('data', {})
    metadata = data.get('metadata', {}) if isinstance(data, dict) else {}
    invoice_id = metadata.get('invoice_id')

    if not invoice_id or event != 'charge.success':
        return JsonResponse({'status': 'ignored'})

    invoice = Invoice.objects.filter(id=invoice_id).first()
    if not invoice:
        return HttpResponseBadRequest('Invoice not found.')

    invoice.status = 'PAID'
    invoice.save(update_fields=['status'])

    TransactionWebhookLog.objects.create(
        invoice=invoice,
        gateway='PAYSTACK',
        reference_code=data.get('reference', ''),
        payload_dump=payload,
        processed_at=None,
    )

    try:
        send_payment_receipt_email.delay(str(invoice.id))
    except Exception:
        # Fallback to synchronous send if Celery is not available
        send_payment_receipt_email(str(invoice.id))

    return JsonResponse({'status': 'success'})
