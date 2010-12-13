from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _
from core.forms import UserForm
from autoentrepreneur.forms import UserProfileForm
from contact.forms import AddressForm
from django.db.transaction import commit_on_success
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from accounts.models import Expense
import time
import datetime

@login_required
def index(request):
    user = request.user
    paid = user.get_profile().get_paid_sales()
    waiting = user.get_profile().get_waiting_invoices()
    to_be_invoiced = user.get_profile().get_to_be_invoiced()
    limit = user.get_profile().get_sales_limit()
    late_invoices = user.get_profile().get_late_invoices()
    invoices_to_send = user.get_profile().get_invoices_to_send()
    potential = user.get_profile().get_potential_sales()
    duration = user.get_profile().get_potential_duration()
    proposals_to_send = user.get_profile().get_proposals_to_send()
    begin_date, end_date = user.get_profile().get_period_for_tax()
    amount_paid_for_tax = user.get_profile().get_paid_sales_for_period(begin_date, end_date)
    tax_rate = user.get_profile().get_tax_rate()
    amount_to_pay = float(amount_paid_for_tax) * float(tax_rate) / 100

    invoices = user.get_profile().get_paid_invoices()
    sales_progression = []
    last = 0.0
    for invoice in invoices:
        amount = last + float(invoice.amount)
        sales_progression.append([int(time.mktime(invoice.paid_date.timetuple())*1000), amount])
        last = amount

    expenses_progression = []
    last = 0.0
    for expense in Expense.objects.all().order_by(('date')):
        amount = last + float(expense.amount)
        expenses_progression.append([int(time.mktime(expense.date.timetuple())*1000), amount])
        last = amount

    pay_date = None
    if end_date:
        year = end_date.year
        if end_date.year == 12:
            year = end_date.year + 1
        pay_date = datetime.date(year,
                                 (end_date.month + 2) % 12 or 12,
                                 1) - datetime.timedelta(1)

    sales = {'paid': paid,
             'waiting': waiting,
             'to_be_invoiced': to_be_invoiced,
             'total': paid + waiting + to_be_invoiced,
             'limit': limit,
             'remaining': limit - paid - waiting - to_be_invoiced}

    invoices = {'late': late_invoices,
                'to_send': invoices_to_send}

    percentage_of_remaining = 0
    if sales['remaining']:
        percentage_of_remaining = potential * 100 / sales['remaining']

    average_unit_price = 0
    if duration:
        average_unit_price = potential / duration

    prospects = {'potential_sales': potential,
                 'percentage_of_remaining': percentage_of_remaining,
                 'duration': duration,
                 'average_unit_price': average_unit_price,
                 'proposals_to_send': proposals_to_send}

    taxes = {'period_begin': begin_date,
             'period_end': end_date,
             'paid_sales_for_period': amount_paid_for_tax,
             'tax_rate': tax_rate,
             'amount_to_pay': amount_to_pay,
             'tax_due_date': pay_date}

    charts = {'sales_progression':simplejson.dumps(sales_progression),
              'expenses_progression':simplejson.dumps(expenses_progression)}

    return render_to_response('core/index.html',
                              {'active': 'dashboard',
                               'title': _('Dashboard'),
                               'sales': sales,
                               'invoices': invoices,
                               'prospects': prospects,
                               'taxes': taxes,
                               'charts': charts},
                              context_instance=RequestContext(request))

@login_required
@commit_on_success
def settings_edit(request):
    user = request.user
    profile = user.get_profile()
    address = profile.address

    if request.method == 'POST':
        userform = UserForm(request.POST, prefix="user", instance=user)
        profileform = UserProfileForm(request.POST, prefix="profile", instance=profile)
        addressform = AddressForm(request.POST, prefix="address", instance=address)

        if userform.is_valid() and profileform.is_valid() and addressform.is_valid():
            userform.save()
            profileform.save()
            address = addressform.save(commit=False)
            address.save(user=user)
            messages.success(request, _('Your settings have been updated successfully'))
            return redirect(reverse('settings_edit'))
        else:
            messages.error(request, _('Data provided are invalid'))
    else:
        userform = UserForm(prefix="user", instance=user)
        profileform = UserProfileForm(prefix="profile", instance=profile)
        addressform = AddressForm(prefix="address", instance=address)

    return render_to_response('core/settings_edit.html',
                              {'active': 'account',
                               'title': _('Settings'),
                               'userform': userform,
                               'profileform': profileform,
                               'addressform': addressform},
                              context_instance=RequestContext(request))