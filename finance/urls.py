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
    path("settings/",views.SettingsView.as_view(),name='settings'),
    path("add/recurring/expense/",views.AddRecurringView.as_view(),name='add_recurring'),
    path("edit/recurring/expense/<int:pk>",views.EditRecurringView.as_view(),name='edit_recurring'),
    path("delete/recurring/expense/<int:pk>",views.DeleteRecurringView.as_view(),name='delete_recurring'),
    path("start-cycle/", views.StartCycleView.as_view(), name='start_cycle'),
]
