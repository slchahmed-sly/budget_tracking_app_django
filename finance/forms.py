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
        fields = '__all__'