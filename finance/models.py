from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Cycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cycles')
    start = models.DateField(_('Start date'))
    end = models.DateField(_('End date'))
    title = models.CharField(_('Title'), max_length=100)
    currency_symbol = models.CharField(_('Currency'), max_length=10, default="TL")

    class Meta:
        ordering = ['-start', '-pk']

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    @property
    def total_days(self):
        return max((self.end - self.start).days + 1, 1)


class RecurringExpense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_expenses')
    amount = models.PositiveIntegerField(_('Amount'), blank=True, null=True)
    purpose = models.CharField(_('Purpose'), max_length=100)
    is_active = models.BooleanField(_('Active'), default=True)

    def __str__(self):
        return f'{self.purpose}: {self.amount} ({self.user.username})'


class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(_('Name'), max_length=100)
    target = models.PositiveIntegerField(_('Target'))
    monthly_amount = models.PositiveIntegerField(_('Amount per cycle'), default=0)
    deadline = models.DateField(_('Deadline'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.name} ({self.user.username})'

    @property
    def saved(self):
        return self.transactions.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def percent(self):
        if not self.target:
            return 0
        return max(0, min(100, round(self.saved * 100 / self.target)))


class Entry(models.Model):
    """
    One line of a cycle's plan: money coming in or going out.
    Certain entries make up the plan; probable/uncertain ones are only
    counted in the "if pending comes through" numbers.
    """
    INCOME = 'income'
    EXPENSE = 'expense'
    KIND_CHOICES = [
        (INCOME, _('Income')),
        (EXPENSE, _('Expense')),
    ]

    CERTAIN = 'certain'
    PROBABLE = 'probable'
    UNCERTAIN = 'uncertain'
    CERTAINTY_CHOICES = [
        (CERTAIN, _('Certain')),
        (PROBABLE, _('Probable')),
        (UNCERTAIN, _('Uncertain')),
    ]

    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='entries')
    kind = models.CharField(_('Type'), max_length=10, choices=KIND_CHOICES, default=EXPENSE)
    title = models.CharField(_('Title'), max_length=100)
    amount = models.PositiveIntegerField(_('Amount'), default=0)
    certainty = models.CharField(_('How sure is it?'), max_length=10, choices=CERTAINTY_CHOICES, default=CERTAIN)
    # Received (income) or paid (expense)
    is_done = models.BooleanField(_('Done'), default=False)
    done_at = models.DateTimeField(null=True, blank=True)
    # I owe this money (expense) / someone owes me (income)
    is_debt = models.BooleanField(_('Debt'), default=False)
    previous_amount = models.PositiveIntegerField(null=True, blank=True)
    comment = models.TextField(_('Note'), blank=True)
    goal = models.ForeignKey(
        SavingsGoal, on_delete=models.SET_NULL, null=True, blank=True, related_name='entries'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-amount', 'pk']
        verbose_name_plural = 'entries'

    def __str__(self):
        return f'{self.title}: {self.signed_amount}'

    @property
    def is_income(self):
        return self.kind == self.INCOME

    @property
    def is_certain(self):
        return self.certainty == self.CERTAIN

    @property
    def signed_amount(self):
        return self.amount if self.is_income else -self.amount

    def set_done(self, done):
        if done and not self.is_done:
            self.done_at = timezone.now()
        elif not done:
            self.done_at = None
        self.is_done = done

    def sync_savings(self):
        """Keep the goal's savings transaction in line with this entry.

        Money going out of the balance into a goal is a transfer in;
        money coming into the balance from a goal is a withdrawal.
        """
        existing = SavingsTransaction.objects.filter(entry=self).first()
        if self.goal_id and self.is_done and self.is_certain:
            amount = -self.signed_amount
            date = timezone.localdate(self.done_at) if self.done_at else timezone.localdate()
            if existing:
                existing.goal_id = self.goal_id
                existing.amount = amount
                existing.save(update_fields=['goal', 'amount'])
            else:
                SavingsTransaction.objects.create(goal_id=self.goal_id, amount=amount, date=date, entry=self)
        elif existing:
            existing.delete()


class CheckIn(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='checkins')
    balance = models.IntegerField(_('Current balance'))
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return f'{self.balance} @ {self.created_at:%Y-%m-%d}'


class SavingsTransaction(models.Model):
    goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='transactions')
    # Positive: money added to the goal. Negative: money taken out.
    amount = models.IntegerField()
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=200, blank=True)
    entry = models.OneToOneField(
        Entry, on_delete=models.CASCADE, null=True, blank=True, related_name='savings_transaction'
    )

    class Meta:
        ordering = ['-date', '-pk']

    def __str__(self):
        return f'{self.goal.name}: {self.amount}'
