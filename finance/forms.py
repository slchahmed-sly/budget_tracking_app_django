from django import forms 
from . import models

class CycleForm(forms.ModelForm):
    class Meta:
        model = models.Cycle
        fields = '__all__'


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = models.RecurringExpense
        fields = '__all__'


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = models.Expense
        fields = '__all__'



class IncomeForm(forms.ModelForm):
    class Meta:
        model = models.Income
        fields = '__all__'

class SpecialForm(forms.ModelForm):
    class Meta:
        model = models.Special
        fields = '__all__'