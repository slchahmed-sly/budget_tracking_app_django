from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from . import models
from datetime import date, timedelta
from . import forms
# User Registration
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

# Helper function to get active cycle
def get_active_cycle(user):
    return models.Cycle.objects.filter(user=user).order_by('-start').first()



class DashBoardView(LoginRequiredMixin,View):
    def get(self,request):
        current_cycle = get_active_cycle(request.user)
        if not current_cycle:
            return render(request, 'finance/dashboard.html', {'error': 'No active cycle found.'})
        
        cycle_end_date =  current_cycle.start + timedelta(days = 30)
        today = date.today()
        rest_of_days = (cycle_end_date - today).days

        if rest_of_days < 1:
            rest_of_days = 1

        
        incomes = models.Income.objects.filter(cycle=current_cycle).order_by('-amount')
        expenses = models.Expense.objects.filter(cycle=current_cycle).order_by('-amount')
        specials = models.Special.objects.filter(cycle=current_cycle).order_by('-amount') 

        total_incomes = sum(i.amount for i in incomes if i.amount)
        total_expenses = sum(i.amount for i in expenses if i.amount)

        # Main Budget (Sure Incomes - Sure Expenses)
        main_budget = total_incomes - total_expenses
        main_daily_allowance = round(main_budget / rest_of_days)

        # Specials Calculation
        special_incomes = [s for s in specials if s.type == 'income']
        special_expenses = [s for s in specials if s.type == 'expense']

        total_special_incomes = sum(s.amount for s in special_incomes if s.amount)
        total_special_expenses = sum(s.amount for s in special_expenses if s.amount)

        # Potential Budget (Sure + Special)
        potential_total_incomes = total_incomes + total_special_incomes
        potential_total_expenses = total_expenses + total_special_expenses
        
        potential_budget = potential_total_incomes - potential_total_expenses
        potential_daily_allowance = round(potential_budget / rest_of_days)

        return render(request, 'finance/dashboard.html', {
            'main_budget': main_budget,
            'main_daily_allowance': main_daily_allowance,
            
            'potential_budget': potential_budget,
            'potential_daily_allowance': potential_daily_allowance,

            'remaining_days': rest_of_days,
            'cycle_currency': current_cycle.currency_symbol,
            'incomes': incomes,
            'expenses': expenses,
            'specials': specials,
            
            'total_incomes': total_incomes,
            'total_expenses': total_expenses,
            'total_special_incomes': total_special_incomes,
            'total_special_expenses': total_special_expenses,
        })


class ConvertSpecialView(LoginRequiredMixin,View):
    def post(self, request, pk):
        special = get_object_or_404(models.Special,cycle__user=request.user, pk=pk)
        current_cycle = special.cycle

        if special.type == 'income':
            # Create new Income, assuming 'certain' status as per user request
            models.Income.objects.create(
                source=special.title,
                amount=special.amount,
                cycle=current_cycle,
                comment=special.comment,
                owe_me=special.owe_me,
                status='certain' 
            )
        elif special.type == 'expense':
            # Create new Expense
            models.Expense.objects.create(
                purpose=special.title,
                amount=special.amount,
                cycle=current_cycle,
                comment=special.comment,
                i_owe=special.i_owe
            )
        
        special.delete()
        return redirect('home')


class AddIncomeView(LoginRequiredMixin,View):
    def get(self,request):
        form = forms.IncomeForm()
        active_cycle = get_active_cycle(request.user)
        if not active_cycle:
             return render(request, 'finance/no_cycle.html')

        cycle_currency = active_cycle.currency_symbol
        return render(request,'finance/add_income.html',{'form':form,'cycle_currency':cycle_currency})
    
    def post(self,request):
        active_cycle = get_active_cycle(request.user)
        if not active_cycle:
             return render(request, 'finance/no_cycle.html')

        form = forms.IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.cycle = active_cycle
            income.save()
            return redirect('home')
        
        return render(request,'finance/add_income.html',{'form':form})


