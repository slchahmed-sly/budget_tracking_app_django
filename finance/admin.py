from django.contrib import admin
from .models import Cycle,RecurringExpense, Expense, Income, Special

# Register your models here.

admin.site.register(Cycle)
admin.site.register(RecurringExpense)
admin.site.register(Expense)
admin.site.register(Income)
admin.site.register(Special)