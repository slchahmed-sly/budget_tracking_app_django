from django.urls import path 
from . import views
from django.contrib.auth.views import LoginView, LogoutView
urlpatterns = [
    path("", views.DashBoardView.as_view(), name="home"),
    # Income and Expense Routes
    path("add/income/",views.AddIncomeView.as_view(),name='add_income'),
    path("add/expense/",views.AddExpenseView.as_view(),name='add_expense'),
    path("edit/income/<int:pk>",views.EditIncomeView.as_view(),name='edit_income'),
    path("edit/expense/<int:pk>",views.EditExpenseView.as_view(),name='edit_expense'),
    path("delete/income/<int:pk>",views.DeleteIncomeView.as_view(),name='delete_income'),
    path("delete/expense/<int:pk>",views.DeleteExpenseView.as_view(),name='delete_expense'),
    # Settings Routes
    path("settings/",views.SettingsView.as_view(),name='settings'),
    path("start-cycle/", views.StartCycleView.as_view(), name='start_cycle'),
    # Recurring Expense Routes
    path("add/recurring/expense/",views.AddRecurringView.as_view(),name='add_recurring'),
    path("edit/recurring/expense/<int:pk>",views.EditRecurringView.as_view(),name='edit_recurring'),
    path("delete/recurring/expense/<int:pk>",views.DeleteRecurringView.as_view(),name='delete_recurring'),
    # Special Routes
    path("add/special/",views.AddSpecialView.as_view(),name='add_special'),
    path("edit/special/<int:pk>",views.EditSpecialView.as_view(),name='edit_special'),
    path("delete/special/<int:pk>",views.DeleteSpecialView.as_view(),name='delete_special'),
    path("convert/special/<int:pk>",views.ConvertSpecialView.as_view(),name='convert_special'),
    # --- Auth Routes ---
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(template_name='finance/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]
