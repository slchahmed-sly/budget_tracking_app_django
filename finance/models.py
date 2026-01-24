from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

STATUS_CHOICES = [
    ('certain', 'Certain (Green)'),
    ('probable', 'Probable (Yellow)'),
    ('uncertain', 'Uncertain (Red)'),
]


class Cycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cycles')
    start  = models.DateField()
    title = models.CharField(max_length=100)
    currency_symbol = models.CharField(max_length=10, default="TL")

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class RecurringExpense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_expenses')
    amount = models.PositiveIntegerField(blank=True, null=True)
    purpose = models.CharField(max_length = 100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.purpose}: {self.amount} ({self.user.username})'

class BaseTransaction(models.Model):
    """
    This model will not create a database table. 
    It is just a template for other models.
    """
    amount = models.PositiveIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)
    
    cycle = models.ForeignKey(
        Cycle, 
        on_delete=models.CASCADE, 
        related_name='%(class)s' 
    )

    class Meta:
        abstract = True  



class Expense(BaseTransaction):
    purpose = models.CharField(max_length=100)
    i_owe = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.purpose}: {self.amount}'


class Income(BaseTransaction):
    source = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='certain')
    owe_me = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.source}: {self.amount}'


class Special(BaseTransaction):
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense')
    ]
    title = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='expense')
    i_owe = models.BooleanField(default=False)
    owe_me = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.title}: {self.amount}'
