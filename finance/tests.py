from datetime import date, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from . import budget, models

Entry = models.Entry


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pw-12345!')
        self.client.login(username='alice', password='pw-12345!')
        today = timezone.localdate()
        # Day 14 of a 31 day cycle: 18 days left including today
        self.cycle = models.Cycle.objects.create(
            user=self.user, start=today - timedelta(days=13), end=today + timedelta(days=17),
            title='Oct', currency_symbol='TL',
        )

    def entry(self, kind, amount, certainty=Entry.CERTAIN, done=False, **kwargs):
        e = Entry(cycle=self.cycle, kind=kind, title=kwargs.pop('title', kind), amount=amount,
                  certainty=certainty, **kwargs)
        e.set_done(done)
        e.save()
        return e


class SummaryTests(BaseTestCase):
    def test_free_money_is_certain_income_minus_certain_expenses(self):
        self.entry(Entry.INCOME, 20000, done=True)
        self.entry(Entry.EXPENSE, 9500, done=True)
        self.entry(Entry.EXPENSE, 4000)
        self.entry(Entry.INCOME, 3000, Entry.PROBABLE)
        self.entry(Entry.EXPENSE, 1200, Entry.UNCERTAIN)

        s = budget.summarize(self.cycle)
        self.assertEqual(s.total_days, 31)
        self.assertEqual(s.days_left, 18)
        self.assertEqual(s.free_money, 6500)
        self.assertEqual(s.pending_net, 1800)

    def test_without_checkin_allowance_does_not_grow_over_time(self):
        self.entry(Entry.INCOME, 3100)
        first = budget.summarize(self.cycle, today=self.cycle.start)
        later = budget.summarize(self.cycle, today=self.cycle.end - timedelta(days=2))
        self.assertEqual(first.per_day, 100)
        self.assertEqual(later.per_day, 100)

    def test_checkin_drives_free_money_left(self):
        self.entry(Entry.INCOME, 20000, done=True)
        self.entry(Entry.EXPENSE, 9500, done=True)
        self.entry(Entry.EXPENSE, 800)  # not paid yet
        models.CheckIn.objects.create(cycle=self.cycle, balance=6200)

        s = budget.summarize(self.cycle)
        self.assertEqual(s.free_left, 5400)
        self.assertEqual(s.per_day, 300)

    def test_paying_after_checkin_does_not_change_free_money(self):
        debt = self.entry(Entry.EXPENSE, 800)
        models.CheckIn.objects.create(cycle=self.cycle, balance=6200,
                                      created_at=timezone.now() - timedelta(hours=1))
        before = budget.summarize(self.cycle).free_left

        debt.set_done(True)
        debt.save()
        self.assertEqual(budget.summarize(self.cycle).free_left, before)

    def test_pace_flags_spending_too_fast(self):
        self.entry(Entry.INCOME, 3100, done=True)
        models.CheckIn.objects.create(cycle=self.cycle, balance=100)
        self.assertEqual(budget.summarize(self.cycle).pace, budget.TOO_FAST)


class EntryViewTests(BaseTestCase):
    def test_dashboard_renders(self):
        self.entry(Entry.INCOME, 20000, done=True, title='Salary')
        self.entry(Entry.EXPENSE, 1200, Entry.UNCERTAIN, title='Laptop repair')
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Salary')
        self.assertContains(response, 'Laptop repair')

    def test_dashboard_without_cycle_invites_to_start(self):
        self.cycle.delete()
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('start_cycle'))

    def test_add_entry(self):
        response = self.client.post(reverse('add_entry'), {
            'kind': 'income', 'title': 'Salary', 'amount': 20000, 'certainty': 'certain', 'is_done': 'on',
        })
        self.assertRedirects(response, reverse('home'))
        e = Entry.objects.get()
        self.assertTrue(e.is_done)
        self.assertIsNotNone(e.done_at)

    def test_edit_remembers_previous_amount(self):
        e = self.entry(Entry.EXPENSE, 800, title='Ali')
        self.client.post(reverse('edit_entry', args=[e.pk]), {
            'kind': 'expense', 'title': 'Ali', 'amount': 600, 'certainty': 'certain',
        })
        e.refresh_from_db()
        self.assertEqual((e.amount, e.previous_amount), (600, 800))

    def test_confirm_pending_entry(self):
        e = self.entry(Entry.INCOME, 3000, Entry.PROBABLE)
        self.client.post(reverse('confirm_entry', args=[e.pk]))
        e.refresh_from_db()
        self.assertEqual(e.certainty, Entry.CERTAIN)
        self.assertTrue(e.is_done)

    def test_toggle_done(self):
        e = self.entry(Entry.EXPENSE, 9500)
        self.client.post(reverse('toggle_entry_done', args=[e.pk]))
        e.refresh_from_db()
        self.assertTrue(e.is_done)

    def test_other_users_entries_are_404(self):
        other = User.objects.create_user('bob', password='pw-12345!')
        cycle = models.Cycle.objects.create(user=other, start=date(2026, 1, 1), end=date(2026, 1, 30), title='x')
        e = Entry.objects.create(cycle=cycle, kind=Entry.EXPENSE, title='x', amount=1)
        for name in ('edit_entry', 'delete_entry'):
            self.assertEqual(self.client.get(reverse(name, args=[e.pk])).status_code, 404)
        for name in ('toggle_entry_done', 'confirm_entry'):
            self.assertEqual(self.client.post(reverse(name, args=[e.pk])).status_code, 404)

    def test_recurring_views_return_404_for_missing_or_foreign_item(self):
        other = User.objects.create_user('bob', password='pw-12345!')
        foreign = models.RecurringExpense.objects.create(user=other, amount=10, purpose='Rent')
        for name in ('edit_recurring', 'delete_recurring'):
            for pk in (foreign.pk, 9999):
                self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404)

    def test_checkin(self):
        self.client.post(reverse('checkin'), {'balance': 6200})
        self.assertEqual(self.cycle.checkins.get().balance, 6200)

    @mock.patch('finance.ai_utils.get_financial_advice', return_value='ok')
    def test_ai_advice(self, advice):
        self.entry(Entry.INCOME, 20000)
        response = self.client.get(reverse('get_ai_advice'))
        self.assertEqual(response.json(), {'advice': 'ok'})


