from django.contrib import admin
from .models import Cycle, RecurringExpense, Entry, SavingsGoal, SavingsTransaction

admin.site.register(Cycle)
admin.site.register(RecurringExpense)
admin.site.register(Entry)
admin.site.register(SavingsGoal)
admin.site.register(SavingsTransaction)
