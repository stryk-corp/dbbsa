import json
from datetime import timedelta
from decimal import Decimal
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseBadRequest, HttpResponseServerError, JsonResponse

from neural_village.core.models import Invoice, WaitlistEntry, School


def _use_fake_payment():
    return (
        settings.DEBUG
        and getattr(settings, 'PAYSTACK_FAKE', False)
        and getattr(settings, 'PAYMENT_GATEWAY', '').upper() == 'PAYSTACK'
)


@require_http_methods(['GET'])
def apply_start(request):
    # Simple apply start page where applicant provides an email and chooses currency
    currencies = getattr(settings, 'SUPPORTED_CURRENCIES', ['NGN', 'USD'])
    context = {
        'currencies': currencies,
        'fee_ngn': getattr(settings, 'APPLICATION_FEE_NGN', 4500),
        'paystack_public_key': getattr(settings, 'PAYSTACK_PUBLIC_KEY', ''),
    }
    return render(request, 'apply/start.html', context)


@require_http_methods(['POST'])
def initialize_application_payment(request):
    email = request.POST.get('email')
    currency = request.POST.get('currency', 'NGN')
    if not email:
        return HttpResponseBadRequest('Email is required')

    amount_naira = Decimal(getattr(settings, 'APPLICATION_FEE_NGN', 4500))
    # Simple conversion — production should use a live FX provider
    rates = getattr(settings, 'EXCHANGE_RATES', {'NGN': 1, 'USD': Decimal('0.0025')})
    rate = Decimal(rates.get(currency, 1))
    amount = (
        amount_naira.quantize(Decimal('1.'))
        if currency == 'NGN'
        else (amount_naira * rate).quantize(Decimal('0.01'))
    )

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.POST.get('ajax') == '1'
    )

    # create an invoice for application fee (payer_user is null until account created)
    invoice = Invoice.objects.create(
        payer_user=None,
        payer_email=email,
        student=None,
        amount=amount,
        currency=currency,
        description='DBBSA Application Fee',
        status='UNPAID',
    )

    if _use_fake_payment():
        if is_ajax:
            return JsonResponse({'status': 'ok', 'invoice_id': invoice.id, 'reference': f'FAKE-{invoice.id}'})
        return redirect(f"{reverse('apply:apply_continue')}?invoice_id={invoice.id}&reference=FAKE-{invoice.id}")

    # Initialize Paystack
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        return HttpResponseServerError('Payment gateway is not configured. Please contact support.')

    if is_ajax:
        return JsonResponse({
            'status': 'ok',
            'invoice_id': invoice.id,
            'amount': int(amount * Decimal('100')),
            'currency': currency,
            'public_key': settings.PAYSTACK_PUBLIC_KEY,
        })

    payload = {
        'email': email,
        'amount': int(amount * Decimal('100')),
        'currency': currency,
        'metadata': {
            'invoice_id': str(invoice.id),
            'purpose': 'application',
            'applicant_email': email,
        },
        'callback_url': f"{settings.BASE_PUBLIC_URL}{reverse('apply:apply_continue')}",
    }

    try:
        resp = requests.post(
            f"{settings.PAYSTACK_API_BASE_URL}/transaction/initialize",
            json=payload,
            headers={'Authorization': f'Bearer {secret_key}'},
            timeout=15,
        )
        data = resp.json()
    except requests.exceptions.RequestException:
        return HttpResponseServerError('Unable to reach the payment provider. Please try again later.')
    except ValueError:
        return HttpResponseServerError('Invalid response from payment provider.')

    if resp.status_code != 200 or not data.get('status'):
        error_message = data.get('message') or 'Unable to initialize payment. Please check your payment details and try again.'
        return HttpResponseBadRequest(f'Paystack initialization failed: {error_message}')

    return redirect(data['data']['authorization_url'])


