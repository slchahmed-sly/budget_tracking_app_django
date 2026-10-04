from datetime import timedelta

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView

from . import ai_utils, budget, forms, models


# Helper function to get active cycle
def get_active_cycle(user):
    return models.Cycle.objects.filter(user=user).first()


def savings_total(user):
    return models.SavingsTransaction.objects.filter(goal__user=user).aggregate(total=Sum('amount'))['total'] or 0


class DashBoardView(LoginRequiredMixin, View):
    def get(self, request):
        cycle = get_active_cycle(request.user)
        if not cycle:
            return render(request, 'finance/dashboard.html', {'cycle': None})

        summary = budget.summarize(cycle)
        cycle_saved = models.SavingsTransaction.objects.filter(
            goal__user=request.user, entry__cycle=cycle
        ).aggregate(total=Sum('amount'))['total'] or 0
        return render(request, 'finance/dashboard.html', {
            'cycle': cycle,
            's': summary,
            'savings_total': savings_total(request.user),
            'goal_count': request.user.savings_goals.count(),
            'cycle_saved': cycle_saved,
        })


# --- Entries (income and expenses) ---

class AddEntryView(LoginRequiredMixin, View):
    def get(self, request):
        cycle = get_active_cycle(request.user)
        if not cycle:
            return redirect('start_cycle')
        initial = {
            'kind': request.GET.get('kind', models.Entry.EXPENSE),
            'certainty': request.GET.get('certainty', models.Entry.CERTAIN),
        }
        form = forms.EntryForm(initial=initial)
        return render(request, 'finance/entry_form.html', {'form': form, 'cycle': cycle})

    def post(self, request):
        cycle = get_active_cycle(request.user)
        if not cycle:
            return redirect('start_cycle')
        form = forms.EntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.cycle = cycle
            entry.is_done = False
            entry.set_done(form.cleaned_data['is_done'])
            entry.save()
            return redirect('home')
        return render(request, 'finance/entry_form.html', {'form': form, 'cycle': cycle})


class EditEntryView(LoginRequiredMixin, View):
    def get(self, request, pk):
        entry = get_object_or_404(models.Entry, cycle__user=request.user, pk=pk)
        form = forms.EntryForm(instance=entry)
        return render(request, 'finance/entry_form.html', self.context(entry, form))

    def post(self, request, pk):
        entry = get_object_or_404(models.Entry, cycle__user=request.user, pk=pk)
        old_amount, was_done = entry.amount, entry.is_done
        form = forms.EntryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save(commit=False)
            if entry.amount != old_amount:
                entry.previous_amount = old_amount
            entry.is_done = was_done
            entry.set_done(form.cleaned_data['is_done'])
            entry.save()
            entry.sync_savings()
            return redirect('home')
        return render(request, 'finance/entry_form.html', self.context(entry, form))

    def context(self, entry, form):
        s = budget.summarize(entry.cycle)
        # Data for the live "what does this change do to my day" preview
        return {
            'form': form,
            'entry': entry,
            'cycle': entry.cycle,
            'impact': {
                'perDay': s.per_day,
                'freeMoney': s.free_money,
                'daysLeft': s.days_left,
                'kind': entry.kind,
                'certainty': entry.certainty,
                'amount': entry.amount,
            },
        }


class DeleteEntryView(LoginRequiredMixin, View):
    def get(self, request, pk):
        entry = get_object_or_404(models.Entry, cycle__user=request.user, pk=pk)
        return render(request, 'finance/confirm_delete.html', {'obj': entry, 'cancel_url': 'home'})

    def post(self, request, pk):
        entry = get_object_or_404(models.Entry, cycle__user=request.user, pk=pk)
        entry.delete()
        return redirect('home')


