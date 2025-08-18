from django import forms
from core.models import CustomUser, Task, PRIORITY_CHOICES, TASK_STATUS_CHOICES, APPROVAL_STATUS_CHOICES, EVALUATION_STATUS_CHOICES, KPI, QualityType, TaskPriorityType, TaskEvaluationSettings
from django.contrib.auth.forms import UserCreationForm
from datetime import date
from django.db import models
import re
from django.core.cache import cache
import random
import string

# --- Custom Email Login Form ---
class EmailLoginForm(forms.Form):
    """
    Custom login form that uses email instead of username
    """
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )

class TwoFactorForm(forms.Form):
    """
    Simple email OTP form. Stores codes in cache for a short period.
    """
    code = forms.CharField(
        label='Verification Code',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit code',
            'autocomplete': 'one-time-code'
        })
    )

    @staticmethod
    def generate_code(length: int = 6) -> str:
        digits = string.digits
        return ''.join(random.choice(digits) for _ in range(length))

# --- User Registration Form ---
class UserRegistrationForm(UserCreationForm):
    """
    Custom user registration form with role-based fields
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    user_type = forms.ChoiceField(
        choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('employee', 'Employee'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter designation'
        })
    )
    under_supervision = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='manager'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=False,  # Changed from True to False since it's auto-generated
        widget=forms.HiddenInput(),  # Hide the username field since it will be auto-generated
        help_text='Username will be automatically generated from email address'
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'user_type', 'designation', 'under_supervision', 
            'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        
        # Override label_from_instance to show usernames instead of full names
        self.fields['under_supervision'].label_from_instance = lambda obj: obj.username
        
        # Role-based field visibility
        if self.user:
            if self.user.user_type == 'admin':
                # Admin can create admins, managers, and employees
                self.fields['user_type'].choices = [
                    ('admin', 'Admin'),
                    ('manager', 'Manager'),
                    ('employee', 'Employee'),
                ]
            elif self.user.user_type == 'manager':
                # Managers can only create employees under their supervision
                self.fields['user_type'].choices = [('employee', 'Employee')]
                self.fields['under_supervision'].queryset = CustomUser.objects.filter(id=self.user.id)
                self.fields['under_supervision'].initial = self.user
                self.fields['under_supervision'].widget.attrs['readonly'] = True
                # Ensure username display even for single user
                self.fields['under_supervision'].label_from_instance = lambda obj: obj.username

        # Set under_supervision requirements based on user_type
        user_type_value = self.initial.get('user_type') or self.data.get('user_type')
        if user_type_value == 'admin':
            self.fields['under_supervision'].widget = forms.HiddenInput()
            self.fields['under_supervision'].required = False
            self.initial['under_supervision'] = None
        elif user_type_value == 'manager':
            self.fields['under_supervision'].required = False
        elif user_type_value == 'employee':
            self.fields['under_supervision'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        
        # Auto-generate username from email
        username = email.split('@')[0]  # Get part before @
        
        # Clean the username (remove special characters, keep only letters, numbers, dots, hyphens, underscores)
        username = re.sub(r'[^a-zA-Z0-9._-]', '', username)
        
        # Ensure username is not empty after cleaning
        if not username:
            username = 'user'
        
        # Ensure username starts with a letter or number (Django requirement)
        if username and not username[0].isalnum():
            username = 'user' + username
        
        # Limit username length to 150 characters (Django requirement)
        if len(username) > 150:
            username = username[:150]
        
        # Handle duplicate usernames by adding a number
        original_username = username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            # Ensure we don't exceed 150 characters when adding counter
            suffix = str(counter)
            if len(original_username) + len(suffix) > 150:
                original_username = original_username[:150-len(suffix)]
            username = f"{original_username}{suffix}"
            counter += 1
            if counter > 999:  # Prevent infinite loop
                raise forms.ValidationError("Unable to generate unique username. Please try a different email address.")
        
        # Set the generated username
        self.cleaned_data['username'] = username
        
        return email

    def clean(self):
        """Ensure username is set from email"""
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        
        if email and not cleaned_data.get('username'):
            # Auto-generate username from email if not already set
            username = email.split('@')[0]  # Get part before @
            
            # Clean the username (remove special characters, keep only letters, numbers, dots, hyphens, underscores)
            username = re.sub(r'[^a-zA-Z0-9._-]', '', username)
            
            # Ensure username is not empty after cleaning
            if not username:
                username = 'user'
            
            # Ensure username starts with a letter or number (Django requirement)
            if username and not username[0].isalnum():
                username = 'user' + username
            
            # Limit username length to 150 characters (Django requirement)
            if len(username) > 150:
                username = username[:150]
            
            # Handle duplicate usernames by adding a number
            original_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                # Ensure we don't exceed 150 characters when adding counter
                suffix = str(counter)
                if len(original_username) + len(suffix) > 150:
                    original_username = original_username[:150-len(suffix)]
                username = f"{original_username}{suffix}"
                counter += 1
                if counter > 999:  # Prevent infinite loop
                    raise forms.ValidationError("Unable to generate unique username. Please try a different email address.")
            
            cleaned_data['username'] = username
        
        # Final validation: ensure username is set
        if not cleaned_data.get('username'):
            raise forms.ValidationError("Username is required. Please provide a valid email address.")
        
        return cleaned_data

    def clean_username(self):
        """Validate the auto-generated username"""
        username = self.cleaned_data.get('username')
        
        # If username is empty, it will be set in the clean() method
        if not username:
            return username
        
        # Import Django's username validator
        from django.contrib.auth.validators import UnicodeUsernameValidator
        validator = UnicodeUsernameValidator()
        
        try:
            validator(username)
        except Exception as e:
            raise forms.ValidationError(f"Generated username '{username}' is invalid: {str(e)}")
        
        return username

    def clean_under_supervision(self):
        under_supervision = self.cleaned_data.get('under_supervision', None)
        user_type = self.cleaned_data.get('user_type')
        if user_type == 'admin':
            return None
        if user_type == 'manager':
            # Managers may or may not have a supervisor
            return under_supervision
        if user_type == 'employee':
            if not under_supervision:
                raise forms.ValidationError("Employees must be under supervision of a manager.")
        if self.user and self.user.user_type == 'manager':
            if under_supervision != self.user:
                raise forms.ValidationError("You can only assign users to your supervision.")
        return under_supervision

    def save(self, commit=True):
        user = super(UserRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        
        # Set created_by to current user
        if self.user:
            user.created_by = self.user
        
        # Ensure admin has no under_supervision
        if user.user_type == 'admin':
            user.under_supervision = None
        
        if commit:
            user.save()
        return user

# --- User Profile Edit Form ---
class UserProfileEditForm(forms.ModelForm):
    """
    Form for editing user profiles with role-based field restrictions
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter designation'
        })
    )
    user_type = forms.ChoiceField(
        choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('employee', 'Employee'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    under_supervision = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='manager'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'designation', 'user_type', 'under_supervision', 'avatar']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(UserProfileEditForm, self).__init__(*args, **kwargs)
        
        # Override label_from_instance to show usernames instead of full names
        if 'under_supervision' in self.fields:
            self.fields['under_supervision'].label_from_instance = lambda obj: obj.username
        
        # Role-based field restrictions
        if self.user:
            if self.user.user_type in ['manager', 'employee']:
                # Managers and employees can only edit first_name, last_name, and avatar
                # Hide email, designation, user_type, and under_supervision fields
                if 'email' in self.fields:
                    del self.fields['email']
                if 'designation' in self.fields:
                    del self.fields['designation']
                if 'user_type' in self.fields:
                    del self.fields['user_type']
                if 'under_supervision' in self.fields:
                    del self.fields['under_supervision']
            elif self.user.user_type == 'admin':
                # Admins can edit all fields including user_type and under_supervision
                # Update under_supervision queryset to exclude the current user being edited
                if 'under_supervision' in self.fields and self.instance and self.instance.pk:
                    self.fields['under_supervision'].queryset = CustomUser.objects.filter(
                        user_type='manager'
                    ).exclude(pk=self.instance.pk)
                    # Ensure username display
                    self.fields['under_supervision'].label_from_instance = lambda obj: obj.username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.id if self.instance else None
        if CustomUser.objects.filter(email=email).exclude(id=user_id).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_under_supervision(self):
        under_supervision = self.cleaned_data.get('under_supervision', None)
        user_type = self.cleaned_data.get('user_type')
        
        if user_type == 'admin':
            return None
        elif user_type == 'manager':
            # Managers may or may not have a supervisor
            return under_supervision
        elif user_type == 'employee':
            if not under_supervision:
                raise forms.ValidationError("Employees must be under supervision of a manager.")
        
        return under_supervision

    def save(self, commit=True):
        user = super(UserProfileEditForm, self).save(commit=False)

        # If email changed (only present for admins), regenerate username from email
        # Use changed_data to reliably detect change even after ModelForm populates instance
        if 'email' in getattr(self, 'changed_data', []):
            new_email = self.cleaned_data.get('email')
            if new_email:
                base_username = new_email.split('@')[0]
                # Clean username: allow letters, numbers, dots, hyphens, underscores
                base_username = re.sub(r'[^a-zA-Z0-9._-]', '', base_username) or 'user'
                if not base_username[0].isalnum():
                    base_username = 'user' + base_username
                if len(base_username) > 150:
                    base_username = base_username[:150]

                # Ensure uniqueness, excluding the current instance
                candidate = base_username
                original = base_username
                counter = 1
                while CustomUser.objects.filter(username=candidate).exclude(pk=self.instance.pk).exists():
                    suffix = str(counter)
                    if len(original) + len(suffix) > 150:
                        original = original[:150 - len(suffix)]
                    candidate = f"{original}{suffix}"
                    counter += 1
                    if counter > 999:
                        # Fallback to a random suffix to avoid rare infinite loops
                        candidate = f"{original}{random.randint(1000, 9999)}"
                        break
                user.username = candidate

        # Ensure admin has no under_supervision
        if user.user_type == 'admin':
            user.under_supervision = None

        if commit:
            user.save()
        return user

class TaskRegistrationForm(forms.ModelForm):
    """
    Task registration form with role-based field visibility and permissions
    According to exact requirements:
    - Employees can only create tasks for themselves
    - Managers/Sub-managers can assign tasks to their subordinates
    - Only managers can set priority, KPI, quality, close date, percentage, comments, approval
    """
    issue_action = forms.CharField(
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Issue/Action Description'}),
        label="Issue/Action"
    )
    responsible = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='employee'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Responsible"
    )
    priority = forms.ModelChoiceField(
        queryset=TaskPriorityType.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Priority"
    )
    kpi = forms.ModelChoiceField(
        queryset=KPI.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="KPI"
    )
    quality = forms.ModelChoiceField(
        queryset=QualityType.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label="Quality"
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Start Date"
    )
    target_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Target Date",
        help_text="Expected completion date"
    )
    file_upload = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="File Upload"
    )

    class Meta:
        model = Task
        fields = [
            'issue_action', 'responsible', 'priority', 'kpi', 'quality', 
            'start_date', 'target_date', 'file_upload'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(TaskRegistrationForm, self).__init__(*args, **kwargs)
        
        # Role-based field visibility and permissions
        if self.user:
            if self.user.user_type == 'employee':
                # Employees can only create tasks for themselves
                self.fields['responsible'].queryset = CustomUser.objects.filter(id=self.user.id)
                self.fields['responsible'].initial = self.user
                self.fields['responsible'].widget.attrs['readonly'] = True
                
                # Hide manager-only fields for employees
                del self.fields['priority']
                del self.fields['kpi']
                del self.fields['quality']
                
                # Set default values for employee-created tasks
                self.fields['start_date'].initial = date.today()
                
            elif self.user.user_type in ['manager']:
                # Managers can create tasks for themselves (like employees) OR for their subordinates (like managers)
                # Include themselves and their subordinates in the responsible field
                subordinates = CustomUser.objects.filter(under_supervision=self.user)
                manager_and_subordinates = CustomUser.objects.filter(
                    models.Q(id=self.user.id) | models.Q(under_supervision=self.user)
                )
                self.fields['responsible'].queryset = manager_and_subordinates
                
                # Restrict KPIs to those created by this manager
                self.fields['kpi'].queryset = KPI.objects.filter(created_by=self.user)
                # Allow managers to use all quality types (created by admins)
                self.fields['quality'].queryset = QualityType.objects.all()
                

                
                # Remove quality field for managers at creation time (will be set during evaluation)
                if 'quality' in self.fields:
                    del self.fields['quality']

            elif self.user.user_type == 'admin':
                # Admins cannot create tasks
                raise forms.ValidationError("Admins cannot create tasks")

    def clean_responsible(self):
        responsible = self.cleaned_data.get('responsible')
        if self.user:
            if self.user.user_type == 'employee':
                # Employees can only assign tasks to themselves
                if responsible != self.user:
                    raise forms.ValidationError("Employees can only create tasks for themselves")
            elif self.user.user_type in ['manager']:
                # Managers can assign tasks to themselves OR their subordinates
                if responsible:
                    if responsible == self.user:
                        # Manager is trying to create a task for themselves
                        if not self.user.under_supervision:
                            raise forms.ValidationError("You cannot create a task for yourself unless you are under the supervision of another manager.")
                    elif responsible.under_supervision != self.user:
                        raise forms.ValidationError("You can only assign tasks to yourself or your subordinates")
        return responsible

    def clean_target_date(self):
        target_date = self.cleaned_data.get('target_date')
        start_date = self.cleaned_data.get('start_date')
        
        if target_date and start_date and target_date < start_date:
            raise forms.ValidationError("Target date cannot be before start date")
        
        return target_date

    def save(self, commit=True):
        task = super(TaskRegistrationForm, self).save(commit=False)
        
        # Set created_by to current user
        if self.user:
            task.created_by = self.user
        
        # Set default values for employee-created tasks
        if self.user and self.user.user_type == 'employee':
            # Set default priority if available
            default_priority = TaskPriorityType.objects.filter(is_active=True).first()
            if default_priority:
                task.priority = default_priority
            # Set default KPI if available
            default_kpi = KPI.objects.first()
            if default_kpi:
                task.kpi = default_kpi
            task.target_date = task.start_date  # Default target date to start date for employees
            task.percentage_completion = 0
            task.approval_status = 'pending'
        
        if commit:
            task.save()
        return task

class TaskEditForm(forms.ModelForm):
    """
    Form for editing tasks with role-based permissions
    """
    issue_action = forms.CharField(
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Issue/Action"
    )
    responsible = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='employee'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Responsible"
    )
    priority = forms.ModelChoiceField(
        queryset=TaskPriorityType.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Priority"
    )
    kpi = forms.ModelChoiceField(
        queryset=KPI.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="KPI"
    )
    quality = forms.ModelChoiceField(
        queryset=QualityType.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label="Quality"
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Start Date"
    )
    target_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Target Date",
        help_text="Expected completion date"
    )
    percentage_completion = forms.FloatField(
        min_value=0, 
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Percentage of Completion"
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control'}),
        required=False,
        label="Comments"
    )
    approval_status = forms.ChoiceField(
        choices=APPROVAL_STATUS_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Approval Status"
    )
    file_upload = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="File Upload"
    )

    class Meta:
        model = Task
        fields = [
            'issue_action', 'responsible', 'priority', 'kpi', 'quality', 
            'start_date', 'target_date', 'percentage_completion', 
            'comments', 'approval_status', 'file_upload'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(TaskEditForm, self).__init__(*args, **kwargs)
        
        # Role-based field permissions
        if self.user:
            if self.user.user_type == 'employee':
                # Employees cannot edit tasks
                raise forms.ValidationError("Employees cannot edit tasks")
            elif self.user.user_type in ['manager']:
                # Managers can only edit tasks assigned to their subordinates
                # They CANNOT edit tasks assigned to themselves (only their supervisor can)
                subordinates = CustomUser.objects.filter(under_supervision=self.user)
                self.fields['responsible'].queryset = subordinates
                # Restrict KPIs to those created by this manager
                self.fields['kpi'].queryset = KPI.objects.filter(created_by=self.user)
                # Allow managers to use all quality types (created by admins)
                self.fields['quality'].queryset = QualityType.objects.all()
            elif self.user.user_type == 'admin':
                # Admins cannot edit tasks
                raise forms.ValidationError("Admins cannot edit tasks")

    def clean_responsible(self):
        responsible = self.cleaned_data.get('responsible')
        if self.user and self.user.user_type in ['manager']:
            if responsible:
                if responsible.under_supervision != self.user:
                    raise forms.ValidationError("You can only assign tasks to your subordinates")
        return responsible

    def clean_target_date(self):
        target_date = self.cleaned_data.get('target_date')
        start_date = self.cleaned_data.get('start_date')
        
        if target_date and start_date and target_date < start_date:
            raise forms.ValidationError("Target date cannot be before start date")
        
        return target_date 

# --- KPI Management Forms ---
class KPIForm(forms.ModelForm):
    """
    Form for creating and editing KPIs with weights
    Only managers can use this form
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter KPI name'
        }),
        help_text="Name of the Key Performance Indicator"
    )
    
    weight = forms.FloatField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter weight percentage (0-100)',
            'step': '0.01'
        }),
        help_text="Weight percentage for this KPI in employee progress calculation"
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe what this KPI measures'
        }),
        required=False,
        help_text="Description of what this KPI measures"
    )
    
    sort_order = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter sort order'
        }),
        required=False,
        help_text="Order in which this KPI is displayed"
    )

    class Meta:
        model = KPI
        fields = ['name', 'weight', 'description', 'is_active', 'sort_order']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(KPIForm, self).__init__(*args, **kwargs)
        
        if self.user and self.user.user_type == 'manager':
            # Set initial weight to available weight if creating new KPI
            if not self.instance.pk:
                available_weight = KPI.get_available_weight_for_manager(self.user)
                self.fields['weight'].initial = available_weight
                self.fields['weight'].help_text += f" (Available: {available_weight}%)"

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        weight = cleaned_data.get('weight')
        # Ensure blank sort_order defaults to 0 to avoid DB null constraint errors
        sort_order = cleaned_data.get('sort_order')
        if sort_order in [None, '']:
            cleaned_data['sort_order'] = 0
        
        if self.user and self.user.user_type == 'manager':
            # Check for name uniqueness within the same manager's KPIs
            existing_kpi = KPI.objects.filter(
                name__iexact=name, 
                created_by=self.user
            ).exclude(pk=self.instance.pk if self.instance else None)
            if existing_kpi.exists():
                raise forms.ValidationError("You already have a KPI with this name.")
            
            # Validate total weight doesn't exceed 100%
            if weight:
                other_kpis_weight = KPI.objects.filter(
                    created_by=self.user,
                    is_active=True
                ).exclude(pk=self.instance.pk if self.instance else None).aggregate(
                    total_weight=models.Sum('weight')
                )['total_weight'] or 0
                
                total_weight = other_kpis_weight + weight
                if total_weight > 100:
                    raise forms.ValidationError(
                        f"Total KPI weights cannot exceed 100%. "
                        f"Current total: {other_kpis_weight}%, "
                        f"this KPI: {weight}%, "
                        f"total would be: {total_weight}%"
                    )
        
        return cleaned_data

    def save(self, commit=True):
        kpi = super(KPIForm, self).save(commit=False)
        if self.user:
            kpi.created_by = self.user
        if commit:
            kpi.save()
        return kpi

# --- QualityType Management Forms ---
class QualityTypeForm(forms.ModelForm):
    """
    Form for creating and editing Quality Types
    Only admins can use this form
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter quality type name'
        })
    )
    percentage = forms.FloatField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter percentage (0-100)',
            'step': '0.01'
        }),
        help_text="Quality type percentage (0-100)"
    )

    class Meta:
        model = QualityType
        fields = ['name', 'percentage']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(QualityTypeForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        # Check for uniqueness across all quality types (admin can manage all)
        if self.user and self.user.user_type == 'admin':
            existing_quality_type = QualityType.objects.filter(
                name__iexact=name
            ).exclude(pk=self.instance.pk if self.instance else None)
            if existing_quality_type.exists():
                raise forms.ValidationError("A quality type with this name already exists.")
        return name

    def clean_percentage(self):
        percentage = self.cleaned_data.get('percentage')
        if percentage is not None and (percentage < 0 or percentage > 100):
            raise forms.ValidationError("Percentage must be between 0 and 100.")
        return percentage

    def save(self, commit=True):
        quality_type = super(QualityTypeForm, self).save(commit=False)
        if self.user:
            quality_type.created_by = self.user
        if commit:
            quality_type.save()
        return quality_type 

class TaskPriorityTypeForm(forms.ModelForm):
    """
    Form for creating and editing Task Priority Types
    Only admins can use this form
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter priority name'
        }),
        help_text="Name of the priority level (e.g., 'Low', 'Medium', 'High')"
    )
    code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter unique code'
        }),
        help_text="Unique code for this priority (e.g., 'low', 'medium', 'high')"
    )
    multiplier = forms.FloatField(
        min_value=0.1,
        max_value=10.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter multiplier (e.g., 1.2 for +20%)',
            'step': '0.01'
        }),
        help_text="Multiplier applied to quality score (e.g., 1.2 = +20%)"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe when to use this priority level'
        }),
        required=False,
        help_text="Description of when to use this priority level"
    )
    sort_order = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter sort order'
        }),
        help_text="Order in which priorities are displayed"
    )
    
    class Meta:
        model = TaskPriorityType
        fields = ['name', 'code', 'multiplier', 'description', 'is_active', 'sort_order']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(TaskPriorityTypeForm, self).__init__(*args, **kwargs)
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        # Check for uniqueness
        existing_priority = TaskPriorityType.objects.filter(
            code__iexact=code
        ).exclude(pk=self.instance.pk if self.instance else None)
        if existing_priority.exists():
            raise forms.ValidationError("A priority type with this code already exists.")
        return code.lower()
    
    def clean_multiplier(self):
        multiplier = self.cleaned_data.get('multiplier')
        if multiplier is not None and multiplier <= 0:
            raise forms.ValidationError("Multiplier must be greater than 0.")
        return multiplier

class TaskEvaluationForm(forms.ModelForm):
    """
    Form for managers to evaluate tasks
    This form is used during task evaluation to set quality, close_date, and approval_status
    """
    quality = forms.ModelChoiceField(
        queryset=QualityType.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Quality Rating",
        help_text="Select the quality rating for this task"
    )
    close_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Close Date",
        help_text="Actual completion date",
        required=True
    )
    approval_status = forms.ChoiceField(
        choices=APPROVAL_STATUS_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Approval Status",
        required=True
    )
    evaluation_comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Evaluation comments...'}),
        required=False,
        label="Evaluation Comments"
    )

    class Meta:
        model = Task
        fields = ['quality', 'close_date', 'approval_status', 'evaluation_comments']

    def clean_close_date(self):
        close_date = self.cleaned_data.get('close_date')
        if close_date and close_date < self.instance.start_date:
            raise forms.ValidationError("Close date cannot be before start date")
        return close_date

    def __init__(self, *args, **kwargs):
        super(TaskEvaluationForm, self).__init__(*args, **kwargs)
        # Set initial close_date to today if not already set
        if not self.instance.close_date:
            self.fields['close_date'].initial = date.today()

class TaskEvaluationSettingsForm(forms.ModelForm):
    """
    Form for configuring task evaluation settings
    Only admins can use this form
    """
    class Meta:
        model = TaskEvaluationSettings
        fields = [
            'formula_name', 'use_quality_score', 'use_priority_multiplier', 
            'use_time_bonus_penalty', 'use_manager_closure_penalty',
            'early_completion_bonus_per_day', 'max_early_completion_bonus',
            'late_completion_penalty_per_day', 'max_late_completion_penalty',
            'manager_closure_penalty', 'evaluation_formula'
        ]
        widgets = {
            'formula_name': forms.TextInput(attrs={'class': 'form-control'}),
            'evaluation_formula': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of the evaluation formula'
            }),
            'early_completion_bonus_per_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_early_completion_bonus': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'late_completion_penalty_per_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_late_completion_penalty': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'manager_closure_penalty': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(TaskEvaluationSettingsForm, self).__init__(*args, **kwargs)

class AdminSetPasswordForm(forms.Form):
    """
    Form for admin to set a new password for any user
    """
    password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, user):
        user.set_password(self.cleaned_data['password1'])
        user.save()
        return user 