class CycleTests(BaseTestCase):
    def test_start_cycle_copies_recurring_and_planned_savings(self):
        models.RecurringExpense.objects.create(user=self.user, amount=9500, purpose='Rent')
        models.RecurringExpense.objects.create(user=self.user, amount=50, purpose='Old', is_active=False)
        goal = models.SavingsGoal.objects.create(user=self.user, name='Laptop', target=12000, monthly_amount=2000)

        self.client.post(reverse('start_cycle'), {
            'title': 'Nov', 'start': '2026-11-01', 'end': '2026-11-30', 'currency_symbol': 'TL',
            f'goal_{goal.pk}': '1500',
        })
        cycle = models.Cycle.objects.get(title='Nov')
        self.assertEqual(
            sorted((e.title, e.amount, e.goal_id) for e in cycle.entries.all()),
            [('Laptop', 1500, goal.pk), ('Rent', 9500, None)],
        )

    def test_end_before_start_is_rejected(self):
        response = self.client.post(reverse('start_cycle'), {
            'title': 'Bad', 'start': '2026-11-30', 'end': '2026-11-01', 'currency_symbol': 'TL',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(models.Cycle.objects.filter(title='Bad').exists())


class SavingsTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.goal = models.SavingsGoal.objects.create(user=self.user, name='Laptop', target=12000)

    def test_paid_savings_entry_moves_money_into_goal(self):
        e = self.entry(Entry.EXPENSE, 2000, goal=self.goal)
        self.client.post(reverse('toggle_entry_done', args=[e.pk]))
        self.assertEqual(self.goal.saved, 2000)

        self.client.post(reverse('edit_entry', args=[e.pk]), {
            'kind': 'expense', 'title': 'Laptop', 'amount': 2500, 'certainty': 'certain', 'is_done': 'on',
        })
        self.assertEqual(self.goal.saved, 2500)

        self.client.post(reverse('toggle_entry_done', args=[e.pk]))
        self.assertEqual(self.goal.saved, 0)

    def test_add_and_withdraw(self):
        self.client.post(reverse('goal_transfer', args=[self.goal.pk, 'in']), {'amount': 3000})
        self.client.post(reverse('goal_transfer', args=[self.goal.pk, 'out']), {'amount': 1000})
        self.assertEqual(self.goal.saved, 2000)
        kinds = sorted(self.cycle.entries.values_list('kind', 'amount'))
        self.assertEqual(kinds, [('expense', 3000), ('income', 1000)])

    def test_bad_direction_is_404(self):
        self.assertEqual(self.client.get(f'/savings/goal/{self.goal.pk}/sideways/').status_code, 404)

    def test_savings_page_renders(self):
        self.client.post(reverse('goal_transfer', args=[self.goal.pk, 'in']), {'amount': 3000})
        response = self.client.get(reverse('savings'))
        self.assertContains(response, 'Laptop')


class MigrationTests(TransactionTestCase):
    """Old Income/Expense/Special rows are carried over as entries."""

    def test_old_transactions_become_entries(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('finance', '0001_initial')])
        old = executor.loader.project_state([('finance', '0001_initial')]).apps

        user = old.get_model('auth', 'User').objects.create(username='old')
        cycle = old.get_model('finance', 'Cycle').objects.create(
            user_id=user.pk, start=date(2026, 9, 15), title='Sep', currency_symbol='TL')
        old.get_model('finance', 'Income').objects.create(cycle_id=cycle.pk, source='Salary', amount=20000, status='certain')
        old.get_model('finance', 'Income').objects.create(cycle_id=cycle.pk, source='Ghost', amount=None, status='probable', owe_me=True)
        old.get_model('finance', 'Expense').objects.create(cycle_id=cycle.pk, purpose='Rent', amount=9500, i_owe=True)
        old.get_model('finance', 'Special').objects.create(cycle_id=cycle.pk, title='Repair', amount=1200, type='expense')

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

        new_cycle = models.Cycle.objects.get(pk=cycle.pk)
        self.assertEqual(new_cycle.end, date(2026, 10, 14))
        self.assertEqual(
            sorted(new_cycle.entries.values_list('kind', 'title', 'amount', 'certainty', 'is_debt')),
            [
                ('expense', 'Rent', 9500, 'certain', True),
                ('expense', 'Repair', 1200, 'uncertain', False),
                ('income', 'Ghost', 0, 'probable', True),
                ('income', 'Salary', 20000, 'certain', False),
            ],
        )
