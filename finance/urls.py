from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path("", views.DashBoardView.as_view(), name="home"),
    # Entries (income and expenses)
    path("add/", views.AddEntryView.as_view(), name='add_entry'),
    path("entry/<int:pk>/edit/", views.EditEntryView.as_view(), name='edit_entry'),
    path("entry/<int:pk>/delete/", views.DeleteEntryView.as_view(), name='delete_entry'),
    path("entry/<int:pk>/toggle-done/", views.ToggleEntryDoneView.as_view(), name='toggle_entry_done'),
    path("entry/<int:pk>/confirm/", views.ConfirmEntryView.as_view(), name='confirm_entry'),
    path("check-in/", views.CheckInView.as_view(), name='checkin'),
    # Cycles and settings
    path("settings/", views.SettingsView.as_view(), name='settings'),
    path("start-cycle/", views.StartCycleView.as_view(), name='start_cycle'),
    path("edit-cycle/", views.EditCycleView.as_view(), name='edit_cycle'),
    # Recurring Expense Routes
    path("add/recurring/expense/", views.AddRecurringView.as_view(), name='add_recurring'),
    path("edit/recurring/expense/<int:pk>", views.EditRecurringView.as_view(), name='edit_recurring'),
    path("delete/recurring/expense/<int:pk>", views.DeleteRecurringView.as_view(), name='delete_recurring'),
    # Savings
    path("savings/", views.SavingsView.as_view(), name='savings'),
    path("savings/goal/add/", views.AddGoalView.as_view(), name='add_goal'),
    path("savings/goal/<int:pk>/edit/", views.EditGoalView.as_view(), name='edit_goal'),
    path("savings/goal/<int:pk>/delete/", views.DeleteGoalView.as_view(), name='delete_goal'),
    path("savings/goal/<int:pk>/<str:direction>/", views.GoalTransferView.as_view(), name='goal_transfer'),
    # --- AI API ---
    path("api/get-ai-advice/", views.GetAIAdviceView.as_view(), name='get_ai_advice'),
    # --- Auth Routes ---
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(template_name='finance/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]
