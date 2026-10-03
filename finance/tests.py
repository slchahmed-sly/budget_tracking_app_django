from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import models


class BugFixTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pw-12345!')
        self.client.login(username='alice', password='pw-12345!')
        self.cycle = models.Cycle.objects.create(
            user=self.user, start=date.today(), title='Oct', currency_symbol='EUR'
        )

    def test_recurring_views_return_404_for_missing_or_foreign_item(self):
        other = User.objects.create_user('bob', password='pw-12345!')
        foreign = models.RecurringExpense.objects.create(user=other, amount=10, purpose='Rent')
        for name in ('edit_recurring', 'delete_recurring'):
            for pk in (foreign.pk, 9999):
                self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404)

    def test_invalid_add_forms_keep_currency(self):
        for name in ('add_income', 'add_expense', 'add_special'):
            response = self.client.post(reverse(name), {})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['cycle_currency'], 'EUR')

    def test_invalid_edit_forms_keep_currency(self):
        income = models.Income.objects.create(cycle=self.cycle, amount=5, source='Job')
        expense = models.Expense.objects.create(cycle=self.cycle, amount=5, purpose='Food')
        special = models.Special.objects.create(cycle=self.cycle, amount=5, title='Gift')
        for name, obj in (('edit_income', income), ('edit_expense', expense), ('edit_special', special)):
            response = self.client.post(reverse(name, args=[obj.pk]), {})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['cycle_currency'], 'EUR')

    @mock.patch('finance.ai_utils.get_financial_advice', return_value='ok')
    def test_ai_advice_handles_income_without_amount(self, advice):
        models.Income.objects.create(cycle=self.cycle, amount=None, source='Maybe', status='uncertain', owe_me=True)
        models.Income.objects.create(cycle=self.cycle, amount=100, source='Job', status='probable', owe_me=True)
        response = self.client.get(reverse('get_ai_advice'))
        self.assertEqual(response.status_code, 200)
        context = advice.call_args.args[0]
        self.assertEqual(context['uncertain_total'], 100)
        self.assertEqual(context['debt_total'], 100)