class AddSpecialView(LoginRequiredMixin,View):
    def get(self, request):
        form = forms.SpecialForm()
        active_cycle = get_active_cycle(request.user)
        if not active_cycle:
             return render(request, 'finance/no_cycle.html')
        
        cycle_currency = active_cycle.currency_symbol
        return render(request, 'finance/add_special.html', {'form': form, 'cycle_currency': cycle_currency})

    def post(self, request):
        active_cycle = get_active_cycle(request.user)
        if not active_cycle:
             return render(request, 'finance/no_cycle.html')

        form = forms.SpecialForm(request.POST)
        if form.is_valid():
            special = form.save(commit=False)
            special.cycle = active_cycle
            special.save()
            return redirect('home')
        return render(request, 'finance/add_special.html', {'form': form})


class EditSpecialView(LoginRequiredMixin,View):
    def get(self, request, pk):
        special = get_object_or_404(models.Special,cycle__user=request.user, pk=pk)
        form = forms.SpecialForm(instance=special)
        active_cycle = get_active_cycle(request.user)
        if active_cycle:
            cycle_currency = active_cycle.currency_symbol
        else:
            cycle_currency = 'no currency'
        return render(request, 'finance/edit_special.html', {'form': form, 'special': special, 'cycle_currency': cycle_currency})

    def post(self, request, pk):
        special = get_object_or_404(models.Special,cycle__user=request.user, pk=pk)
        form = forms.SpecialForm(request.POST, instance=special)
        if form.is_valid():
            form.save()
            return redirect('home')
        return render(request, 'finance/edit_special.html', {'form': form, 'special': special})


class DeleteSpecialView(LoginRequiredMixin,View):
    def get(self, request, pk):
        special = get_object_or_404(models.Special,cycle__user=request.user, pk=pk)
        return render(request, 'finance/delete_confirm.html', {'obj': special, 'type': 'Special Transaction'})

    def post(self, request, pk):
        special = get_object_or_404(models.Special,cycle__user=request.user, pk=pk)
        special.delete()
        return redirect('home')


class AddExpenseView(LoginRequiredMixin,View):
    def get(self,request):
        form = forms.ExpenseForm()
        active_cycle = get_active_cycle(request.user)
        if not active_cycle:
             return render(request, 'finance/no_cycle.html')
        
        cycle_currency = active_cycle.currency_symbol
        return render(request,'finance/add_expense.html',{'form':form,'cycle_currency':cycle_currency})
    
    def post(self,request):
        active_cycle = get_active_cycle(request.user)
        if not active_cycle:
             return render(request, 'finance/no_cycle.html')

        form = forms.ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.cycle = active_cycle
            expense.save()
            return redirect('home')
        
        return render(request,'finance/add_expense.html',{'form':form})


class EditIncomeView(LoginRequiredMixin,View):
    
    def get(self,request,pk):
        income = get_object_or_404(models.Income,cycle__user=request.user,pk=pk)
        form = forms.IncomeForm(instance=income)
        active_cycle = get_active_cycle(request.user)
        if active_cycle:
            cycle_currency = active_cycle.currency_symbol
        else:
            cycle_currency = 'no currency'
        return render(request,'finance/edit_income.html',{'form':form,'income':income,'cycle_currency':cycle_currency})
    
    def post(self,request,pk):
        income =  get_object_or_404(models.Income,cycle__user=request.user,pk=pk)
        form = forms.IncomeForm(request.POST,instance=income)
        if form.is_valid():
            form.save()
            return redirect('home')
        else:
            return render(request,'finance/edit_income.html',{'form':form,'income':income})


class EditExpenseView(LoginRequiredMixin,View):
    
    def get(self,request,pk):
        expense = get_object_or_404(models.Expense,cycle__user=request.user,pk=pk)
        form = forms.ExpenseForm(instance=expense)
        active_cycle = get_active_cycle(request.user)
        if active_cycle:
            cycle_currency = active_cycle.currency_symbol
        else:
            cycle_currency = 'no currency'
        return render(request,'finance/edit_expense.html',{'form':form,'expense':expense,'cycle_currency':cycle_currency})
    
    def post(self,request,pk):
        expense =  get_object_or_404(models.Expense,cycle__user=request.user,pk=pk)
        form = forms.ExpenseForm(request.POST,instance=expense)
        if form.is_valid():
            form.save()
            return redirect('home')
        else:
            return render(request,'finance/edit_expense.html',{'form':form,'expense':expense})

