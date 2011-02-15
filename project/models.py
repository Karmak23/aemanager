# -*- coding: utf-8 -*-
from decimal import Decimal
from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext
from contact.models import Contact
from core.models import OwnedObject
from django.db.models.signals import post_save, pre_save
from django.utils.formats import localize
from django.db.models.aggregates import Sum
from core.templatetags.htmltags import to_html
from django.conf import settings
import ho.pisa as pisa

class Contract(OwnedObject):
    customer = models.ForeignKey(Contact, verbose_name=_('Customer'), related_name="contracts")
    title = models.CharField(max_length=255, verbose_name=_('Title'))
    content = models.TextField(verbose_name=_('Content'))
    update_date = models.DateField(verbose_name=_('Update date'))

    def __unicode__(self):
        return self.title

    @staticmethod
    def get_substitution_map():
        substitution_map = {ugettext('reference'): '',
                            ugettext('customer'): '',
                            ugettext('customer_legal_form'): '',
                            ugettext('customer_street'): '',
                            ugettext('customer_zipcode'): '',
                            ugettext('customer_city'): '',
                            ugettext('customer_country'): '',
                            ugettext('customer_national_id'): '',
                            ugettext('customer_representative'): '',
                            ugettext('customer_representative_function'): '',
                            ugettext('firstname'): '',
                            ugettext('lastname'): '',
                            ugettext('street'): '',
                            ugettext('zipcode'): '',
                            ugettext('city'): '',
                            ugettext('country'): '',
                            ugettext('national_id'): '',
                            }

        return substitution_map

    def to_pdf(self, user, response):
        css_file = open("%s%s" % (settings.MEDIA_ROOT, "/css/pisa.css"), 'r')
        css = css_file.read()

        substitution_map = Contract.get_substitution_map()

        substitution_map[ugettext('customer')] = unicode(self.customer)
        substitution_map[ugettext('customer_legal_form')] = self.customer.legal_form
        substitution_map[ugettext('customer_street')] = self.customer.address.street
        substitution_map[ugettext('customer_zipcode')] = self.customer.address.zipcode
        substitution_map[ugettext('customer_city')] = self.customer.address.city
        substitution_map[ugettext('customer_country')] = unicode(self.customer.address.country)
        substitution_map[ugettext('customer_national_id')] = self.customer.company_id
        substitution_map[ugettext('customer_representative')] = self.customer.representative
        substitution_map[ugettext('customer_representative_function')] = self.customer.representative_function
        substitution_map[ugettext('firstname')] = user.first_name
        substitution_map[ugettext('lastname')] = user.last_name
        substitution_map[ugettext('street')] = user.get_profile().address.street
        substitution_map[ugettext('zipcode')] = user.get_profile().address.zipcode
        substitution_map[ugettext('city')] = user.get_profile().address.city
        substitution_map[ugettext('country')] = unicode(user.get_profile().address.country)
        substitution_map[ugettext('national_id')] = user.get_profile().company_id

        contract_content = "<h1>%s</h1>%s" % (self.title, self.content.replace('&nbsp;', ' '))

        for tag, value in substitution_map.items():
            contract_content = contract_content.replace('{{ %s }}' % (tag), value)

        pdf = pisa.pisaDocument(to_html(contract_content),
                                response,
                                default_css=css)
        return response

PROJECT_STATE_PROSPECT = 1
PROJECT_STATE_PROPOSAL_SENT = 2
PROJECT_STATE_PROPOSAL_ACCEPTED = 3
PROJECT_STATE_STARTED = 4
PROJECT_STATE_FINISHED = 5
PROJECT_STATE_CANCELED = 6
PROJECT_STATE = ((PROJECT_STATE_PROSPECT, _('Prospect')),
                 (PROJECT_STATE_PROPOSAL_SENT, _('Proposal sent')),
                 (PROJECT_STATE_PROPOSAL_ACCEPTED, _('Proposal accepted')),
                 (PROJECT_STATE_STARTED, _('Started')),
                 (PROJECT_STATE_FINISHED, _('Finished')),
                 (PROJECT_STATE_CANCELED, _('Canceled')),)