@require_http_methods(['GET'])
def apply_continue(request):
    # Paystack will redirect the user here after payment with query params
    reference = request.GET.get('reference')
    invoice_id = request.GET.get('invoice') or request.GET.get('invoice_id')

    # Verify payment with Paystack
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not reference and not invoice_id:
        return HttpResponseBadRequest('Missing reference')

    # If invoice_id present, fetch invoice and use metadata if available
    invoice = None
    if invoice_id:
        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            invoice = None

    if _use_fake_payment() and invoice_id:
        if invoice:
            invoice.status = 'PAID'
            invoice.save(update_fields=['status'])

        wait = WaitlistEntry.objects.create(
            email=invoice.payer_email if invoice else '',
            payment_reference=reference or f'FAKE-{invoice_id}',
            invoice=invoice,
            status='AWAITING_DETAILS',
        )
        return redirect(reverse('apply:apply_details', kwargs={'token': str(wait.temp_token)}))

    # verify with paystack using reference param if provided
    verify_url = f"{settings.PAYSTACK_API_BASE_URL}/transaction/verify/{reference}" if reference else None
    if verify_url:
        try:
            resp = requests.get(verify_url, headers={'Authorization': f'Bearer {secret_key}'}, timeout=15)
            data = resp.json()
        except requests.exceptions.RequestException:
            return HttpResponseServerError('Unable to reach the payment provider. Please try again later.')
        except ValueError:
            return HttpResponseServerError('Invalid response from payment provider.')

        if resp.status_code == 200 and data.get('status') and data.get('data', {}).get('status') == 'success':
            metadata = data['data'].get('metadata', {})
            inv_id = metadata.get('invoice_id')
            try:
                invoice = Invoice.objects.get(id=inv_id)
            except Invoice.DoesNotExist:
                invoice = None

            if invoice:
                invoice.status = 'PAID'
                invoice.save(update_fields=['status'])

            # create waitlist entry in awaiting details state
            wait = WaitlistEntry.objects.create(
                email=data['data'].get('customer', {}).get('email') or metadata.get('applicant_email'),
                payment_reference=data['data'].get('reference') or reference,
                invoice=invoice,
                status='AWAITING_DETAILS',
            )
            # redirect user to secure details entry
            return redirect(reverse('apply:apply_details', kwargs={'token': str(wait.temp_token)}))

    return HttpResponseBadRequest('Payment verification failed')


@require_http_methods(['GET', 'POST'])
def apply_details(request, token):
    try:
        wait = WaitlistEntry.objects.get(temp_token=token, status='AWAITING_DETAILS')
    except WaitlistEntry.DoesNotExist:
        return HttpResponseBadRequest('Invalid or expired token')

    if request.method == 'GET':
        schools = School.objects.filter(is_active=True)
        return render(request, 'apply/details.html', {'wait': wait, 'schools': schools})

    # POST — save applicant details
    full_name = request.POST.get('full_name')
    phone = request.POST.get('phone')
    dob = request.POST.get('dob')
    role = request.POST.get('role')
    school_id = request.POST.get('school_id')

    wait.full_name = full_name or wait.full_name
    wait.phone = phone or wait.phone
    if dob:
        try:
            wait.dob = timezone.datetime.fromisoformat(dob).date()
        except Exception:
            pass
    wait.role_requested = role or wait.role_requested
    if school_id:
        try:
            wait.target_school = School.objects.get(id=school_id)
        except Exception:
            pass
    wait.status = 'PENDING'
    wait.save()

    return render(request, 'apply/thankyou.html', {'wait': wait})


@require_http_methods(['GET', 'POST'])
def check_application(request, token=None):
    context = {}
    approval_code = token or request.POST.get('approval_code')
    if approval_code:
        try:
            wait = WaitlistEntry.objects.get(temp_token=approval_code)
        except WaitlistEntry.DoesNotExist:
            context['error'] = 'We could not find an application with that code. Please verify and try again.'
        else:
            context['wait'] = wait
            context['approval_code'] = str(wait.temp_token)
            context['approved'] = wait.status in ('APPROVED', 'PROVISIONED')
            context['rejected'] = wait.status == 'REJECTED'
            context['pending'] = wait.status in ('PENDING', 'AWAITING_DETAILS')
            context['expired'] = False
            context['show_portal_details'] = False
            if context['approved'] and wait.processed_at:
                expires_at = wait.processed_at + timedelta(days=30)
                context['expires_at'] = expires_at
                if timezone.now() > expires_at:
                    context['expired'] = True
                else:
                    context['show_portal_details'] = True
            user = None
            profile = None
            student = None
            if context.get('approved'):
                user = User.objects.filter(email=wait.email).first()
                if user:
                    profile = getattr(user, 'profile', None)
                    student = getattr(user, 'student_profile', None)
            context['user'] = user
            context['profile'] = profile
            context['student'] = student
    return render(request, 'apply/check.html', context)