class DeleteIncomeView(LoginRequiredMixin,View):
    def get(self, request, pk):
        income = get_object_or_404(models.Income,cycle__user=request.user, pk=pk)

        return render(request, 'finance/delete_confirm.html', {'obj': income, 'type': 'Income'})
    
    def post(self, request, pk):
        income = get_object_or_404(models.Income,cycle__user=request.user, pk=pk)
        income.delete()
        return redirect('home')

class DeleteExpenseView(LoginRequiredMixin,View):
    def get(self, request, pk):
        expense = get_object_or_404(models.Expense,cycle__user=request.user, pk=pk)
        return render(request, 'finance/delete_confirm.html', {'obj': expense, 'type': 'Expense'})
    
    def post(self, request, pk):
        expense = get_object_or_404(models.Expense,cycle__user=request.user, pk=pk)
        expense.delete()
        return redirect('home')





# settings section related views

class SettingsView(LoginRequiredMixin,View):
    def get(self, request):
        cycle_form = forms.CycleForm()
        active_cycle = get_active_cycle(request.user)
        if active_cycle:
            cycle_currency = active_cycle.currency_symbol
        else:
            cycle_currency = 'no currency'
        recurring_expenses = models.RecurringExpense.objects.filter(user=request.user).order_by('-amount')
        return render(request,'finance/settings.html',{'recurring_expenses':recurring_expenses,'form':cycle_form,'cycle_currency':cycle_currency})


class AddRecurringView(LoginRequiredMixin,View):
    def get(self,request):
        form = forms.RecurringExpenseForm()
        return render(request,'finance/add_recurring.html',{'form':form})

    def post(self,request):
        form = forms.RecurringExpenseForm(request.POST)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.user = request.user
            recurring.save()
            return redirect('settings')
        return render(request,'finance/add_recurring.html',{'form':form})


class EditRecurringView(LoginRequiredMixin,View):
    def get(self,request,pk):
        recurring_expense = models.RecurringExpense.objects.filter(user=request.user).get(pk = pk)
        form = forms.RecurringExpenseForm(instance=recurring_expense)
        return render(request,'finance/edit_recurring.html',{'form':form})

    def post(self,request,pk):
        recurring_expense = models.RecurringExpense.objects.filter(user=request.user).get(pk = pk)
        form = forms.RecurringExpenseForm(request.POST,instance=recurring_expense)
        if form.is_valid():
            form.save()
            return redirect('settings')
        return render(request,'finance/edit_recurring.html',{'form':form})



class DeleteRecurringView(LoginRequiredMixin,View):
    def get(self,request,pk):
        recurring_expense = models.RecurringExpense.objects.filter(user=request.user).get(pk = pk)
        return render(request,'finance/delete_confirm.html',{'obj':recurring_expense,'type':'Recurring Expense'})

    def post(self,request,pk):
        recurring_expense = models.RecurringExpense.objects.filter(user=request.user).get(pk = pk)
        recurring_expense.delete()
        return redirect('settings')



class StartCycleView(LoginRequiredMixin,View):
    
    def post(self,request):
        form = forms.CycleForm(request.POST)

        if form.is_valid():
            active_cycle = form.save(commit=False)
            active_cycle.user = request.user
            active_cycle.save()
            recurring_expenses = models.RecurringExpense.objects.filter(user=request.user,is_active=True)
            for recurring in recurring_expenses:
                expense = models.Expense(purpose=recurring.purpose,amount=recurring.amount,cycle=active_cycle)
                expense.save()
            return redirect('home')
        return redirect('settings')
            
        


# User Registration

class SignupView(CreateView):
    form_class = UserCreationForm
    template_name = 'finance/signup.html'
    success_url = reverse_lazy('login')