class Project(OwnedObject):
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    customer = models.ForeignKey(Contact, verbose_name=_('Customer'))
    state = models.IntegerField(choices=PROJECT_STATE, default=PROJECT_STATE_PROSPECT, verbose_name=_('State'))

    def __unicode__(self):
        return self.name

    def is_proposal_accepted(self):
        if self.state >= PROJECT_STATE_PROPOSAL_ACCEPTED:
            return True
        return False

class ProposalAmountError(Exception):
    pass

PROPOSAL_STATE_DRAFT = 1
PROPOSAL_STATE_SENT = 2
PROPOSAL_STATE_ACCEPTED = 3
PROPOSAL_STATE_BALANCED = 4
PROPOSAL_STATE_REFUSED = 5
PROPOSAL_STATE = ((PROPOSAL_STATE_DRAFT, _('Draft')),
                  (PROPOSAL_STATE_SENT, _('Sent')),
                  (PROPOSAL_STATE_ACCEPTED, _('Accepted')),
                  (PROPOSAL_STATE_BALANCED, _('Balanced')),
                  (PROPOSAL_STATE_REFUSED, _('Refused')))

class ProposalManager(models.Manager):
    def get_potential_sales(self, owner):
        amount_sum = self.filter(state__lte=PROPOSAL_STATE_SENT,
                                 owner=owner).exclude(project__state__gte=PROJECT_STATE_FINISHED).aggregate(sales=Sum('amount'))
        return amount_sum['sales'] or 0

    def get_proposals_to_send(self, owner):
        proposals = self.filter(state=PROPOSAL_STATE_DRAFT,
                                owner=owner).exclude(project__state__gte=PROJECT_STATE_FINISHED)
        return proposals

    def get_potential_duration(self, owner):
        quantity_sum = ProposalRow.objects.filter(proposal__state__lte=PROPOSAL_STATE_SENT,
                                                  owner=owner).exclude(proposal__project__state__gte=PROJECT_STATE_FINISHED).aggregate(quantity=Sum('quantity'))
        return quantity_sum['quantity'] or 0

