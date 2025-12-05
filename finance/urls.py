from django.urls import path 
from . import views
urlpatterns = [
    path("", views.DashBoardView.as_view(), name="home"),
    path("add/income/",views.AddIncomeView.as_view(),name='add_income'),
    path("add/expense/",views.AddExpenseView.as_view(),name='add_expense'),
    path("edit/income/<int:pk>",views.EditIncomeView.as_view(),name='edit_income'),
    path("edit/expense/<int:pk>",views.EditExpenseView.as_view(),name='edit_expense'),
    path("delete/income/<int:pk>",views.DeleteIncomeView.as_view(),name='delete_income'),
    path("delete/expense/<int:pk>",views.DeleteExpenseView.as_view(),name='delete_expense'),
]
