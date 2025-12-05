from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from . import models
from datetime import date, timedelta
from . import forms


# Helper function to get active cycle
def get_active_cycle():
    return models.Cycle.objects.order_by('-start').first()



class DashBoardView(View):
    def get(self,request):
        current_cycle = models.Cycle.objects.order_by('-start').first()
        if not current_cycle:
            return render(request, 'finance/dashboard.html', {'error': 'No active cycle found.'})
        
        cycle_end_date =  current_cycle.start + timedelta(days = 30)
        today = date.today()
        rest_of_days = (cycle_end_date - today).days

        if rest_of_days < 1:
            rest_of_days = 1

        
        incomes = models.Income.objects.filter(cycle=current_cycle)
        expenses = models.Expense.objects.filter(cycle=current_cycle)


        total_incomes = sum(i.amount_tl for i in incomes if i.amount_tl)
        total_expenses = sum(i.amount_tl for i in expenses if i.amount_tl)

        budget = total_incomes - total_expenses
        daily_allowance = round(budget / rest_of_days)

        return render(request,'finance/dashboard.html',{
            'incomes':incomes,
            'expenses':expenses,
            'total_incomes':total_incomes,
            'total_expenses':total_expenses,
            'budget':budget,
            'daily_allowance':daily_allowance,
            'remaining_days':rest_of_days
            })





class AddIncomeView(View):
    def get(self,request):
        form = forms.IncomeForm()
        return render(request,'finance/add_income.html',{'form':form})
    
    def post(self,request):
        form = forms.IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.cycle = get_active_cycle()
            income.save()
            return redirect('home')
        
        return render(request,'finance/add_income.html',{'form':form})


class AddExpenseView(View):
    def get(self,request):
        form = forms.ExpenseForm()
        return render(request,'finance/add_expense.html',{'form':form})
    
    def post(self,request):
        form = forms.ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.cycle = get_active_cycle()
            expense.save()
            return redirect('home')
        
        return render(request,'finance/add_expense.html',{'form':form})


class EditIncomeView(View):
    
    def get(self,request,pk):
        income = models.Income.objects.get(pk=pk)
        form = forms.IncomeForm(instance=income)
        return render(request,'finance/edit_income.html',{'form':form,'income':income})
    
    def post(self,request,pk):
        income =  models.Income.objects.get(pk=pk)
        form = forms.IncomeForm(request.POST,instance=income)
        if form.is_valid():
            form.save()
            return redirect('home')
        else:
            return render(request,'finance/edit_income.html',{'form':form,'income':income})


class EditExpenseView(View):
    
    def get(self,request,pk):
        expense = models.Expense.objects.get(pk=pk)
        form = forms.ExpenseForm(instance=expense)
        return render(request,'finance/edit_expense.html',{'form':form,'expense':expense})
    
    def post(self,request,pk):
        expense =  models.Expense.objects.get(pk=pk)
        form = forms.ExpenseForm(request.POST,instance=expense)
        if form.is_valid():
            form.save()
            return redirect('home')
        else:
            return render(request,'finance/edit_expense.html',{'form':form,'expense':expense})

class DeleteIncomeView(View):
    def get(self, request, pk):
        income = get_object_or_404(models.Income, pk=pk)
        # Reuse a generic confirmation template
        return render(request, 'finance/delete_confirm.html', {'obj': income, 'type': 'Income'})
    
    def post(self, request, pk):
        income = get_object_or_404(models.Income, pk=pk)
        income.delete()
        return redirect('home')

class DeleteExpenseView(View):
    def get(self, request, pk):
        expense = get_object_or_404(models.Expense, pk=pk)
        return render(request, 'finance/delete_confirm.html', {'obj': expense, 'type': 'Expense'})
    
    def post(self, request, pk):
        expense = get_object_or_404(models.Expense, pk=pk)
        expense.delete()
        return redirect('home')