from django.test import TestCase
from contact.models import Contact, CONTACT_TYPE_PERSON, Address
from django.core.urlresolvers import reverse

class ContactPermissionTest(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        self.client.login(username='test', password='test')
        address1 = Address.objects.create(street="3 rue de la paix",
                                          zipcode="75000",
                                          city="Paris",
                                          country=None,
                                          owner_id=1)
        address2 = Address.objects.create(street="4 rue de la paix",
                                          zipcode="75000",
                                          city="Paris",
                                          owner_id=2)
        self.contact1 = Contact.objects.create(contact_type=CONTACT_TYPE_PERSON,
                                               name="contact1",
                                               firstname="first name",
                                               email="test1@test.com",
                                               address=address1,
                                               owner_id=1)
        self.contact2 = Contact.objects.create(contact_type=CONTACT_TYPE_PERSON,
                                               name="contact2",
                                               firstname="first name",
                                               email="test2@test.com",
                                               address=address2,
                                               owner_id=2)

    def testContactSearch(self):
        response = self.client.get(reverse("contact_search"))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(set(response.context['contacts'].object_list.all()), set([self.contact1]))

    def testContactDetail(self):
        response = self.client.get(reverse("contact_detail", kwargs={'id': self.contact2.id}))
        self.assertEquals(response.status_code, 404)

    def testContactDelete(self):
        response = self.client.get(reverse("contact_delete", kwargs={'id': self.contact2.id}))
        self.assertEquals(response.status_code, 404)
        response = self.client.post(reverse("contact_delete", kwargs={'id': self.contact2.id}))
        self.assertEquals(response.status_code, 404)

    def testContactAdd(self):
        """
        Nothing to test
        """
        pass

    def testContactEdit(self):
        response = self.client.get(reverse("contact_edit", kwargs={'id': self.contact2.id}))
        self.assertEquals(response.status_code, 404)
        response = self.client.post(reverse("contact_edit", kwargs={'id': self.contact2.id}),
                                    {'name': 'test modify'})
        self.assertEquals(response.status_code, 404)

class ContactTest(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        self.client.login(username='test', password='test')

    def testBug95(self):
        """
        Company id is mandatory for company contact
        """
        response = self.client.post(reverse('contact_add'),
                                    {'contact-name': 'Customer',
                                     'contact-contact_type': '2',
                                     'contact-company_id':'',
                                     'phonenumber_set-TOTAL_FORMS': '1',
                                     'phonenumber_set-INITIAL_FORMS': '0',
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75000',
                                     'address-city': 'Paris'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.context['contactForm'].errors), 1)

        response = self.client.post(reverse('contact_add'),
                                    {'contact-name': 'Customer',
                                     'contact-contact_type': '1',
                                     'contact-company_id':'',
                                     'phonenumber_set-TOTAL_FORMS': '1',
                                     'phonenumber_set-INITIAL_FORMS': '0',
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75000',
                                     'address-city': 'Paris'})
        self.assertEquals(response.status_code, 302)
