from decimal import Decimal
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from neural_village.auth.decorators import role_required
from neural_village.core.models import Invoice


def _get_or_create_parent(request):
    return getattr(request.user, 'parent_profile', None)


def _paystack_initialize_payment(invoice, email):
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        raise RuntimeError('PAYSTACK_SECRET_KEY is not configured.')

    payload = {
        'email': email,
        'amount': int(invoice.amount * Decimal('100')),
        'currency': invoice.currency,
        'metadata': {
            'invoice_id': str(invoice.id),
            'payer_user_id': str(invoice.payer_user.id),
        },
        'callback_url': f"{settings.BASE_PUBLIC_URL}{reverse('parent:financials')}",
        'description': invoice.description,
    }

    response = requests.post(
        f"{settings.PAYSTACK_API_BASE_URL}/transaction/initialize",
        json=payload,
        headers={
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        },
        timeout=15,
    )
    response_data = response.json()
    if response.status_code != 200 or not response_data.get('status'):
        message = response_data.get('message', 'Unable to initialize payment')
        raise RuntimeError(f'Paystack initialization failed: {message}')

    return response_data['data']['authorization_url']


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


@role_required('parent')
def financials(request):
    parent = _get_or_create_parent(request)
    if not parent:
        return redirect('parent:dashboard')

    children = parent.children.select_related('school', 'cohort').all()
    invoices = []
    today = timezone.now().date()

    for child in children:
        invoice = Invoice.objects.filter(student=child, payer_user=request.user, status='UNPAID').order_by('due_date').first()
        if not invoice:
            invoice = Invoice.objects.create(
                payer_user=request.user,
                student=child,
                amount=Decimal('4500.00'),
                currency='NGN',
                description='KNSB 2026 Term Tuition',
                status='UNPAID',
                due_date=today + timezone.timedelta(days=14),
            )
        invoices.append(invoice)

    total_due = sum(invoice.amount for invoice in invoices)
    context = {
        'welcome_name': request.user.first_name or request.user.username,
        'invoices': invoices,
        'total_due': total_due,
        'fee_label': '₦4,500 termly tuition',
        'gateway_name': 'Paystack',
    }
    return render(request, 'parent/financials.html', context)


@role_required('parent')
@require_POST
def initialize_payment(request):
    invoice_id = request.POST.get('invoice_id')
    if not invoice_id:
        return redirect('parent:financials')

    invoice = Invoice.objects.filter(id=invoice_id, payer_user=request.user).first()
    if not invoice:
        return redirect('parent:financials')

    try:
        authorization_url = _paystack_initialize_payment(invoice, request.user.email)
        return redirect(authorization_url)
    except Exception as exc:
        context = {
            'error': str(exc),
            'welcome_name': request.user.first_name or request.user.username,
            'invoices': [invoice],
            'total_due': invoice.amount,
            'fee_label': '₦4,500 termly tuition',
            'gateway_name': 'Paystack',
        }
        return render(request, 'parent/financials.html', context)
