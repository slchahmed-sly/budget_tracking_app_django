from django import forms 
from . import models

class CycleForm(forms.ModelForm):
    class Meta:
        model = models.Cycle
        exclude = ['user']
        widgets = {
            'currency_symbol': forms.TextInput(attrs={'placeholder': 'e.g. TL, USD'}),
            'start': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'currency_symbol': 'Currency Name'
        }


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = models.RecurringExpense
        exclude = ['user']


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = models.Expense
        exclude = ['cycle']
        widgets = {
            # This is the Magic Line: Turn the dropdown into Radio Buttons
            'status': forms.RadioSelect, 
            'comment': forms.Textarea(attrs={'rows': 3}),
        }



class IncomeForm(forms.ModelForm):
    class Meta:
        model = models.Income
        exclude = ['cycle']
        widgets = {
            # This is the Magic Line: Turn the dropdown into Radio Buttons
            'status': forms.RadioSelect, 
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

class SpecialForm(forms.ModelForm):
    class Meta:
        model = models.Special
        exclude = ['cycle']
        widgets = {
            'type': forms.RadioSelect,
            'comment': forms.Textarea(attrs={'rows': 3}),
        }