from django.db import models
import logging
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from datetime import date
from django.utils import timezone
from .utils.dates import business_localdate
from django.templatetags.static import static
from .managers import TaskQuerySet
import os

USER_TYPE_CHOICES = [
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('employee', 'Employee'),
]

class CustomUser(AbstractUser):
    """
    Custom user model with role-based access:
    - Admin: Can manage all users, assign managers, but cannot create tasks.
    - Manager: Can manage employees, assign tasks, approve/disapprove tasks.
    - Employee: Can only create tasks for themselves, is supervised by a manager.
    The 'under_supervision' field points to the user's direct supervisor (manager).
    """
    email = models.EmailField(unique=True)  # Make email unique for authentication
    user_type = models.CharField(max_length=15, choices=USER_TYPE_CHOICES, db_index=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')
    created_date = models.DateField(auto_now_add=True)
    created_time = models.TimeField(auto_now_add=True)
    under_supervision = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_users')
    avatar = models.ImageField(upload_to='core/avatar', blank=True, null=True)

    def __str__(self):
        return self.username

    def get_subordinates(self):
        """Get all users under this user's supervision"""
        return CustomUser.objects.filter(under_supervision=self)

    def can_manage_user(self, target_user):
        """Check if this user can manage the target user"""
        if self.user_type == 'admin':
            return True
        elif self.user_type == 'manager':
            return target_user.under_supervision == self
        return False

    def save(self, *args, **kwargs):
        """Ensure new users are active by default"""
        if not self.pk:  # New user being created
            self.is_active = True
        super().save(*args, **kwargs)

    @property
    def avatar_url(self):
        """Always returns a valid avatar URL - user uploaded or static PNG default"""
        # 1) Remote storages (e.g., Cloudinary): return URL directly
        try:
            if self.avatar:
                url = getattr(self.avatar, 'url', None)
                if url and ('cloudinary' in url or 'res.cloudinary.com' in url):
                    return url
                # 2) Local filesystem: return URL only if file exists
                avatar_path = getattr(self.avatar, 'path', None)
                if avatar_path and os.path.isfile(avatar_path) and url:
                    return url
        except Exception:
            # If anything goes wrong, fall back to static default
            pass
        # Otherwise, return the static PNG
        return static('core/img/avatar/blank_profile.png')
   

class KPI(models.Model):
    """
    KPI model for managing Key Performance Indicators with weights
    Only managers can create, edit, and delete KPIs
    """
    name = models.CharField(max_length=100, verbose_name="KPI Name")
    weight = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Weight (%)",
        help_text="Weight percentage for this KPI in employee progress calculation (0-100%)"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Description of what this KPI measures"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether this KPI is active and used in calculations"
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="Sort Order",
        help_text="Order in which KPIs are displayed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "KPI"
        verbose_name_plural = "KPIs"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate that total weights don't exceed 100% for the same manager"""
        from django.core.exceptions import ValidationError
        
        if self.created_by and self.weight > 0:
            # Get total weight of other KPIs by the same manager
            other_kpis_weight = KPI.objects.filter(
                created_by=self.created_by,
                is_active=True
            ).exclude(pk=self.pk if self.pk else None).aggregate(
                total_weight=models.Sum('weight')
            )['total_weight'] or 0
            
            total_weight = other_kpis_weight + self.weight
            if total_weight > 100:
                raise ValidationError(
                    f"Total KPI weights cannot exceed 100%. "
                    f"Current total: {other_kpis_weight}%, "
                    f"this KPI: {self.weight}%, "
                    f"total would be: {total_weight}%"
                )
    
    @classmethod
    def get_total_weight_for_manager(cls, manager):
        """Get total weight of all active KPIs for a manager"""
        return cls.objects.filter(
            created_by=manager,
            is_active=True
        ).aggregate(total_weight=models.Sum('weight'))['total_weight'] or 0
    
    @classmethod
    def get_available_weight_for_manager(cls, manager):
        """Get available weight percentage for a manager"""
        return 100 - cls.get_total_weight_for_manager(manager)


class EmployeeProgress(models.Model):
    """
    Model to track employee progress based on KPI performance
    """
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name="Employee"
    )
    manager = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='managed_progress',
        verbose_name="Manager"
    )
    period_start = models.DateField(verbose_name="Period Start Date")
    period_end = models.DateField(verbose_name="Period End Date")
    
    # Calculated progress scores
    total_progress_score = models.FloatField(
        null=True, blank=True,
        verbose_name="Total Progress Score (%)",
        help_text="Overall progress score calculated from KPI performance"
    )
    
    # Progress calculation details
    calculation_date = models.DateTimeField(auto_now_add=True)
    calculated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='calculated_progress',
        verbose_name="Calculated By"
    )
    
    # Progress breakdown by KPI
    progress_breakdown = models.JSONField(
        default=dict,
        verbose_name="Progress Breakdown",
        help_text="Detailed breakdown of progress by KPI"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes about the progress calculation"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Employee Progress"
        verbose_name_plural = "Employee Progress Records"
        ordering = ['-period_end', '-created_at']
        unique_together = ['employee', 'manager', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.period_start} to {self.period_end}"
    
    def calculate_progress(self):
        """
        Calculate employee progress based on KPI performance
        Formula: Employee Progress Score = (Average Project KPI Score × Project KPI Weight) + (Average HSE KPI Score × HSE KPI Weight) + ...
        """
        from django.db.models import Avg, Sum, Count
        
        # Get all active KPIs for the manager
        manager_kpis = KPI.objects.filter(
            created_by=self.manager,
            is_active=True
        ).order_by('sort_order')
        
        if not manager_kpis.exists():
            return None
        
        # Get CLOSED and evaluated tasks for this employee in the period
        tasks = Task.objects.filter(
            responsible=self.employee,
            completion_date__date__gte=self.period_start,
            completion_date__date__lte=self.period_end,
            status='closed',
            evaluation_status='evaluated',
            final_score__isnull=False
        )
        
        progress_breakdown = {}
        total_weighted_score = 0
        total_weight = 0
        
        for kpi in manager_kpis:
            # Get tasks for this specific KPI
            kpi_tasks = tasks.filter(kpi=kpi)
            
            if kpi_tasks.exists():
                # Per-task weighting: sum(final_score * weight) over tasks
                task_count = kpi_tasks.count()
                avg_score = kpi_tasks.aggregate(avg_score=Avg('final_score'))['avg_score']
                sum_scores = kpi_tasks.aggregate(total_score=Sum('final_score'))['total_score'] or 0
                # Contribution of this KPI across all its tasks (no /100 here)
                weighted_score = float(sum_scores) * float(kpi.weight)
                
                # Convert tasks to JSON-serializable format
                tasks_data = []
                for task in kpi_tasks:
                    tasks_data.append({
                        'id': task.id,
                        'issue_action': task.issue_action,
                        'final_score': task.final_score,
                        'completion_date': task.completion_date.isoformat() if task.completion_date else None
                    })
                
                progress_breakdown[kpi.name] = {
                    'kpi_id': kpi.id,
                    'weight': kpi.weight,
                    'task_count': task_count,
                    'average_score': round(avg_score, 2),
                    'weighted_score': round(weighted_score, 2),
                    'tasks': tasks_data
                }
                
                total_weighted_score += weighted_score
                # Denominator sums KPI weight for each task under this KPI
                total_weight += float(kpi.weight) * float(task_count)
            else:
                # No CLOSED tasks for this KPI in the period; do not include its weight
                progress_breakdown[kpi.name] = {
                    'kpi_id': kpi.id,
                    'weight': kpi.weight,
                    'task_count': 0,
                    'average_score': 0,
                    'weighted_score': 0,
                    'tasks': []
                }
        
        # Calculate total progress score using per-task weighting
        if total_weight > 0:
            total_progress_score = (total_weighted_score / total_weight)
        else:
            total_progress_score = 0
        
        # Update the record
        self.total_progress_score = round(total_progress_score, 2)
        self.progress_breakdown = progress_breakdown
        self.calculated_by = self.manager
        
        return {
            'total_progress_score': self.total_progress_score,
            'progress_breakdown': progress_breakdown,
            'total_weight': total_weight
        }
    
    @classmethod
    def calculate_employee_progress(cls, employee, manager, period_start, period_end, force_recalculate=False):
        """
        Calculate or get existing progress for an employee
        """
        progress_record, created = cls.objects.get_or_create(
            employee=employee,
            manager=manager,
            period_start=period_start,
            period_end=period_end,
            defaults={'calculated_by': manager}
        )
        
        if created or force_recalculate:
            result = progress_record.calculate_progress()
            if result:
                progress_record.save()
                return progress_record
        
        return progress_record

class QualityType(models.Model):
    """
    QualityType model for managing quality assessment types
    Only admins can create, edit, and delete quality types
    Managers can only use quality types created by admins for task evaluation
    """
    name = models.CharField(max_length=100)
    percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        verbose_name="Percentage",
        help_text="Quality type percentage (0-100)"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Description of this quality level"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether this quality type is available for use"
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="Sort Order",
        help_text="Order in which quality types are displayed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Quality Type"
        verbose_name_plural = "Quality Types"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name
    
    @classmethod
    def get_active_quality_types(cls):
        """Get active quality types for forms and templates"""
        return cls.objects.filter(is_active=True)

# Task-related choices
PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]