class Proposal(OwnedObject):
    project = models.ForeignKey(Project)
    reference = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Reference'))
    state = models.IntegerField(choices=PROPOSAL_STATE, default=PROPOSAL_STATE_DRAFT, verbose_name=_('State'))
    amount = models.DecimalField(blank=True, null=True, max_digits=12, decimal_places=2, verbose_name=_('Amount'))
    begin_date = models.DateField(blank=True, null=True, verbose_name=_('Begin date'))
    end_date = models.DateField(blank=True, null=True, verbose_name=_('End date'))
    contract_content = models.TextField(blank=True, default="", verbose_name=_('Contract'))
    update_date = models.DateField(verbose_name=_('Update date'))
    expiration_date = models.DateField(blank=True, null=True, verbose_name=_('Expiration date'))

    objects = ProposalManager()

    def __unicode__(self):
        if self.begin_date and self.end_date:
            return _('Proposal %(reference)s from %(begin_date)s to %(end_date)s for %(project)s') % {'reference': self.reference,
                                                                                                      'begin_date': localize(self.begin_date),
                                                                                                      'end_date': localize(self.end_date),
                                                                                                      'project' : self.project}
        else:
            return _('Proposal %(reference)s for %(project)s') % {'reference': self.reference,
                                                                                                      'project' : self.project}

    def is_accepted(self):
        return self.state == PROPOSAL_STATE_ACCEPTED or self.state == PROPOSAL_STATE_BALANCED

    def get_next_states(self):
        if self.state == PROPOSAL_STATE_DRAFT:
            return (PROPOSAL_STATE[PROPOSAL_STATE_SENT - 1],)
        elif self.state == PROPOSAL_STATE_SENT:
            return (PROPOSAL_STATE[PROPOSAL_STATE_ACCEPTED - 1], PROPOSAL_STATE[PROPOSAL_STATE_REFUSED - 1])

        return ()

    def get_remaining_to_invoice(self):
        has_balancing_invoice = self.invoice_rows.filter(balance_payments=True).count()
        if has_balancing_invoice:
            return 0

        invoice_amount = self.invoice_rows.filter(invoice__state__gte=1).aggregate(amount=Sum('amount'))
        return self.amount - (invoice_amount['amount'] or 0)

    """
    Set amount equals to sum of proposal rows if none
    """
    def update_amount(self):
        amount = 0
        for row in self.proposal_rows.all():
            amount = amount + row.quantity * row.unit_price

        self.amount = amount
        invoicerow_sum = float(self.invoice_rows.all().aggregate(sum=Sum('amount'))['sum'] or 0)
        if float(self.amount) < invoicerow_sum :
            raise ProposalAmountError(ugettext("Proposal amount can't be less than sum of invoices"))
        self.save(user=self.owner)

    """
    Generate a PDF file for the proposal
    """
    def to_pdf(self, user, response):
        css_file = open("%s%s" % (settings.MEDIA_ROOT, "/css/pisa.css"), 'r')
        css = css_file.read()

        substitution_map = Contract.get_substitution_map()

        substitution_map[ugettext('reference')] = unicode(self.reference)
        substitution_map[ugettext('customer')] = unicode(self.project.customer)
        substitution_map[ugettext('customer_legal_form')] = self.project.customer.legal_form
        substitution_map[ugettext('customer_street')] = self.project.customer.address.street
        substitution_map[ugettext('customer_zipcode')] = self.project.customer.address.zipcode
        substitution_map[ugettext('customer_city')] = self.project.customer.address.city
        substitution_map[ugettext('customer_country')] = unicode(self.project.customer.address.country)
        substitution_map[ugettext('customer_national_id')] = self.project.customer.company_id
        substitution_map[ugettext('customer_representative')] = self.project.customer.representative
        substitution_map[ugettext('customer_representative_function')] = self.project.customer.representative_function
        substitution_map[ugettext('firstname')] = user.first_name
        substitution_map[ugettext('lastname')] = user.last_name
        substitution_map[ugettext('street')] = user.get_profile().address.street
        substitution_map[ugettext('zipcode')] = user.get_profile().address.zipcode
        substitution_map[ugettext('city')] = user.get_profile().address.city
        substitution_map[ugettext('country')] = unicode(user.get_profile().address.country)
        substitution_map[ugettext('national_id')] = user.get_profile().company_id

        contract_content = self.contract_content.replace('&nbsp;', ' ')

        for tag, value in substitution_map.items():
            contract_content = contract_content.replace('{{ %s }}' % (tag), value)

        pdf = pisa.pisaDocument(to_html(contract_content),
                                response,
                                default_css=css)
        return response

def update_project_state(sender, instance, created, **kwargs):
    proposal = instance
    project = proposal.project
    if project.state != PROJECT_STATE_STARTED:
        if proposal.state == PROPOSAL_STATE_SENT:
            project.state = PROJECT_STATE_PROPOSAL_SENT
        elif proposal.state == PROPOSAL_STATE_ACCEPTED:
            project.state = PROJECT_STATE_PROPOSAL_ACCEPTED

    try:
        project.save(user=proposal.owner)
    except:
        pass

post_save.connect(update_project_state, sender=Proposal)

ROW_CATEGORY_SERVICE = 1
ROW_CATEGORY_PRODUCT = 2
ROW_CATEGORY = ((ROW_CATEGORY_SERVICE, _('Service')),
                (ROW_CATEGORY_PRODUCT, _('Product')))

class Row(OwnedObject):
    label = models.CharField(max_length=255)
    category = models.IntegerField(choices=ROW_CATEGORY)
    quantity = models.DecimalField(max_digits=5, decimal_places=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        abstract = True

def update_row_amount(sender, instance, **kwargs):
    row = instance
    row.amount = Decimal(row.quantity) * Decimal(row.unit_price)

class ProposalRow(Row):
    proposal = models.ForeignKey(Proposal, related_name="proposal_rows")

def update_proposal_amount(sender, instance, created, **kwargs):
    row = instance
    proposal = row.proposal
    proposal.amount = proposal.proposal_rows.all().aggregate(sum=Sum('amount'))['sum'] or 0
    proposal.save(user=proposal.owner)

pre_save.connect(update_row_amount, sender=ProposalRow)
post_save.connect(update_proposal_amount, sender=ProposalRow)