class ToggleEntryDoneView(LoginRequiredMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(models.Entry, cycle__user=request.user, pk=pk)
        entry.set_done(not entry.is_done)
        entry.save()
        entry.sync_savings()
        return redirect('home')


class ConfirmEntryView(LoginRequiredMixin, View):
    """A probable/uncertain entry turned out to be real."""
    def post(self, request, pk):
        entry = get_object_or_404(models.Entry, cycle__user=request.user, pk=pk)
        entry.certainty = models.Entry.CERTAIN
        entry.set_done(True)
        entry.save()
        entry.sync_savings()
        return redirect('home')


# --- Cycles ---

class StartCycleView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        previous = get_active_cycle(request.user)
        form = forms.CycleForm(initial={
            'start': today,
            'end': today + timedelta(days=29),
            'currency_symbol': previous.currency_symbol if previous else 'TL',
        })
        return render(request, 'finance/cycle_form.html', self.context(request, form))

    def post(self, request):
        form = forms.CycleForm(request.POST)
        if not form.is_valid():
            return render(request, 'finance/cycle_form.html', self.context(request, form))

        cycle = form.save(commit=False)
        cycle.user = request.user
        cycle.save()
        for recurring in request.user.recurring_expenses.filter(is_active=True):
            models.Entry.objects.create(
                cycle=cycle, kind=models.Entry.EXPENSE, title=recurring.purpose, amount=recurring.amount or 0,
            )
        for goal in request.user.savings_goals.all():
            try:
                amount = int(request.POST.get(f'goal_{goal.pk}') or 0)
            except ValueError:
                amount = 0
            if amount > 0:
                models.Entry.objects.create(
                    cycle=cycle, kind=models.Entry.EXPENSE, title=goal.name, amount=amount, goal=goal,
                )
        return redirect('home')

    def context(self, request, form):
        return {
            'form': form,
            'is_new': True,
            'recurring': request.user.recurring_expenses.filter(is_active=True),
            'goals': request.user.savings_goals.all(),
        }


class EditCycleView(LoginRequiredMixin, View):
    def get(self, request):
        cycle = get_active_cycle(request.user)
        if not cycle:
            return redirect('start_cycle')
        return render(request, 'finance/cycle_form.html', {'form': forms.CycleForm(instance=cycle), 'is_new': False})

    def post(self, request):
        cycle = get_active_cycle(request.user)
        if not cycle:
            return redirect('start_cycle')
        form = forms.CycleForm(request.POST, instance=cycle)
        if form.is_valid():
            form.save()
            return redirect('settings')
        return render(request, 'finance/cycle_form.html', {'form': form, 'is_new': False})


# --- Settings and recurring expenses ---

class SettingsView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'finance/settings.html', {
            'cycle': get_active_cycle(request.user),
            'recurring_expenses': request.user.recurring_expenses.order_by('-amount'),
        })


class AddRecurringView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'finance/recurring_form.html', {'form': forms.RecurringExpenseForm()})

    def post(self, request):
        form = forms.RecurringExpenseForm(request.POST)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.user = request.user
            recurring.save()
            return redirect('settings')
        return render(request, 'finance/recurring_form.html', {'form': form})


class EditRecurringView(LoginRequiredMixin, View):
    def get(self, request, pk):
        recurring_expense = get_object_or_404(models.RecurringExpense, user=request.user, pk=pk)
        form = forms.RecurringExpenseForm(instance=recurring_expense)
        return render(request, 'finance/recurring_form.html', {'form': form, 'obj': recurring_expense})

    def post(self, request, pk):
        recurring_expense = get_object_or_404(models.RecurringExpense, user=request.user, pk=pk)
        form = forms.RecurringExpenseForm(request.POST, instance=recurring_expense)
        if form.is_valid():
            form.save()
            return redirect('settings')
        return render(request, 'finance/recurring_form.html', {'form': form, 'obj': recurring_expense})


class DeleteRecurringView(LoginRequiredMixin, View):
    def get(self, request, pk):
        recurring_expense = get_object_or_404(models.RecurringExpense, user=request.user, pk=pk)
        return render(request, 'finance/confirm_delete.html', {'obj': recurring_expense, 'cancel_url': 'settings'})

    def post(self, request, pk):
        recurring_expense = get_object_or_404(models.RecurringExpense, user=request.user, pk=pk)
        recurring_expense.delete()
        return redirect('settings')


# --- Savings ---

