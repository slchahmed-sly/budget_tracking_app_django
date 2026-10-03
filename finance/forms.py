from django import forms
from django.utils.translation import gettext_lazy as _

from . import models


class CycleForm(forms.ModelForm):
    class Meta:
        model = models.Cycle
        fields = ['title', 'start', 'end', 'currency_symbol']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('e.g. October')}),
            'start': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'end': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'currency_symbol': forms.TextInput(attrs={'placeholder': _('e.g. TL, USD')}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start'), cleaned.get('end')
        if start and end and end < start:
            self.add_error('end', _('The end date must be after the start date.'))
        return cleaned


class EntryForm(forms.ModelForm):
    class Meta:
        model = models.Entry
        fields = ['kind', 'title', 'amount', 'certainty', 'is_done', 'is_debt', 'comment']
        widgets = {
            'kind': forms.RadioSelect,
            'certainty': forms.RadioSelect,
            'amount': forms.NumberInput(attrs={'inputmode': 'numeric', 'min': 0}),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }


class CheckInForm(forms.ModelForm):
    class Meta:
        model = models.CheckIn
        fields = ['balance']
        widgets = {
            'balance': forms.NumberInput(attrs={'inputmode': 'numeric', 'autofocus': True}),
        }


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = models.RecurringExpense
        fields = ['purpose', 'amount', 'is_active']
        widgets = {
            'amount': forms.NumberInput(attrs={'inputmode': 'numeric', 'min': 0}),
        }


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = models.SavingsGoal
        fields = ['name', 'target', 'monthly_amount', 'deadline']
        widgets = {
            'target': forms.NumberInput(attrs={'inputmode': 'numeric', 'min': 0}),
            'monthly_amount': forms.NumberInput(attrs={'inputmode': 'numeric', 'min': 0}),
            'deadline': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }


class TransferForm(forms.Form):
    amount = forms.IntegerField(
        label=_('Amount'), min_value=1,
        widget=forms.NumberInput(attrs={'inputmode': 'numeric', 'autofocus': True}),
    )
