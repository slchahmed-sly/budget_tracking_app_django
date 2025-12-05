from django.shortcuts import render
from django.views import View
from . import models
from datetime import date, timedelta


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
            })