class SavingsView(LoginRequiredMixin, View):
    def get(self, request):
        goals = list(request.user.savings_goals.all())
        transactions = list(
            models.SavingsTransaction.objects.filter(goal__user=request.user).select_related('goal')
        )

        # Running total at the end of each month, oldest first
        monthly = {}
        for t in transactions:
            key = t.date.strftime('%Y-%m')
            monthly[key] = monthly.get(key, 0) + t.amount
        history, running = [], 0
        for key in sorted(monthly):
            running += monthly[key]
            history.append({'month': key, 'total': running})

        # When each goal is reached at its planned amount per cycle
        this_month = timezone.localdate().replace(day=1)
        for g in goals:
            g.months_left = None
            g.eta = None
            if g.saved >= g.target:
                g.months_left = 0
            elif g.monthly_amount:
                g.months_left = -(-(g.target - g.saved) // g.monthly_amount)
                month_index = this_month.month - 1 + g.months_left
                g.eta = this_month.replace(year=this_month.year + month_index // 12, month=month_index % 12 + 1)

        cycle = get_active_cycle(request.user)
        chart = {
            'history': history,
            'total': running,
            'goals': [{'name': g.name, 'months': g.months_left} for g in goals],
            'per_month': sum(g.monthly_amount for g in goals),
        }
        return render(request, 'finance/savings.html', {
            'goals': goals,
            'total': running,
            'transactions': transactions[:20],
            'chart': chart,
            'currency': cycle.currency_symbol if cycle else '',
        })


class AddGoalView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'finance/goal_form.html', {'form': forms.SavingsGoalForm()})

    def post(self, request):
        form = forms.SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('savings')
        return render(request, 'finance/goal_form.html', {'form': form})


class EditGoalView(LoginRequiredMixin, View):
    def get(self, request, pk):
        goal = get_object_or_404(models.SavingsGoal, user=request.user, pk=pk)
        return render(request, 'finance/goal_form.html', {'form': forms.SavingsGoalForm(instance=goal), 'obj': goal})

    def post(self, request, pk):
        goal = get_object_or_404(models.SavingsGoal, user=request.user, pk=pk)
        form = forms.SavingsGoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            return redirect('savings')
        return render(request, 'finance/goal_form.html', {'form': form, 'obj': goal})


class DeleteGoalView(LoginRequiredMixin, View):
    def get(self, request, pk):
        goal = get_object_or_404(models.SavingsGoal, user=request.user, pk=pk)
        return render(request, 'finance/confirm_delete.html', {'obj': goal, 'cancel_url': 'savings'})

    def post(self, request, pk):
        goal = get_object_or_404(models.SavingsGoal, user=request.user, pk=pk)
        goal.delete()
        return redirect('savings')


class GoalTransferView(LoginRequiredMixin, View):
    """Move money from the balance into a goal: an expense in the current cycle."""
    def get(self, request, pk):
        goal = get_object_or_404(models.SavingsGoal, user=request.user, pk=pk)
        return render(request, 'finance/goal_transfer.html', {'form': forms.TransferForm(), 'goal': goal})

    def post(self, request, pk):
        goal = get_object_or_404(models.SavingsGoal, user=request.user, pk=pk)
        form = forms.TransferForm(request.POST)
        if not form.is_valid():
            return render(request, 'finance/goal_transfer.html', {'form': form, 'goal': goal})

        amount = form.cleaned_data['amount']
        cycle = get_active_cycle(request.user)
        if cycle:
            entry = models.Entry(cycle=cycle, kind=models.Entry.EXPENSE, title=goal.name, amount=amount, goal=goal)
            entry.set_done(True)
            entry.save()
            entry.sync_savings()
        else:
            models.SavingsTransaction.objects.create(goal=goal, amount=amount)
        return redirect('savings')


# --- AI API ---

class GetAIAdviceView(LoginRequiredMixin, View):
    def get(self, request):
        cycle = get_active_cycle(request.user)
        if not cycle:
            return JsonResponse({'error': 'No active cycle found.'}, status=400)

        s = budget.summarize(cycle)
        entries = list(cycle.entries.select_related('goal'))
        ai_context = {
            'remaining_days': s.days_left,
            'main_budget': s.free_money,
            'daily_allowance': s.per_day,
            'currency': cycle.currency_symbol,
            'uncertain_total': s.pending_net,
            'debt_total': sum(e.amount for e in entries if e.is_income and e.is_debt),
            'full_ledger': budget.ledger_text(entries, cycle.currency_symbol),
            'language': request.LANGUAGE_CODE,
        }

        try:
            advice = ai_utils.get_financial_advice(ai_context)
            return JsonResponse({'advice': advice})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# User Registration

class SignupView(CreateView):
    form_class = UserCreationForm
    template_name = 'finance/signup.html'
    success_url = reverse_lazy('login')
