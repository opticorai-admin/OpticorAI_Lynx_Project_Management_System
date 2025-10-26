from core.models import CustomUser, Task, KPI, QualityType, Notification, TaskEvaluationSettings, TaskPriorityType, EmployeeProgress, Note, NoteReminder, ChatBot, ChatMessage
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# Register your models here.

class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'designation', 'is_active']
    list_filter = ['user_type', 'is_active', 'created_date']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'designation', 'under_supervision', 'created_by', 'avatar')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'designation', 'under_supervision', 'email')}),
    )

    def save_model(self, request, obj, form, change):
        # Call parent to handle default save behavior
        super().save_model(request, obj, form, change)
        # If an admin updates a user via admin site, notify that user about changed fields
        try:
            if change and request.user and hasattr(form, 'changed_data') and form.changed_data:
                # Avoid notifying when the user edits their own record via admin
                if obj != request.user:
                    field_labels = {
                        'email': 'Email',
                        'first_name': 'First name',
                        'last_name': 'Last name',
                        'designation': 'Designation',
                        'user_type': 'Role',
                        'under_supervision': 'Supervisor',
                        'avatar': 'Profile picture',
                        'is_active': 'Active status',
                        'is_staff': 'Staff status',
                        'is_superuser': 'Superuser status',
                    }
                    friendly = [field_labels.get(f, f) for f in form.changed_data]
                    changes_text = ", ".join(sorted(set(friendly)))
                    Notification.objects.create(
                        recipient=obj,
                        sender=request.user,
                        message=f"Your profile was updated by an administrator. Updated fields: {changes_text}.",
                        link=f"/users/{obj.id}/"
                    )
        except Exception:
            # Never break admin save because of notification errors
            pass

class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'issue_action', 'responsible', 'priority', 'kpi', 'quality',
        'start_date', 'target_date', 'close_date', 'created_by', 'status',
        'percentage_completion', 'approval_status', 'final_score', 'created_date', 'updated_date'
    ]
    search_fields = ['issue_action', 'responsible__username', 'created_by__username']
    list_filter = ['priority', 'kpi', 'quality', 'status', 'approval_status', 'evaluation_status', 'created_date', 'updated_date']
    readonly_fields = ['created_date', 'updated_date', 'final_score', 'quality_score_calculated', 'priority_multiplier', 'time_bonus_penalty', 'completion_date']
    list_select_related = ('responsible', 'priority', 'kpi', 'quality', 'created_by')

class KPIAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight', 'is_active', 'sort_order', 'created_by', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['is_active', 'created_at', 'created_by']
    list_editable = ['weight', 'is_active', 'sort_order']
    readonly_fields = ['created_at']
    ordering = ['sort_order', 'name']
    list_select_related = ('created_by',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Configuration', {
            'fields': ('weight', 'is_active', 'sort_order')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

class TaskPriorityTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'multiplier', 'is_active', 'sort_order', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active', 'sort_order']
    readonly_fields = ['created_at']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Configuration', {
            'fields': ('multiplier', 'is_active', 'sort_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class QualityTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'percentage', 'is_active', 'sort_order', 'created_by', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active', 'sort_order']
    readonly_fields = ['created_at', 'created_by']
    ordering = ['sort_order', 'name']
    list_select_related = ('created_by',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Configuration', {
            'fields': ('percentage', 'is_active', 'sort_order')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'sender', 'message', 'read', 'created_at']
    list_filter = ['read', 'created_at', 'recipient__user_type', 'sender__user_type']
    search_fields = ['message', 'recipient__username', 'sender__username']
    readonly_fields = ['created_at']
    list_editable = ['read']
    date_hierarchy = 'created_at'
    list_select_related = ('recipient', 'sender')

class TaskEvaluationSettingsAdmin(admin.ModelAdmin):
    list_display = ['evaluation_formula', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not TaskEvaluationSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion
        return False

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(KPI, KPIAdmin)
admin.site.register(TaskPriorityType, TaskPriorityTypeAdmin)
admin.site.register(QualityType, QualityTypeAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(TaskEvaluationSettings, TaskEvaluationSettingsAdmin)

class EmployeeProgressAdmin(admin.ModelAdmin):
    list_display = ['employee', 'manager', 'period_start', 'period_end', 'total_progress_score', 'calculation_date']
    list_filter = ['manager', 'calculation_date', 'period_start', 'period_end']
    search_fields = ['employee__first_name', 'employee__last_name', 'manager__first_name', 'manager__last_name']
    readonly_fields = ['calculation_date', 'created_at', 'updated_at']
    ordering = ['-period_end', '-created_at']
    list_select_related = ('employee', 'manager', 'calculated_by')
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'manager')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Progress Data', {
            'fields': ('total_progress_score', 'progress_breakdown', 'notes')
        }),
        ('Metadata', {
            'fields': ('calculated_by', 'calculation_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(EmployeeProgress, EmployeeProgressAdmin)

class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'assigned_to', 'is_flagged', 'related_task', 'created_at', 'updated_at']
    list_filter = ['is_flagged', 'created_at', 'updated_at', 'created_by', 'assigned_to']
    search_fields = ['title', 'content', 'created_by__username', 'assigned_to__username']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_flagged']
    date_hierarchy = 'created_at'
    list_select_related = ('created_by', 'assigned_to', 'related_task')
    
    fieldsets = (
        ('Note Information', {
            'fields': ('title', 'content', 'is_flagged')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to', 'related_task')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class NoteReminderAdmin(admin.ModelAdmin):
    list_display = ['note', 'recipient', 'scheduled_for', 'created_by', 'sent_at', 'created_at']
    list_filter = ['scheduled_for', 'sent_at', 'created_at', 'recipient']
    search_fields = ['note__title', 'recipient__username', 'message']
    readonly_fields = ['created_at', 'sent_at']
    date_hierarchy = 'scheduled_for'
    list_select_related = ('note', 'recipient', 'created_by')
    
    fieldsets = (
        ('Reminder Information', {
            'fields': ('note', 'recipient', 'scheduled_for', 'message')
        }),
        ('Status', {
            'fields': ('created_by', 'sent_at', 'created_at')
        }),
    )

admin.site.register(Note, NoteAdmin)
admin.site.register(NoteReminder, NoteReminderAdmin)

class ChatBotAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'user', 'is_active', 'created_at', 'updated_at', 'get_messages_count']
    list_filter = ['is_active', 'created_at', 'updated_at', 'user__user_type']
    search_fields = ['session_name', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']
    date_hierarchy = 'created_at'
    list_select_related = ('user',)
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'session_name', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['chat_session', 'message_type', 'content_preview', 'tokens_used', 'timestamp']
    list_filter = ['message_type', 'timestamp', 'chat_session__user']
    search_fields = ['content', 'chat_session__session_name', 'chat_session__user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    list_select_related = ('chat_session', 'chat_session__user')
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'
    
    fieldsets = (
        ('Message Information', {
            'fields': ('chat_session', 'message_type', 'content')
        }),
        ('API Data', {
            'fields': ('tokens_used',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )

admin.site.register(ChatBot, ChatBotAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
