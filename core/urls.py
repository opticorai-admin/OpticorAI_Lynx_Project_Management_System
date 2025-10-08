from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.IndexView.as_view(), name='dashboard'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('verify-2fa/', views.VerifyTwoFactorView.as_view(), name='verify-2fa'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # --- User Management ---
    path('new-user/', views.RegisterView.as_view(), name='new-user'),
    path('users/', views.UsersView.as_view(), name='users'),
    path('users/profile', views.ProfileView.as_view(), name='profile'),
    path('users/<int:profile_id>/', views.UserProfileView.as_view(), name='user'),
    path('users/<int:user_id>/edit/', views.EditUserProfileView.as_view(), name='edit-user-profile'),
    path('users/<int:user_id>/tasks/', views.UserTasksView.as_view(), name='user-tasks'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='delete-user'),
    path('users/<int:user_id>/set-password/', views.AdminSetPasswordView.as_view(), name='admin-set-password'),
    
    # --- Email Testing (Admin Only) ---
    path('test-email/', views.TestEmailView.as_view(), name='test-email'),
    
    # --- Task Management ---
    path('projects/', views.ProjectsView.as_view(), name='projects'),
    path('views/my-tasks/', views.MyTasksView.as_view(), name='my-tasks'),
    path('projects/new-task/', views.NewTaskView.as_view(), name='new-task'),
    path('projects/task/<int:task_id>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('projects/task/<int:task_id>/edit/', views.EditTaskView.as_view(), name='edit-task'),
    path('projects/task/<int:task_id>/delete/', views.DeleteTaskView.as_view(), name='delete-task'),
    path('projects/task/<int:task_id>/download/', views.DownloadFileView.as_view(), name='download-file'),
    path('projects/task/<int:task_id>/reminder/', views.CreateTaskReminderView.as_view(), name='create-task-reminder'),
    path('projects/task/<int:task_id>/reminder/<int:reminder_id>/update/', views.UpdateTaskReminderView.as_view(), name='update-task-reminder'),
    path('projects/task/<int:task_id>/reminder/<int:reminder_id>/delete/', views.DeleteTaskReminderView.as_view(), name='delete-task-reminder'),
    path('projects/task/<int:task_id>/upload/', views.UploadTaskFileView.as_view(), name='upload-task-file'),
    path('projects/task/<int:task_id>/approve/', views.ApproveTaskView.as_view(), name='approve-task'),
    path('projects/task/<int:task_id>/evaluate/', views.EvaluateTaskView.as_view(), name='evaluate-task'),
    path('projects/task/<int:task_id>/close-incomplete/', views.CloseIncompleteTaskView.as_view(), name='close-incomplete-task'),
    path('projects/task/<int:task_id>/submit-text/', views.SubmitTaskTextView.as_view(), name='submit-task-text'),
    
    # --- Settings Management (Manager Only) ---
    path('settings/', views.SettingsDashboardView.as_view(), name='settings-dashboard'),
    path('settings/update-task-statuses/', views.UpdateTaskStatusesView.as_view(), name='update-task-statuses'),
    
    # --- KPI Management ---
    path('settings/kpis/', views.KPIListView.as_view(), name='kpi-list'),
    path('settings/kpis/create/', views.KPICreateView.as_view(), name='kpi-create'),
    path('settings/kpis/<int:pk>/edit/', views.KPIUpdateView.as_view(), name='kpi-edit'),
    path('settings/kpis/<int:pk>/delete/', views.KPIDeleteView.as_view(), name='kpi-delete'),
    
    # --- QualityType Management ---
    path('settings/quality-types/', views.QualityTypeListView.as_view(), name='qualitytype-list'),
    path('settings/quality-types/create/', views.QualityTypeCreateView.as_view(), name='qualitytype-create'),
    path('settings/quality-types/<int:pk>/edit/', views.QualityTypeUpdateView.as_view(), name='qualitytype-edit'),
    path('settings/quality-types/<int:pk>/delete/', views.QualityTypeDeleteView.as_view(), name='qualitytype-delete'),
    
    # --- TaskPriorityType Management (Admin Only) ---
    path('settings/priority-types/', views.TaskPriorityTypeListView.as_view(), name='taskprioritytype-list'),
    path('settings/priority-types/create/', views.TaskPriorityTypeCreateView.as_view(), name='taskprioritytype-create'),
    path('settings/priority-types/<int:pk>/edit/', views.TaskPriorityTypeUpdateView.as_view(), name='taskprioritytype-edit'),
    path('settings/priority-types/<int:pk>/delete/', views.TaskPriorityTypeDeleteView.as_view(), name='taskprioritytype-delete'),
    
    # --- Employee Progress Management (Manager Only) ---
    path('settings/employee-progress/', views.EmployeeProgressListView.as_view(), name='employee-progress-list'),
    path('settings/employee-progress/<int:employee_id>/', views.EmployeeProgressDetailView.as_view(), name='employee-progress-detail'),
    path('settings/employee-progress/<int:employee_id>/recalculate/', views.RecalculateProgressView.as_view(), name='recalculate-progress'),
    
    # --- TaskEvaluationSettings Management (Admin Only) ---
    path('settings/evaluation-settings/', views.TaskEvaluationSettingsView.as_view(), name='taskevaluationsettings'),
    
    # --- Evaluation Demo ---
    path('evaluation-demo/', views.EvaluationDemoView.as_view(), name='evaluation-demo'),
    
    # --- Notification Management ---
    path('notifications/', views.NotificationsListView.as_view(), name='notifications-list'),
    path('notifications/<int:notification_id>/mark-read/', views.MarkNotificationReadView.as_view(), name='mark-notification-read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark-all-notifications-read'),
    path('notifications/<int:notification_id>/delete/', views.DeleteNotificationView.as_view(), name='delete-notification'),

    # --- Progress Report (Manager Only) ---
    path('settings/progress-report/', views.ProgressReportView.as_view(), name='progress-report'),

    # --- Monthly Employee Stats (Manager Only) ---
    path('settings/monthly-stats/', views.MonthlyEmployeeStatsView.as_view(), name='monthly-employee-stats'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)