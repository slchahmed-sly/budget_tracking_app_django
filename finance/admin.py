from django.contrib import admin
from .models import Cycle, RecurringExpense, Entry, CheckIn, SavingsGoal, SavingsTransaction

admin.site.register(Cycle)
admin.site.register(RecurringExpense)
admin.site.register(Entry)
admin.site.register(CheckIn)
admin.site.register(SavingsGoal)
admin.site.register(SavingsTransaction)