TASK_STATUS_CHOICES = [
    ('open', 'Open'),
    ('closed', 'Closed'),
    ('due', 'Due'),
]

APPROVAL_STATUS_CHOICES = [
    ('approved', 'Approved'),
    ('disapproved', 'Disapproved'),
]

EVALUATION_STATUS_CHOICES = [
    ('pending', 'Pending Evaluation'),
    ('evaluated', 'Evaluated'),
]

class TaskPriorityType(models.Model):
    """
    Admin-configurable task priority types with multipliers
    """
    name = models.CharField(max_length=100, verbose_name="Priority Name")
    code = models.CharField(
        max_length=20, 
        unique=True,
        verbose_name="Priority Code",
        help_text="Unique code for this priority (e.g., 'low', 'medium', 'high')"
    )
    multiplier = models.FloatField(
        default=1.0,
        verbose_name="Priority Multiplier",
        help_text="Multiplier applied to quality score (e.g., 1.2 = +20%)"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Description of when to use this priority level"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Whether this priority type is available for use"
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="Sort Order",
        help_text="Order in which priorities are displayed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Task Priority Type"
        verbose_name_plural = "Task Priority Types"
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_choices(cls):
        """Get choices for forms and templates"""
        return [(priority.code, priority.name) for priority in cls.objects.filter(is_active=True)]
    
    @classmethod
    def get_default_priority(cls):
        """Get the default priority (first active priority)"""
        return cls.objects.filter(is_active=True).first()

class TaskEvaluationSettings(models.Model):
    """
    Admin-configurable settings for automatic task evaluation
    """
    # Evaluation formula configuration
    formula_name = models.CharField(
        max_length=100,
        default="Standard Evaluation Formula",
        verbose_name="Formula Name",
        help_text="Name of the evaluation formula"
    )
    
    # Base formula components
    use_quality_score = models.BooleanField(
        default=True,
        verbose_name="Use Quality Score",
        help_text="Include quality score in evaluation"
    )
    use_priority_multiplier = models.BooleanField(
        default=True,
        verbose_name="Use Priority Multiplier",
        help_text="Apply priority multiplier to quality score"
    )
    use_time_bonus_penalty = models.BooleanField(
        default=True,
        verbose_name="Use Time Bonus/Penalty",
        help_text="Apply early/late completion bonuses/penalties"
    )
    use_manager_closure_penalty = models.BooleanField(
        default=True,
        verbose_name="Use Manager Closure Penalty",
        help_text="Apply penalty when manager closes incomplete task"
    )
    
    # Early completion bonus
    early_completion_bonus_per_day = models.FloatField(
        default=1.0,
        verbose_name="Early Completion Bonus per Day (%)",
        help_text="Bonus percentage per day for early completion"
    )
    max_early_completion_bonus = models.FloatField(
        default=5.0,
        verbose_name="Maximum Early Completion Bonus (%)",
        help_text="Maximum bonus percentage for early completion"
    )
    
    # Late completion penalty
    late_completion_penalty_per_day = models.FloatField(
        default=2.0,
        verbose_name="Late Completion Penalty per Day (%)",
        help_text="Penalty percentage per day for late completion"
    )
    max_late_completion_penalty = models.FloatField(
        default=20.0,
        verbose_name="Maximum Late Completion Penalty (%)",
        help_text="Maximum penalty percentage for late completion"
    )
    
    # Manager closure penalty
    manager_closure_penalty = models.FloatField(
        default=20.0,
        verbose_name="Manager Closure Penalty (%)",
        help_text="Penalty percentage when manager closes incomplete task"
    )
    
    # Evaluation formula
    evaluation_formula = models.CharField(
        max_length=500,
        default="Final Score = (Quality Score × Priority Multiplier) ± Time Bonus/Penalty",
        verbose_name="Evaluation Formula Description",
        help_text="Description of the evaluation formula for reference"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Task Evaluation Settings"
        verbose_name_plural = "Task Evaluation Settings"
    
    def __str__(self):
        return f"Task Evaluation Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def get_settings(cls):
        """Get the current evaluation settings, create default if none exist"""
        settings = cls.objects.first()
        if not settings:
            settings = cls.objects.create()
        return settings

class Task(models.Model):
    """
    Task model according to exact requirements:
    - Issue/Action: Task description
    - Responsible: Assigned employee
    - Priority: Low/Medium/High (only managers choose)
    - KPI: Project/Base Layer/Troubleshooting/HSE/Deliverable/Development (only managers choose)
    - Quality: Poor/Below Average/Good/Excellent (only managers evaluate)
    - Start Date: When task starts
    - Close Date: When task should be completed (only managers choose)
    - Created By: Who created the task
    - Status: Open/Closed/Due (decided by date and submission)
    - Percentage of completion: Only managers set
    - Comments: Only managers can add
    - Approval Status: Approved/Disapproved (only managers)
    - File upload: For task attachments
    """
    issue_action = models.CharField(max_length=500, verbose_name="Issue/Action", null=True, blank=True)
    responsible = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='assigned_tasks',
        verbose_name="Responsible",
        null=True, blank=True
    )
    priority = models.ForeignKey(
        TaskPriorityType,
        on_delete=models.SET_NULL,
        verbose_name="Priority",
        null=True, blank=True
    )
    kpi = models.ForeignKey(
        KPI,
        on_delete=models.SET_NULL,
        verbose_name="KPI",
        null=True, blank=True
    )
    quality = models.ForeignKey(
        QualityType,
        on_delete=models.SET_NULL,
        verbose_name="Quality",
        null=True, blank=True
    )
    start_date = models.DateField(verbose_name="Start Date", null=True, blank=True, db_index=True)
    target_date = models.DateField(verbose_name="Target Date", null=True, blank=True, help_text="Expected completion date set at task creation", db_index=True)
    close_date = models.DateField(verbose_name="Close Date", null=True, blank=True, help_text="Actual completion date set by manager during evaluation", db_index=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='created_tasks',
        verbose_name="Created By",
        null=True, blank=True
    )
    status = models.CharField(
        max_length=10, 
        choices=TASK_STATUS_CHOICES, 
        default='open',
        verbose_name="Status",
        null=True, blank=True,
        db_index=True
    )
    percentage_completion = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], 
        default=0,
        verbose_name="Percentage of Completion",
        null=True, blank=True
    )
    comments = models.TextField(blank=True, null=True, verbose_name="Comments")
    approval_status = models.CharField(
        max_length=15, 
        choices=APPROVAL_STATUS_CHOICES, 
        default='disapproved',
        verbose_name="Approval Status",
        null=True, blank=True,
        db_index=True
    )
    file_upload = models.FileField(
        upload_to='core/task_files/', 
        blank=True, 
        null=True,
        verbose_name="File Upload"
    )
    # Optional text submission provided by the employee when no file is attached
    employee_submission = models.TextField(
        blank=True,
        null=True,
        verbose_name="Employee Submission",
        help_text="Employee-provided textual submission when no file is attached"
    )
    employee_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Employee Submission Timestamp",
        help_text="When the employee last submitted content for manager evaluation/approval"
    )
    evaluation_status = models.CharField(
        max_length=20, 
        choices=EVALUATION_STATUS_CHOICES, 
        default='pending',
        verbose_name="Evaluation Status",
        db_index=True
    )
    quality_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)], 
        null=True, blank=True,
        verbose_name="Quality Score (1-10)"
    )
    evaluation_comments = models.TextField(
        blank=True, null=True,
        verbose_name="Evaluation Comments"
    )
    evaluated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='evaluated_tasks',
        verbose_name="Evaluated By"
    )
    evaluated_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Evaluation Date"
    )
    
    # Automatic evaluation fields
    completion_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Completion Date",
        help_text="Date when task was actually completed"
    )
    final_score = models.FloatField(
        null=True, blank=True,
        verbose_name="Final Score (%)",
        help_text="Automatically calculated final score out of 100%"
    )
    quality_score_calculated = models.FloatField(
        null=True, blank=True,
        verbose_name="Quality Score (Calculated)",
        help_text="Quality score from QualityType percentage"
    )
    priority_multiplier = models.FloatField(
        null=True, blank=True,
        verbose_name="Priority Multiplier",
        help_text="Multiplier applied based on task priority"
    )
    time_bonus_penalty = models.FloatField(
        null=True, blank=True,
        verbose_name="Time Bonus/Penalty (%)",
        help_text="Bonus for early completion or penalty for late completion"
    )
    manager_closure_penalty_applied = models.BooleanField(
        default=False,
        verbose_name="Manager Closure Penalty Applied",
        help_text="Whether manager closure penalty was applied"
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        indexes = [
            models.Index(fields=['created_date'], name='task_created_date_idx'),
        ]

    # Custom queryset/manager for common filters
    objects = TaskQuerySet.as_manager()

    def __str__(self):
        return f"{self.issue_action} - {self.responsible.get_full_name()}"

    def save(self, *args, **kwargs):
        # Store original status and completion for comparison
        if self.pk:
            try:
                original_task = Task.objects.get(pk=self.pk)
                original_status = original_task.status
                original_completion = original_task.percentage_completion
                original_quality = original_task.quality
            except Task.DoesNotExist:
                original_status = None
                original_completion = None
                original_quality = None
        else:
            original_status = None
            original_completion = None
            original_quality = None
        
        # Auto-update status based on dates and completion
        if self.percentage_completion >= 100:
            self.status = 'closed'
        elif self.target_date and self.target_date < business_localdate():
            self.status = 'due'
        else:
            self.status = 'open'
        
        # Save the task
        super().save(*args, **kwargs)
        
        # Auto-evaluate task if quality is set and task is completed
        if (self.quality and 
            self.percentage_completion >= 100 and 
            self.evaluation_status == 'pending'):
            self.apply_automatic_evaluation()
            super().save(update_fields=[
                'quality_score_calculated', 'priority_multiplier', 
                'time_bonus_penalty', 'final_score', 'manager_closure_penalty_applied',
                'completion_date', 'evaluation_status'
            ])
        
        # Auto-evaluate task if quality is changed and task is already completed
        if (self.quality and 
            self.percentage_completion >= 100 and 
            original_quality != self.quality and
            self.evaluation_status == 'evaluated'):
            self.apply_automatic_evaluation()
            super().save(update_fields=[
                'quality_score_calculated', 'priority_multiplier', 
                'time_bonus_penalty', 'final_score', 'manager_closure_penalty_applied'
            ])
        
        # Notify employee if status changed automatically
        if original_status and original_status != self.status and self.responsible:
            status_messages = {
                'open': 'is now open',
                'due': 'is now due',
                'closed': 'has been completed'
            }
            
            if self.status in status_messages:
                notification_message = f"Your task '{self.issue_action[:40]}...' {status_messages[self.status]}."
                
                # Import here to avoid circular imports
                from .models import Notification
                Notification.objects.create(
                    recipient=self.responsible,
                    sender=None,  # System notification
                    message=notification_message,
                    link=f"/projects/task/{self.id}/"
                )

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        return self.target_date and self.target_date < business_localdate() and self.status != 'closed'

    @property
    def has_reminder(self):
        """Check if task has any reminders (regardless of sent status or date)"""
        return self.reminders.exists()

    @property
    def can_be_approved_by(self):
        """Return users who can approve this task"""
        if self.created_by.user_type == 'manager':
            return [self.created_by]
        return []
    
    def calculate_automatic_evaluation(self, manager_closure=False):
        """
        Calculate automatic evaluation score based on quality, priority, and timing
        """
        if not self.quality:
            return None
        
        settings = TaskEvaluationSettings.get_settings()
        
        # 1. Quality Score (from QualityType percentage)
        if settings.use_quality_score and self.quality:
            quality_score = self.quality.percentage
        else:
            quality_score = 0
        
        # 2. Priority Multiplier
        if settings.use_priority_multiplier and self.priority:
            priority_multiplier = self.priority.multiplier
        else:
            priority_multiplier = 1.0
        
        # 3. Time Bonus/Penalty
        time_bonus_penalty = 0
        if settings.use_time_bonus_penalty and self.completion_date and self.target_date:
            completion_date = self.completion_date.date()
            target_date = self.target_date
            
            if completion_date < target_date:
                # Early completion - calculate bonus
                days_early = (target_date - completion_date).days
                bonus_per_day = settings.early_completion_bonus_per_day
                max_bonus = settings.max_early_completion_bonus
                time_bonus_penalty = min(days_early * bonus_per_day, max_bonus)
            elif completion_date > target_date:
                # Late completion - calculate penalty
                days_late = (completion_date - target_date).days
                penalty_per_day = settings.late_completion_penalty_per_day
                max_penalty = settings.max_late_completion_penalty
                time_bonus_penalty = -min(days_late * penalty_per_day, max_penalty)
        
        # 4. Manager closure penalty
        manager_closure_penalty_applied = False
        if settings.use_manager_closure_penalty and manager_closure and self.percentage_completion < 100:
            time_bonus_penalty -= settings.manager_closure_penalty
            manager_closure_penalty_applied = True
        
        # 5. Calculate final score using the formula: Final Score = (Quality Score × Priority Multiplier) ± Time Bonus/Penalty
        base_score = quality_score * priority_multiplier
        final_score = base_score + time_bonus_penalty
        
        # Ensure score is within 0-100 range
        final_score = max(0, min(100, final_score))
        
        return {
            'quality_score': quality_score,
            'priority_multiplier': priority_multiplier,
            'time_bonus_penalty': time_bonus_penalty,
            'final_score': final_score,
            'manager_closure_penalty_applied': manager_closure_penalty_applied
        }
    
    def apply_automatic_evaluation(self, manager_closure=False):
        """
        Apply automatic evaluation and save the results
        """
        if not self.quality:
            return False
        
        evaluation_result = self.calculate_automatic_evaluation(manager_closure)
        if not evaluation_result:
            return False
        
        # Update task fields
        self.quality_score_calculated = evaluation_result['quality_score']
        self.priority_multiplier = evaluation_result['priority_multiplier']
        self.time_bonus_penalty = evaluation_result['time_bonus_penalty']
        self.final_score = evaluation_result['final_score']
        self.manager_closure_penalty_applied = evaluation_result['manager_closure_penalty_applied']
        
        # Set completion date if not already set
        if not self.completion_date and self.percentage_completion >= 100:
            from django.utils import timezone
            self.completion_date = timezone.now()
        
        # Update evaluation status
        self.evaluation_status = 'evaluated'

        # --- Audit logging (non-invasive) ---
        try:
            audit_logger = logging.getLogger('core.audit')
            audit_logger.info(
                'task_evaluated task_id=%s responsible_id=%s evaluated_by_id=%s manager_closure=%s '
                'quality_score=%s priority_multiplier=%s time_bonus_penalty=%s final_score=%s '
                'completion_date=%s target_date=%s percentage_completion=%s',
                getattr(self, 'id', None),
                getattr(self.responsible, 'id', None) if hasattr(self, 'responsible') else None,
                getattr(self.evaluated_by, 'id', None) if hasattr(self, 'evaluated_by') else None,
                bool(manager_closure),
                evaluation_result.get('quality_score'),
                evaluation_result.get('priority_multiplier'),
                evaluation_result.get('time_bonus_penalty'),
                evaluation_result.get('final_score'),
                getattr(self, 'completion_date', None),
                getattr(self, 'target_date', None),
                getattr(self, 'percentage_completion', None),
            )
        except Exception:  # best-effort logging only
            pass
        
        return True

    def can_user_manage(self, user):
        """Check if user can manage this task"""
        if user.user_type == 'admin':
            return False  # Admins cannot manage tasks
        elif user.user_type == 'manager':
            # Managers can manage tasks assigned to themselves OR their subordinates
            return self.responsible == user or self.responsible.under_supervision == user
        elif user.user_type == 'employee':
            # Employees can only view their own tasks
            return self.responsible == user
        return False

    def can_user_edit(self, user):
        """Check if user can edit this task"""
        if user.user_type == 'admin':
            return False  # Admins cannot edit tasks
        elif user.user_type == 'manager':
            # Managers can only edit tasks assigned to their subordinates
            # They CANNOT edit tasks assigned to themselves (only their supervisor can)
            return self.responsible.under_supervision == user
        elif user.user_type == 'employee':
            # Employees cannot edit tasks
            return False
        return False

    def can_user_upload_file(self, user):
        """Check if user can upload files to this task"""
        if user.user_type == 'admin':
            return False  # Admins cannot upload files
        elif user.user_type == 'manager':
            # Managers can upload files to their own tasks OR tasks of their subordinates
            return self.responsible == user or self.responsible.under_supervision == user
        elif user.user_type == 'employee':
            # Employees can only upload files to their own tasks, and only if the task is not closed
            return self.responsible == user and self.status != 'closed'
        return False

    def can_user_download_file(self, user):
        """Check if user can download files from this task"""
        if user.user_type == 'admin':
            return False  # Admins cannot download files
        elif user.user_type == 'manager':
            # Managers can download files from their own tasks OR tasks of their subordinates
            return self.responsible == user or self.responsible.under_supervision == user
        elif user.user_type == 'employee':
            # Employees can only download files from their own tasks
            return self.responsible == user
        return False

    def can_user_evaluate(self, user):
        """Check if user can evaluate this task"""
        if user.user_type == 'admin':
            return False  # Admins cannot evaluate tasks
        elif user.user_type == 'manager':
            # Managers can only evaluate tasks assigned to their subordinates
            # They CANNOT evaluate tasks assigned to themselves (only their supervisor can)
            return self.responsible.under_supervision == user
        elif user.user_type == 'employee':
            # Employees cannot evaluate tasks
            return False
        return False

    def can_user_create(self, user):
        """Check if user can create tasks"""
        if user.user_type == 'admin':
            return False  # Admins cannot create tasks
        elif user.user_type == 'manager':
            return True  # Managers can create tasks
        elif user.user_type == 'employee':
            return True  # Employees can create tasks for themselves
        return False

    @classmethod
    def update_all_statuses(cls):
        """
        Update statuses for all tasks based on current date and completion
        Returns a dictionary with update statistics
        """
        today = business_localdate()
        updates = {
            'closed': 0,
            'due': 0,
            'open': 0,
            'total_updated': 0
        }
        
        # Import here to avoid circular imports
        from .models import Notification
        
        # Update tasks to 'closed' (100% completion)
        closed_tasks = cls.objects.filter(
            percentage_completion__gte=100,
            status__in=['open', 'due']
        )
        for task in closed_tasks:
            task.status = 'closed'
            task.save()
            updates['closed'] += 1
            updates['total_updated'] += 1
            
            # Notify employee
            if task.responsible:
                notification_message = f"Your task '{task.issue_action[:40]}...' has been completed automatically (100% completion)."
                Notification.objects.create(
                    recipient=task.responsible,
                    sender=None,  # System notification
                    message=notification_message,
                    link=f"/projects/task/{task.id}/"
                )
        
        # Update tasks to 'due' (past target date but not 100% complete)
        due_tasks = cls.objects.filter(
            target_date__lt=today,
            percentage_completion__lt=100,
            status='open'
        )
        for task in due_tasks:
            task.status = 'due'
            task.save()
            updates['due'] += 1
            updates['total_updated'] += 1
            
            # Notify employee
            if task.responsible:
                notification_message = f"Your task '{task.issue_action[:40]}...' is now due (past target date)."
                Notification.objects.create(
                    recipient=task.responsible,
                    sender=None,  # System notification
                    message=notification_message,
                    link=f"/projects/task/{task.id}/"
                )
        
        # Update tasks to 'open' (not past target date and not 100% complete)
        open_tasks = cls.objects.filter(
            target_date__gte=today,
            percentage_completion__lt=100,
            status='due'
        )
        for task in open_tasks:
            task.status = 'open'
            task.save()
            updates['open'] += 1
            updates['total_updated'] += 1
            
            # Notify employee
            if task.responsible:
                notification_message = f"Your task '{task.issue_action[:40]}...' is now open (not yet due by target date)."
                Notification.objects.create(
                    recipient=task.responsible,
                    sender=None,  # System notification
                    message=notification_message,
                    link=f"/projects/task/{task.id}/"
                )
        
        return updates


class Notification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read', 'created_at'], name='notif_rec_read_created_idx'),
        ]

    def __str__(self):
        return f"To: {self.recipient.get_full_name()} | {self.message[:40]}..."


class TaskReminder(models.Model):
    """One-off scheduled reminder for a task.

    Uses the existing Notification + email signal to actually send email when
    the reminder is triggered. Keeping it separate avoids touching Task logic.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reminders')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='task_reminders')
    scheduled_for = models.DateField(db_index=True)
    message = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_task_reminders')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_for', '-created_at']
        indexes = [
            models.Index(fields=['scheduled_for', 'recipient'], name='reminder_sched_recipient_idx'),
        ]

    def __str__(self):
        return f"Reminder for Task #{self.task_id} to {self.recipient.get_full_name()} on {self.scheduled_for}"

    def mark_sent(self):
        from django.utils import timezone
        self.sent_at = timezone.now()
        self.save(update_fields=['sent_at'])