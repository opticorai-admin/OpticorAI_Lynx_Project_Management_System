from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
import os
from django import forms
from django.http import JsonResponse
from django.views import View
from django.db import models
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from io import BytesIO
from django.db.models.functions import Concat
from django.db.models import Value as V, Avg
from django.core.cache import cache
from django.db.models import Case, When, IntegerField, Count
from django.db.models import Count, Case, When, IntegerField
from .models import CustomUser, Task, KPI, QualityType, Notification, TaskPriorityType, TaskEvaluationSettings, EmployeeProgress
from .forms import (
    EmailLoginForm, TwoFactorForm, UserRegistrationForm, UserProfileEditForm, 
    TaskRegistrationForm, TaskEditForm, KPIForm, QualityTypeForm,
    AdminSetPasswordForm, TaskPriorityTypeForm, TaskEvaluationSettingsForm,
    TaskEvaluationForm
)

User = get_user_model()

# --- Authentication Views ---
class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        form = EmailLoginForm()
        return render(request, 'core/login.html', {'form': form})
    
    def post(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                from django.conf import settings
                if getattr(settings, 'ENABLE_EMAIL_2FA', False):
                    # Stage 1: create and send OTP, then redirect to verify
                    from django.core.mail import send_mail
                    from django.conf import settings as dj_settings
                    from django.core.cache import cache
                    from datetime import timedelta
                    code = TwoFactorForm.generate_code()
                    cache_key = f"otp:{user.id}"
                    cache.set(cache_key, code, 5 * 60)  # 5 minutes
                    from_email = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None) or getattr(dj_settings, 'EMAIL_HOST_USER', None) or 'no-reply@example.com'
                    send_mail(
                        subject='Your verification code',
                        message=f'Your verification code is: {code}\nIt will expire in 5 minutes.',
                        from_email=from_email,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                    # Remember pending user id and backend in session
                    request.session['pending_user_id'] = user.id
                    backend_path = getattr(user, 'backend', None) or settings.AUTHENTICATION_BACKENDS[0]
                    request.session['pending_backend'] = backend_path
                    messages.info(request, 'We sent a verification code to your email.')
                    return redirect('core:verify-2fa')
                else:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.first_name}!')
                    return redirect('core:dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        return render(request, 'core/login.html', {'form': form})

class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('core:login')

class VerifyTwoFactorView(View):
    def get(self, request):
        from django.conf import settings
        if not getattr(settings, 'ENABLE_EMAIL_2FA', False):
            return redirect('core:login')
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        if 'pending_user_id' not in request.session:
            messages.error(request, 'Session expired. Please sign in again.')
            return redirect('core:login')
        form = TwoFactorForm()
        return render(request, 'core/verify_2fa.html', {'form': form})

    def post(self, request):
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from django.core.cache import cache
        if not getattr(settings, 'ENABLE_EMAIL_2FA', False):
            return redirect('core:login')
        if 'pending_user_id' not in request.session:
            messages.error(request, 'Session expired. Please sign in again.')
            return redirect('core:login')
        form = TwoFactorForm(request.POST)
        if not form.is_valid():
            return render(request, 'core/verify_2fa.html', {'form': form})
        submitted_code = form.cleaned_data['code']
        pending_user_id = request.session.get('pending_user_id')
        cache_key = f"otp:{pending_user_id}"
        expected_code = cache.get(cache_key)
        if expected_code and submitted_code == expected_code:
            # login user and cleanup
            User = get_user_model()
            try:
                user = User.objects.get(pk=pending_user_id)
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please sign in again.')
                return redirect('core:login')
            backend_path = request.session.get('pending_backend')
            try:
                if backend_path:
                    login(request, user, backend=backend_path)
                else:
                    # Fallback to first configured backend
                    from django.conf import settings as dj_settings
                    login(request, user, backend=dj_settings.AUTHENTICATION_BACKENDS[0])
            except Exception:
                # As a last resort, force the default backend
                from django.conf import settings as dj_settings
                login(request, user, backend=dj_settings.AUTHENTICATION_BACKENDS[0])
            cache.delete(cache_key)
            request.session.pop('pending_user_id', None)
            request.session.pop('pending_backend', None)
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('core:dashboard')
        messages.error(request, 'Invalid or expired code.')
        return render(request, 'core/verify_2fa.html', {'form': form})

class IndexView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return redirect('core:login')

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type == 'admin':
            users = CustomUser.objects.exclude(user_type='admin')
            managers = CustomUser.objects.filter(user_type='manager')
            employees = CustomUser.objects.filter(user_type='employee')
            context = {
                'users': users,
                'managers': managers,
                'employees': employees,
            }
        elif user.user_type in ['manager']:
            # Managers can see tasks assigned to themselves OR their subordinates
            all_manager_tasks = Task.objects.select_related('responsible', 'priority').for_manager(user)
            subordinates = CustomUser.objects.filter(under_supervision=user)
            subordinate_tasks = Task.objects.select_related('responsible').filter(responsible__in=subordinates)
            # Cache dashboard totals briefly to reduce DB hits
            from django.core.cache import cache
            cache_key = f"dash_totals:{user.id}"
            cached = cache.get(cache_key)
            if cached is None:
                totals = all_manager_tasks.aggregate(
                    total=Count('id'),
                    open_count=Count(Case(When(status='open', then=1), output_field=IntegerField())),
                    closed_count=Count(Case(When(status='closed', then=1), output_field=IntegerField())),
                    due_count=Count(Case(When(status='due', then=1), output_field=IntegerField())),
                )
                total_tasks = totals.get('total', 0) or 0
                open_tasks = totals.get('open_count', 0) or 0
                closed_tasks = totals.get('closed_count', 0) or 0
                due_tasks = totals.get('due_count', 0) or 0
                cached = (total_tasks, open_tasks, closed_tasks, due_tasks)
                cache.set(cache_key, cached, 30)
            else:
                total_tasks, open_tasks, closed_tasks, due_tasks = cached

            # Priority Report (dynamic by active priority types)
            priority_report = {}
            priority_types = list(TaskPriorityType.objects.filter(is_active=True).values_list('name', flat=True))
            for priority_type in TaskPriorityType.objects.filter(is_active=True):
                priority_report[priority_type.name] = all_manager_tasks.filter(priority=priority_type).count()
            # Status Pie (Open/Closed/Due)
            status_report = {
                'open': open_tasks,
                'closed': closed_tasks,
                'due': due_tasks,
            }
            # Status Distribution by User (aggregated)
            
            sub_qs = Task.objects.filter(responsible__in=subordinates)
            agg = sub_qs.values('responsible__first_name', 'responsible__last_name', 'responsible__username') \
                .annotate(
                    open_count=Count(Case(When(status='open', then=1), output_field=IntegerField())),
                    closed_count=Count(Case(When(status='closed', then=1), output_field=IntegerField())),
                    due_count=Count(Case(When(status='due', then=1), output_field=IntegerField())),
                )
            status_by_user = {}
            for row in agg:
                name = (row['responsible__first_name'] or '') + ' ' + (row['responsible__last_name'] or '')
                name = name.strip() or row['responsible__username']
                status_by_user[name] = {
                    'open': row['open_count'],
                    'closed': row['closed_count'],
                    'due': row['due_count'],
                }
            # Priority Distribution by User (aggregated)
            prio_qs = sub_qs.values('responsible__first_name', 'responsible__last_name', 'responsible__username', 'priority__name') \
                .annotate(count=Count('id'))
            priority_by_user = {}
            for row in prio_qs:
                name = (row['responsible__first_name'] or '') + ' ' + (row['responsible__last_name'] or '')
                name = name.strip() or row['responsible__username']
                priority_by_user.setdefault(name, {})[row['priority__name'] or 'Unassigned'] = row['count']
            # Pending evaluations for manager's subordinates
            pending_evaluations_qs = Task.objects.select_related('responsible').filter(
                responsible__in=subordinates,
                evaluation_status='pending'
            ).order_by('-created_date')
            
            # Paginate pending evaluations (3 per page)
            pending_evaluations_paginator = Paginator(pending_evaluations_qs, 3)
            pending_evaluations_page = request.GET.get('evaluations_page', 1)
            try:
                pending_evaluations = pending_evaluations_paginator.page(pending_evaluations_page)
            except (PageNotAnInteger, EmptyPage):
                pending_evaluations = pending_evaluations_paginator.page(1)
            
            # Get pending approvals from subordinate tasks
            pending_approvals_qs = subordinate_tasks.select_related('responsible').filter(
                approval_status='pending'
            ).order_by('-created_date')
            
            # Paginate pending approvals (3 per page)
            pending_approvals_paginator = Paginator(pending_approvals_qs, 3)
            pending_approvals_page = request.GET.get('approvals_page', 1)
            try:
                pending_approvals = pending_approvals_paginator.page(pending_approvals_page)
            except (PageNotAnInteger, EmptyPage):
                pending_approvals = pending_approvals_paginator.page(1)
            
            context = {
                'subordinates': subordinates,
                'subordinate_tasks': subordinate_tasks,
                'all_manager_tasks': all_manager_tasks,
                'total_tasks': total_tasks,
                'open_tasks': open_tasks,
                'closed_tasks': closed_tasks,
                'due_tasks': due_tasks,
                'priority_report': priority_report,
                'priority_types': priority_types,
                'status_report': status_report,
                'status_by_user': status_by_user,
                'priority_by_user': priority_by_user,
                'pending_evaluations': pending_evaluations,
                'pending_approvals': pending_approvals,
            }
        else:
            my_tasks_qs = Task.objects.select_related('priority', 'kpi').for_responsible(user).order_by('-created_date')
            total_tasks = my_tasks_qs.count()
            open_tasks = my_tasks_qs.filter(status='open').count()
            closed_tasks = my_tasks_qs.filter(status='closed').count()
            due_tasks = my_tasks_qs.filter(status='due').count()
            
            # Paginate recent tasks (3 per page)
            recent_tasks_paginator = Paginator(my_tasks_qs, 3)
            recent_tasks_page = request.GET.get('recent_tasks_page', 1)
            try:
                recent_tasks = recent_tasks_paginator.page(recent_tasks_page)
            except (PageNotAnInteger, EmptyPage):
                recent_tasks = recent_tasks_paginator.page(1)
            
            context = {
                'my_tasks': my_tasks_qs,  # Keep for backward compatibility
                'recent_tasks': recent_tasks,  # New paginated version for Recent Tasks section
                'total_tasks': total_tasks,
                'open_tasks': open_tasks,
                'closed_tasks': closed_tasks,
                'due_tasks': due_tasks,
            }
        return render(request, 'core/dashboard.html', context)

# --- User Management Views ---
class RegisterView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type == 'employee':
            messages.error(request, 'Employees cannot create new users.')
            return redirect('core:dashboard')
        form = UserRegistrationForm(user=user)
        return render(request, 'core/reg_form.html', {'form': form})

    def post(self, request):
        user = request.user
        if user.user_type == 'employee':
            messages.error(request, 'Employees cannot create new users.')
            return redirect('core:dashboard')
        form = UserRegistrationForm(request.POST, user=user)
        if form.is_valid():
            # Capture raw password before save for email
            raw_password = form.cleaned_data.get('password1')
            # Create the user instance without committing so we can control signals
            new_user = form.save(commit=False)
            if request.user.user_type == 'admin':
                # Suppress default welcome email; we'll send credentials email instead
                setattr(new_user, '_skip_welcome_email', True)
            # Persist user
            new_user.save()
            # Send credential email only when created by admin
            if request.user.user_type == 'admin':
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings as dj_settings
                    login_url = request.build_absolute_uri('/accounts/login/')
                    subject = 'Your account credentials'
                    body_lines = [
                        f"Hello {new_user.get_full_name() or new_user.username},",
                        "",
                        "An account has been created for you.",
                        f"Hello {new_user.get_full_name() or new_user.username}, Welcome to the system! You can now log in to the system with the following credentials.",
                        f"Login URL: {login_url}",
                        f"Login Email: {new_user.email}",
                        f"Temporary Password: {raw_password}",
                        "",
                        
                    ]
                    body = "\n".join(body_lines)
                    from_email = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None) or getattr(dj_settings, 'EMAIL_HOST_USER', None) or 'no-reply@example.com'
                    send_mail(subject=subject, message=body, from_email=from_email, recipient_list=[new_user.email], fail_silently=True)
                except Exception:
                    pass
            messages.success(request, f'User {new_user.get_full_name()} created successfully! Username: {new_user.username}')
            return render(request, 'core/reg_form.html', {'form': UserRegistrationForm(user=user), 'created': True})
        return render(request, 'core/reg_form.html', {'form': form})

class UsersView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type == 'admin':
            users = CustomUser.objects.select_related('under_supervision').exclude(id=user.id)
        elif user.user_type == 'manager':
            users = CustomUser.objects.select_related('under_supervision').filter(under_supervision=user)
        else:
            messages.error(request, 'You do not have permission to view users.')
            return redirect('core:dashboard')
        # Filters
        search_query = request.GET.get('search', '')
        user_type_filter = request.GET.get('user_type', '')
        designation_filter = request.GET.get('designation', '')
        supervisor_filter = request.GET.get('supervisor', '')
        active_filter = request.GET.get('active', '')
        # Annotate full name for searching
        users = users.annotate(full_name=Concat('first_name', V(' '), 'last_name'))
        if search_query:
            users = users.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        if user_type_filter:
            users = users.filter(user_type=user_type_filter)
        if designation_filter:
            users = users.filter(designation__icontains=designation_filter)
        if supervisor_filter:
            users = users.filter(
                Q(under_supervision__first_name__icontains=supervisor_filter) |
                Q(under_supervision__last_name__icontains=supervisor_filter)
            )
        if active_filter == 'active':
            users = users.filter(is_active=True)
        elif active_filter == 'inactive':
            users = users.filter(is_active=False)
        paginator = Paginator(users, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {
            'users': page_obj,
            'total_users': users.count(),
            'search_query': search_query,
            'user_type_filter': user_type_filter,
            'designation_filter': designation_filter,
            'supervisor_filter': supervisor_filter,
            'active_filter': active_filter,
        }
        return render(request, 'core/users.html', context)

class UserProfileView(LoginRequiredMixin, View):
    def get(self, request, profile_id):
        user = request.user
        profile_user = get_object_or_404(CustomUser, id=profile_id)
        if user.user_type == 'employee':
            if profile_user != user:
                messages.error(request, 'You can only view your own profile.')
                return redirect('core:dashboard')
        elif user.user_type == 'manager':
            if profile_user.under_supervision != user:
                messages.error(request, 'You can only view profiles of your subordinates.')
                return redirect('core:dashboard')
        context = {
            'user_view': profile_user,
        }
        return render(request, 'core/user.html', context)

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        form = UserProfileEditForm(instance=user, user=user)
        class AvatarForm(forms.Form):
            avatar = forms.ImageField(
                required=False,
                widget=forms.FileInput(attrs={'class': 'form-control'})
            )
        avatar_form = AvatarForm()
        context = {
            'profile_form': form,
            'img_form': avatar_form,
            'logged_user': user,
        }
        return render(request, 'core/profile.html', context)

    def post(self, request):
        user = request.user
        if 'update_profile' in request.POST:
            form = UserProfileEditForm(request.POST, request.FILES, instance=user, user=user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('core:profile')
        elif 'update_avatar' in request.POST:
            if 'avatar' in request.FILES:
                user.avatar = request.FILES['avatar']
                user.save()
                messages.success(request, 'Profile picture updated successfully!')
                return redirect('core:profile')
        form = UserProfileEditForm(instance=user, user=user)
        class AvatarForm(forms.Form):
            avatar = forms.ImageField(
                required=False,
                widget=forms.FileInput(attrs={'class': 'form-control'})
            )
        avatar_form = AvatarForm()
        context = {
            'profile_form': form,
            'img_form': avatar_form,
            'logged_user': user,
        }
        return render(request, 'core/profile.html', context)

class EditUserProfileView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        user = request.user
        target_user = get_object_or_404(CustomUser, id=user_id)
        if user.user_type == 'employee':
            if target_user != user:
                messages.error(request, 'You can only edit your own profile.')
                return redirect('core:dashboard')
        elif user.user_type == 'manager':
            if target_user.under_supervision != user:
                messages.error(request, 'You can only edit profiles of your subordinates.')
                return redirect('core:dashboard')
        form = UserProfileEditForm(instance=target_user, user=user)
        context = {
            'form': form,
            'target_user': target_user,
        }
        return render(request, 'core/edit_user_profile.html', context)

    def post(self, request, user_id):
        user = request.user
        target_user = get_object_or_404(CustomUser, id=user_id)
        if user.user_type == 'employee':
            if target_user != user:
                messages.error(request, 'You can only edit your own profile.')
                return redirect('core:dashboard')
        elif user.user_type == 'manager':
            if target_user.under_supervision != user:
                messages.error(request, 'You can only edit profiles of your subordinates.')
                return redirect('core:dashboard')
        form = UserProfileEditForm(request.POST, request.FILES, instance=target_user, user=user)
        if form.is_valid():
            old_email = target_user.email
            updated_user = form.save()
            # If admin updated another user's profile, notify the target user about changes
            if user.user_type == 'admin' and updated_user != user:
                try:
                    changed_fields = list(getattr(form, 'changed_data', []))
                    if changed_fields:
                        # Human-friendly field names
                        field_labels = {
                            'email': 'Email',
                            'first_name': 'First name',
                            'last_name': 'Last name',
                            'designation': 'Designation',
                            'user_type': 'Role',
                            'under_supervision': 'Supervisor',
                            'avatar': 'Profile picture',
                        }
                        friendly = [field_labels.get(f, f) for f in changed_fields]
                        changes_text = ", ".join(sorted(set(friendly)))
                        Notification.objects.create(
                            recipient=updated_user,
                            sender=user,
                            message=f"Your profile was updated by an administrator. Updated fields: {changes_text}.",
                            link=f"/users/{updated_user.id}/"
                        )
                except Exception:
                    pass
            # If admin updated another user's email, set a temporary password and email credentials
            if user.user_type == 'admin' and updated_user != user and 'email' in getattr(form, 'changed_data', []):
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings as dj_settings
                    from django.contrib.auth import get_user_model
                    UserModel = get_user_model()
                    temp_password = UserModel.objects.make_random_password(length=12)
                    updated_user.set_password(temp_password)
                    updated_user.save(update_fields=['password'])
                    login_url = request.build_absolute_uri('/accounts/login/')
                    subject = 'Welcome - Your updated login credentials'
                    body_lines = [
                        f"Hello {updated_user.get_full_name() or updated_user.username}, Welcome to the system! You can now log in with the following credentials.",
                        f"Login URL: {login_url}",
                        f"Updated Login Email: {updated_user.email}",
                        f"Your Password: {temp_password}",
                        "",
                    ]
                    body = "\n".join(body_lines)
                    from_email = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None) or getattr(dj_settings, 'EMAIL_HOST_USER', None) or 'no-reply@example.com'
                    send_mail(subject=subject, message=body, from_email=from_email, recipient_list=[updated_user.email], fail_silently=True)
                except Exception:
                    pass
            messages.success(request, 'Profile updated successfully!')
            # If admin and editing another user's profile, show popup
            if user.user_type == 'admin' and target_user != user:
                context = {
                    'form': UserProfileEditForm(instance=updated_user, user=user),
                    'target_user': updated_user,
                    'profile_updated': True,
                }
                return render(request, 'core/edit_user_profile.html', context)
            if updated_user == user:
                return redirect('core:profile')
            else:
                return redirect('core:user', profile_id=user_id)
        context = {
            'form': form,
            'target_user': target_user,
        }
        return render(request, 'core/edit_user_profile.html', context)

# --- Task Management Views ---
class ProjectsView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type == 'admin':
            messages.error(request, 'Admins cannot view tasks.')
            return redirect('core:dashboard')
        elif user.user_type == 'manager':
            tasks_qs = Task.objects.select_related('responsible', 'priority', 'kpi').for_manager(user)
        else:
            tasks_qs = Task.objects.select_related('priority', 'kpi').for_responsible(user)

        # Apply filters
        search_query = request.GET.get('search', '')
        if search_query:
            tasks_qs = tasks_qs.filter(
                Q(issue_action__icontains=search_query) |
                Q(responsible__first_name__icontains=search_query) |
                Q(responsible__last_name__icontains=search_query)
            )
        status_filter = request.GET.get('status', '')
        if status_filter:
            tasks_qs = tasks_qs.filter(status=status_filter)
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        if start_date:
            tasks_qs = tasks_qs.filter(start_date__gte=start_date)
        if end_date:
            tasks_qs = tasks_qs.filter(close_date__lte=end_date)
        employee_query = request.GET.get('employee', '')
        tasks_qs = tasks_qs.annotate(
            full_name=Concat('responsible__first_name', V(' '), 'responsible__last_name')
        )
        if employee_query:
            tasks_qs = tasks_qs.filter(
                Q(responsible__first_name__icontains=employee_query) |
                Q(responsible__last_name__icontains=employee_query) |
                Q(responsible__username__icontains=employee_query) |
                Q(full_name__icontains=employee_query)
            )

        # Calculate average completion
        avg_tasks = tasks_qs.aggregate(avg=Avg('percentage_completion'))['avg'] or 0

        # Paginate
        paginator = Paginator(tasks_qs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'tasks': page_obj,
            'tasks_qs': tasks_qs,
            'avg_tasks': avg_tasks,
            'search_query': search_query,
            'status_filter': status_filter,
            'start_date': start_date,
            'end_date': end_date,
            'employee_query': employee_query,
        }
        return render(request, 'core/projects.html', context)

class NewTaskView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type == 'admin':
            messages.error(request, 'Admins cannot create tasks.')
            return redirect('core:dashboard')
        form = TaskRegistrationForm(user=user)
        context = {'form': form}
        return render(request, 'core/new_task.html', context)

    def post(self, request):
        user = request.user
        if user.user_type == 'admin':
            messages.error(request, 'Admins cannot create tasks.')
            return redirect('core:dashboard')
        form = TaskRegistrationForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            task = form.save()
            if user.user_type == 'employee' and task.responsible == user:
                if user.under_supervision:
                    Notification.objects.create(
                        recipient=user.under_supervision,
                        sender=user,
                        message=f"{user.get_full_name()} created a new task for themselves: '{task.issue_action[:40]}...'",
                        link=f"/projects/task/{task.id}/"
                    )
            elif user.user_type == 'manager':
                if task.responsible == user:
                    if user.under_supervision:
                        Notification.objects.create(
                            recipient=user.under_supervision,
                            sender=user,
                            message=f"{user.get_full_name()} created a new task for themselves: '{task.issue_action[:40]}...'",
                            link=f"/projects/task/{task.id}/"
                        )
                elif task.responsible != user:
                    Notification.objects.create(
                        recipient=task.responsible,
                        sender=user,
                        message=f"You have been assigned a new task: '{task.issue_action[:40]}...'",
                        link=f"/projects/task/{task.id}/"
                    )
            messages.success(request, 'Task created successfully!')
            # Show popup for manager/employee
            return render(request, 'core/new_task.html', {'form': TaskRegistrationForm(user=user), 'created': True})
        context = {'form': form}
        return render(request, 'core/new_task.html', context)

class TaskDetailView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task.objects.select_related('responsible', 'priority', 'kpi'), id=task_id)
        if not task.can_user_manage(user):
            messages.error(request, 'You do not have permission to view this task.')
            return redirect('core:dashboard')
        context = {'task': task}
        return render(request, 'core/task_detail.html', context)

class EditTaskView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_edit(user):
            messages.error(request, 'You do not have permission to edit this task.')
            return redirect('core:dashboard')
        if user.user_type == 'manager' and task.responsible == user:
            messages.error(request, 'You cannot edit tasks assigned to yourself. Only your supervisor can edit your tasks.')
            return redirect('core:task-detail', task_id=task_id)
        form = TaskEditForm(instance=task, user=user)
        context = {'form': form, 'task': task}
        return render(request, 'core/edit_task.html', context)

    def post(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_edit(user):
            messages.error(request, 'You do not have permission to edit this task.')
            return redirect('core:dashboard')
        if user.user_type == 'manager' and task.responsible == user:
            messages.error(request, 'You cannot edit tasks assigned to yourself. Only your supervisor can edit your tasks.')
            return redirect('core:task-detail', task_id=task_id)
        form = TaskEditForm(request.POST, request.FILES, instance=task, user=user)
        if form.is_valid():
            original_task = Task.objects.get(id=task.id)
            original_data = {
                'issue_action': original_task.issue_action,
                'priority': original_task.priority,
                'kpi': original_task.kpi,
                'quality': original_task.quality,
                'start_date': original_task.start_date,
                'close_date': original_task.close_date,
                'percentage_completion': original_task.percentage_completion,
                'comments': original_task.comments,
                'approval_status': original_task.approval_status,
                'quality_score': original_task.quality_score,
                'evaluation_comments': original_task.evaluation_comments,
                'evaluation_status': original_task.evaluation_status,
                'responsible': original_task.responsible,
            }
            updated_task = form.save()
            if user.user_type == 'manager':
                # Manager editing subordinate's task (like manager)
                changes = []
                if original_data['responsible'] != updated_task.responsible:
                    old_responsible = original_data['responsible'].get_full_name() if original_data['responsible'] else 'None'
                    new_responsible = updated_task.responsible.get_full_name() if updated_task.responsible else 'None'
                    changes.append(f"Task reassigned from {old_responsible} to {new_responsible}")
                    if updated_task.responsible and updated_task.responsible != user:
                        assignment_message = f"You have been assigned a task: '{updated_task.issue_action[:40]}...'"
                        Notification.objects.create(
                            recipient=updated_task.responsible,
                            sender=user,
                            message=assignment_message,
                            link=f"/projects/task/{updated_task.id}/"
                        )
                if original_data['issue_action'] != updated_task.issue_action:
                    changes.append(f"Task description updated")
                if original_data['priority'] != updated_task.priority:
                    changes.append(f"Priority changed from {original_data['priority']} to {updated_task.priority}")
                if original_data['kpi'] != updated_task.kpi:
                    old_kpi = original_data['kpi'].name if original_data['kpi'] else 'None'
                    new_kpi = updated_task.kpi.name if updated_task.kpi else 'None'
                    changes.append(f"KPI changed from {old_kpi} to {new_kpi}")
                if original_data['quality'] != updated_task.quality:
                    old_quality = original_data['quality'].name if original_data['quality'] else 'None'
                    new_quality = updated_task.quality.name if updated_task.quality else 'None'
                    changes.append(f"Quality changed from {old_quality} to {new_quality}")
                if original_data['close_date'] != updated_task.close_date:
                    changes.append(f"Close date updated")
                if original_data['percentage_completion'] != updated_task.percentage_completion:
                    changes.append(f"Completion updated to {updated_task.percentage_completion}%")
                if original_data['comments'] != updated_task.comments:
                    if updated_task.comments and not original_data['comments']:
                        changes.append("Comments added")
                    elif original_data['comments'] and not updated_task.comments:
                        changes.append("Comments removed")
                    else:
                        changes.append("Comments updated")
                if original_data['approval_status'] != updated_task.approval_status:
                    changes.append(f"Approval status changed from {original_data['approval_status']} to {updated_task.approval_status}")
                if original_data['quality_score'] != updated_task.quality_score:
                    if updated_task.quality_score and not original_data['quality_score']:
                        changes.append(f"Quality score added: {updated_task.quality_score}/10")
                    elif original_data['quality_score'] and not updated_task.quality_score:
                        changes.append("Quality score removed")
                    else:
                        changes.append(f"Quality score updated from {original_data['quality_score']}/10 to {updated_task.quality_score}/10")
                if original_data['evaluation_comments'] != updated_task.evaluation_comments:
                    if updated_task.evaluation_comments and not original_data['evaluation_comments']:
                        changes.append("Evaluation comments added")
                    elif original_data['evaluation_comments'] and not updated_task.evaluation_comments:
                        changes.append("Evaluation comments removed")
                    else:
                        changes.append("Evaluation comments updated")
                if original_data['evaluation_status'] != updated_task.evaluation_status:
                    changes.append(f"Evaluation status changed from {original_data['evaluation_status']} to {updated_task.evaluation_status}")
                if changes and not any('reassigned' in change for change in changes):
                    change_summary = "; ".join(changes)
                    notification_message = f"Your task '{updated_task.issue_action[:40]}...' has been updated by your supervisor. Changes: {change_summary}"
                    Notification.objects.create(
                        recipient=updated_task.responsible,
                        sender=user,
                        message=notification_message,
                        link=f"/projects/task/{updated_task.id}/"
                    )
                if (original_data['evaluation_status'] != 'evaluated' and updated_task.evaluation_status == 'evaluated' and \
                    updated_task.quality_score and updated_task.evaluation_comments):
                    evaluation_message = f"Your task '{updated_task.issue_action[:40]}...' has been evaluated by your supervisor. Quality Score: {updated_task.quality_score}/10"
                    Notification.objects.create(
                        recipient=updated_task.responsible,
                        sender=user,
                        message=evaluation_message,
                        link=f"/projects/task/{updated_task.id}/"
                    )
            messages.success(request, 'Task updated successfully!')
            # Show popup for manager/employee
            return render(request, 'core/edit_task.html', {'form': TaskEditForm(instance=updated_task, user=user), 'task': updated_task, 'updated': True})
        context = {'form': form, 'task': task}
        return render(request, 'core/edit_task.html', context)

class DeleteTaskView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_edit(user):
            messages.error(request, 'You do not have permission to delete this task.')
            return redirect('core:dashboard')
        # Additional check: Managers cannot delete tasks assigned to themselves
        if user.user_type == 'manager' and task.responsible == user:
            messages.error(request, 'You cannot delete tasks assigned to yourself. Only your supervisor can delete your tasks.')
            return redirect('core:task-detail', task_id=task_id)
        context = {'task': task}
        return render(request, 'core/delete_task.html', context)

    def post(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_edit(user):
            messages.error(request, 'You do not have permission to delete this task.')
            return redirect('core:dashboard')
        # Additional check: Managers cannot delete tasks assigned to themselves
        if user.user_type == 'manager' and task.responsible == user:
            messages.error(request, 'You cannot delete tasks assigned to yourself. Only your supervisor can delete your tasks.')
            return redirect('core:task-detail', task_id=task_id)
        task_info = {
            'issue_action': task.issue_action,
            'responsible': task.responsible,
            'responsible_name': task.responsible.get_full_name() if task.responsible else 'Unknown'
        }
        if user.user_type == 'manager':
            # Manager deleting subordinate's task (like manager)
            if task.responsible and task.responsible != user:
                notification_message = f"Your task '{task.issue_action[:40]}...' has been deleted by your supervisor."
                Notification.objects.create(
                    recipient=task.responsible,
                    sender=user,
                    message=notification_message,
                    link="/projects/"
                )
        task.delete()
        messages.success(request, 'Task deleted successfully!')
        return redirect('core:projects')
    
class UserTasksView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        user = request.user
        target_user = get_object_or_404(CustomUser, id=user_id)
        if user.user_type == 'employee':
            if target_user != user:
                messages.error(request, 'You can only view your own tasks.')
                return redirect('core:dashboard')
        elif user.user_type == 'manager':
            # Managers can view their own tasks OR tasks of their subordinates
            if target_user != user and target_user.under_supervision != user:
                messages.error(request, 'You can only view your own tasks or tasks of your subordinates.')
                return redirect('core:dashboard')
        elif user.user_type == 'admin':
            messages.error(request, 'Admins cannot view tasks.')
            return redirect('core:dashboard')
        
        # Get tasks for the target user
        tasks_qs = Task.objects.filter(responsible=target_user)
        
        # Apply filters if any
        search_query = request.GET.get('search', '')
        if search_query:
            tasks_qs = tasks_qs.filter(
                Q(issue_action__icontains=search_query) |
                Q(responsible__first_name__icontains=search_query) |
                Q(responsible__last_name__icontains=search_query)
            )
        status_filter = request.GET.get('status', '')
        if status_filter:
            tasks_qs = tasks_qs.filter(status=status_filter)
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        if start_date:
            tasks_qs = tasks_qs.filter(start_date__gte=start_date)
        if end_date:
            tasks_qs = tasks_qs.filter(close_date__lte=end_date)
        
        # Calculate average completion
        avg_tasks = tasks_qs.aggregate(avg=Avg('percentage_completion'))['avg'] or 0
        
        # Paginate
        paginator = Paginator(tasks_qs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'tasks': page_obj,
            'tasks_qs': tasks_qs,
            'target_user': target_user,
            'avg_tasks': avg_tasks,
            'search_query': search_query,
            'status_filter': status_filter,
            'start_date': start_date,
            'end_date': end_date,
        }
        return render(request, 'core/projects.html', context)

class DownloadFileView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_download_file(user):
            messages.error(request, 'You do not have permission to download this file.')
            return redirect('core:dashboard')
        if task.file_upload:
            file_path = task.file_upload.path
            if os.path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
                    return response
        messages.error(request, 'File not found.')
        return redirect('core:task-detail', task_id=task.id)

class ApproveTaskView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can approve tasks.')
            return redirect('core:dashboard')
        if not task.can_user_evaluate(user):
            messages.error(request, 'You can only approve tasks assigned to your subordinates.')
            return redirect('core:dashboard')
        # Additional check: Managers cannot approve tasks assigned to themselves
        if task.responsible == user:
            messages.error(request, 'You cannot approve tasks assigned to yourself. Only your supervisor can approve your tasks.')
            return redirect('core:task-detail', task_id=task_id)
        action = request.POST.get('action')
        if action == 'approve':
            task.approval_status = 'approved'
            messages.success(request, 'Task approved successfully!')
            Notification.objects.create(
                recipient=task.responsible,
                sender=user,
                message=f"Your task '{task.issue_action[:40]}...' has been approved.",
                link=f"/projects/task/{task.id}/"
            )
        elif action == 'disapprove':
            task.approval_status = 'disapproved'
            messages.success(request, 'Task disapproved successfully!')
            Notification.objects.create(
                recipient=task.responsible,
                sender=user,
                message=f"Your task '{task.issue_action[:40]}...' has been disapproved.",
                link=f"/projects/task/{task.id}/"
            )
        task.save()
        return redirect('core:task-detail', task_id=task.id)
    
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can approve tasks.')
            return redirect('core:dashboard')
        if not task.can_user_evaluate(user):
            messages.error(request, 'You can only approve tasks assigned to your subordinates.')
            return redirect('core:dashboard')
        # Additional check: Managers cannot approve tasks assigned to themselves
        if task.responsible == user:
            messages.error(request, 'You cannot approve tasks assigned to yourself. Only your supervisor can approve your tasks.')
            return redirect('core:task-detail', task_id=task_id)
        context = {'task': task}
        return render(request, 'core/task_detail.html', context)

class EvaluateTaskView(LoginRequiredMixin, View):
    """
    View for managers to evaluate tasks using the evaluation form
    """
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        
        if not task.can_user_evaluate(user):
            messages.error(request, 'You do not have permission to evaluate this task.')
            return redirect('core:task-detail', task_id=task_id)
        
        # Check if task is already evaluated
        if task.evaluation_status == 'evaluated':
            messages.warning(request, 'This task has already been evaluated.')
            return redirect('core:task-detail', task_id=task_id)
        
        form = TaskEvaluationForm(instance=task)
        context = {
            'task': task,
            'form': form,
            'title': 'Evaluate Task'
        }
        return render(request, 'core/evaluate_task.html', context)
    
    def post(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        
        if not task.can_user_evaluate(user):
            messages.error(request, 'You do not have permission to evaluate this task.')
            return redirect('core:task-detail', task_id=task_id)
        
        form = TaskEvaluationForm(request.POST, instance=task)
        
        if form.is_valid():
            # Set completion to 100% and status to closed
            task.percentage_completion = 100
            task.status = 'closed'
            
            # Save the form data
            task = form.save(commit=False)
            # Align completion_date with the manager-selected close_date to avoid timezone/day drift
            try:
                from datetime import datetime, time as dtime
                from django.utils import timezone as dj_tz
                if getattr(task, 'close_date', None):
                    naive_dt = datetime.combine(task.close_date, dtime(12, 0))
                    task.completion_date = dj_tz.make_aware(naive_dt, dj_tz.get_current_timezone())
            except Exception:
                # best-effort; fallback handled in apply_automatic_evaluation
                pass
            
            # Apply automatic evaluation
            if task.apply_automatic_evaluation():
                task.evaluated_by = user
                task.evaluated_date = timezone.now()
                task.save()
                messages.success(request, f'Task evaluated successfully! Final Score: {task.final_score:.1f}%')
            else:
                messages.error(request, 'Failed to evaluate task. Please check quality rating.')
                context = {'task': task, 'form': form, 'title': 'Evaluate Task'}
                return render(request, 'core/evaluate_task.html', context)
            
            # Notify employee
            if task.responsible:
                notification_message = f"Your task '{task.issue_action[:40]}...' has been evaluated. Final Score: {task.final_score:.1f}%"
                Notification.objects.create(
                    recipient=task.responsible,
                    sender=user,
                    message=notification_message,
                    link=f"/projects/task/{task.id}/"
                )
            
            return redirect('core:task-detail', task_id=task_id)
        else:
            context = {'task': task, 'form': form, 'title': 'Evaluate Task'}
            return render(request, 'core/evaluate_task.html', context)

class UploadTaskFileView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_upload_file(user):
            messages.error(request, 'You do not have permission to upload files to this task.')
            return redirect('core:dashboard')
        context = {'task': task}
        return render(request, 'core/upload_task_file.html', context)

    def post(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        if not task.can_user_upload_file(user):
            messages.error(request, 'You do not have permission to upload files to this task.')
            return redirect('core:dashboard')
        if 'file_upload' in request.FILES:
            uploaded_file = request.FILES['file_upload']
            if uploaded_file.size > 200 * 1024 * 1024:
                messages.error(request, 'File size must be less than 200MB.')
                context = {'task': task}
                return render(request, 'core/upload_task_file.html', context)
            allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.zip']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            if file_extension not in allowed_extensions:
                messages.error(request, 'File type not allowed. Please upload PDF, Word, Excel, text, image, or zip files.')
                context = {'task': task}
                return render(request, 'core/upload_task_file.html', context)
            task.file_upload = uploaded_file
            task.save()
            if user.under_supervision:
                Notification.objects.create(
                    recipient=user.under_supervision,
                    sender=user,
                    message=f"{user.get_full_name()} uploaded a file for task: '{task.issue_action[:40]}...'",
                    link=f"/projects/task/{task.id}/"
                )
            messages.success(request, 'File uploaded successfully!')
            return redirect('core:task-detail', task_id=task.id)
        else:
            messages.error(request, 'Please select a file to upload.')
        context = {'task': task}
        return render(request, 'core/upload_task_file.html', context)

# --- KPI Management Views ---
class ManagerRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure only managers can access the view
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'manager'

class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure only admins can access the view
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'admin'

class KPIListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """
    List view for KPIs - managers only
    """
    model = KPI
    template_name = 'core/kpi_list.html'
    context_object_name = 'kpis'
    ordering = ['name']
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        # Restrict to KPIs created by this manager
        queryset = queryset.filter(created_by=self.request.user)
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class KPICreateView(LoginRequiredMixin, ManagerRequiredMixin, CreateView):
    """
    Create view for KPIs - managers only
    """
    model = KPI
    form_class = KPIForm
    template_name = 'core/kpi_form.html'
    success_url = reverse_lazy('core:kpi-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'KPI created successfully!')
        return super().form_valid(form)

class KPIUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    """
    Update view for KPIs - managers only
    """
    model = KPI
    form_class = KPIForm
    template_name = 'core/kpi_form.html'
    success_url = reverse_lazy('core:kpi-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'KPI updated successfully!')
        return super().form_valid(form)

class KPIDeleteView(LoginRequiredMixin, ManagerRequiredMixin, DeleteView):
    """
    Delete view for KPIs - managers only
    """
    model = KPI
    template_name = 'core/kpi_confirm_delete.html'
    success_url = reverse_lazy('core:kpi-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'KPI deleted successfully!')
        return super().delete(request, *args, **kwargs)

# --- QualityType Management Views ---
class QualityTypeListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    List view for Quality Types - admins only
    """
    model = QualityType
    template_name = 'core/qualitytype_list.html'
    context_object_name = 'quality_types'
    ordering = ['name']
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        # Admins can see all quality types
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class QualityTypeCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    Create view for Quality Types - admins only
    """
    model = QualityType
    form_class = QualityTypeForm
    template_name = 'core/qualitytype_form.html'
    success_url = reverse_lazy('core:qualitytype-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Quality type created successfully!')
        return super().form_valid(form)

class QualityTypeUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    Update view for Quality Types - admins only
    """
    model = QualityType
    form_class = QualityTypeForm
    template_name = 'core/qualitytype_form.html'
    success_url = reverse_lazy('core:qualitytype-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Quality type updated successfully!')
        return super().form_valid(form)

class QualityTypeDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Delete view for Quality Types - admins only
    """
    model = QualityType
    template_name = 'core/qualitytype_confirm_delete.html'
    success_url = reverse_lazy('core:qualitytype-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Quality type deleted successfully!')
        return super().delete(request, *args, **kwargs)

# --- TaskPriorityType Management Views ---
class TaskPriorityTypeListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    List view for Task Priority Types - admins only
    """
    model = TaskPriorityType
    template_name = 'core/taskprioritytype_list.html'
    context_object_name = 'priority_types'
    ordering = ['sort_order', 'name']
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class TaskPriorityTypeCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    Create view for Task Priority Types - admins only
    """
    model = TaskPriorityType
    form_class = TaskPriorityTypeForm
    template_name = 'core/taskprioritytype_form.html'
    success_url = reverse_lazy('core:taskprioritytype-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Priority type created successfully!')
        return super().form_valid(form)

class TaskPriorityTypeUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    Update view for Task Priority Types - admins only
    """
    model = TaskPriorityType
    form_class = TaskPriorityTypeForm
    template_name = 'core/taskprioritytype_form.html'
    success_url = reverse_lazy('core:taskprioritytype-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Priority type updated successfully!')
        return super().form_valid(form)

class TaskPriorityTypeDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Delete view for Task Priority Types - admins only
    """
    model = TaskPriorityType
    template_name = 'core/taskprioritytype_confirm_delete.html'
    success_url = reverse_lazy('core:taskprioritytype-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Priority type deleted successfully!')
        return super().delete(request, *args, **kwargs)

# --- TaskEvaluationSettings Management Views ---
class TaskEvaluationSettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    View for managing task evaluation settings - admins only
    """
    def get(self, request):
        settings, created = TaskEvaluationSettings.objects.get_or_create(
            defaults={
                'formula_name': 'Enhanced Task Evaluation Formula',
                'use_quality_score': True,
                'use_priority_multiplier': True,
                'use_time_bonus_penalty': True,
                'use_manager_closure_penalty': True,
                'early_completion_bonus_per_day': 1.0,
                'max_early_completion_bonus': 10.0,
                'late_completion_penalty_per_day': 2.0,
                'max_late_completion_penalty': 20.0,
                'manager_closure_penalty': 20.0,
                'evaluation_formula': 'Final Score = (Quality Score × Priority Multiplier) ± Time Bonus/Penalty ± Manager Closure Penalty'
            }
        )
        
        form = TaskEvaluationSettingsForm(instance=settings, user=request.user)
        return render(request, 'core/taskevaluationsettings_form.html', {
            'form': form,
            'settings': settings
        })

    def post(self, request):
        settings = TaskEvaluationSettings.objects.first()
        if not settings:
            settings = TaskEvaluationSettings.objects.create()
        
        form = TaskEvaluationSettingsForm(request.POST, instance=settings, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evaluation settings updated successfully!')
            return redirect('core:taskevaluationsettings')
        else:
            return render(request, 'core/taskevaluationsettings_form.html', {
                'form': form,
                'settings': settings
            })

# --- Evaluation Demo View ---
class EvaluationDemoView(LoginRequiredMixin, View):
    """
    Demo view to show how the evaluation system works
    """
    def get(self, request):
        from core.models import TaskEvaluationSettings
        
        settings = TaskEvaluationSettings.get_settings()
        
        # Example calculation
        example_data = {
            'quality_name': 'Good',
            'quality_percentage': 80.0,
            'priority_name': 'High',
            'priority_multiplier': 1.2,
            'days_early': 2,
            'time_bonus': 2.0,
            'base_score': 80.0 * 1.2,
            'final_score': 80.0 * 1.2 + 2.0
        }
        
        context = {
            'settings': settings,
            'example': example_data,
            'title': 'Task Evaluation System Demo'
        }
        return render(request, 'core/evaluation_demo.html', context)

# --- User Delete View ---
class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Delete user view with role-based permissions
    """
    model = CustomUser
    template_name = 'core/delete_user.html'
    success_url = reverse_lazy('core:users')

    def test_func(self):
        user = self.request.user
        target_user = self.get_object()
        
        # Check permissions
        if user.user_type == 'admin':
            return True
        elif user.user_type == 'manager':
            return target_user.under_supervision == user
        return False

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)

# --- Settings Dashboard View ---
class SettingsDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can access settings.')
            return redirect('core:dashboard')
        # Restrict KPIs to those created by this manager
        kpi_count = KPI.objects.filter(created_by=user).count()
        # Show all quality types (managers can use admin-created quality types)
        quality_type_count = QualityType.objects.all().count()
        recent_kpis = KPI.objects.filter(created_by=user).order_by('-created_at')[:5]
        context = {
            'kpi_count': kpi_count,
            'quality_type_count': quality_type_count,
            'recent_kpis': recent_kpis,
        }
        return render(request, 'core/settings_dashboard.html', context)

# --- Update Task Statuses View ---
class UpdateTaskStatusesView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can update task statuses.')
            return redirect('core:dashboard')
        # Only include tasks of this manager's subordinates
        subordinates = CustomUser.objects.filter(under_supervision=user)
        tasks = Task.objects.filter(responsible__in=subordinates)
        total_tasks = tasks.count()
        open_tasks = tasks.filter(status='open').count()
        due_tasks = tasks.filter(status='due').count()
        closed_tasks = tasks.filter(status='closed').count()
        today = date.today()
        overdue_tasks = tasks.filter(
            close_date__lt=today,
            percentage_completion__lt=100,
            status='open'
        )
        completed_tasks = tasks.filter(
            percentage_completion__gte=100,
            status__in=['open', 'due']
        )
        context = {
            'total_tasks': total_tasks,
            'open_tasks': open_tasks,
            'due_tasks': due_tasks,
            'closed_tasks': closed_tasks,
            'overdue_tasks': overdue_tasks,
            'completed_tasks': completed_tasks,
            'tasks_need_update': overdue_tasks.count() + completed_tasks.count(),
        }
        return render(request, 'core/update_task_statuses.html', context)

    def post(self, request):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can update task statuses.')
            return redirect('core:dashboard')
        # Only update statuses for this manager's subordinates' tasks
        subordinates = CustomUser.objects.filter(under_supervision=user)
        tasks = Task.objects.filter(responsible__in=subordinates)
        today = date.today()
        closed = due = open_ = total_updated = 0
        # Closed tasks
        closed_tasks = tasks.filter(percentage_completion__gte=100, status__in=['open', 'due'])
        for task in closed_tasks:
            task.status = 'closed'
            task.save()
            closed += 1
            total_updated += 1
        # Due tasks
        due_tasks = tasks.filter(close_date__lt=today, percentage_completion__lt=100, status='open')
        for task in due_tasks:
            task.status = 'due'
            task.save()
            due += 1
            total_updated += 1
        # Open tasks
        open_tasks = tasks.filter(close_date__gte=today, percentage_completion__lt=100, status='due')
        for task in open_tasks:
            task.status = 'open'
            task.save()
            open_ += 1
            total_updated += 1
        if total_updated > 0:
            messages.success(
                request,
                f'Task statuses updated successfully! Closed: {closed}, Due: {due}, Open: {open_}'
            )
        else:
            messages.info(request, 'No task statuses needed updating.')
        return redirect('core:settings-dashboard')

# --- Notification Management Views ---
class NotificationsListView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        notifications = Notification.objects.select_related('sender').filter(recipient=user)
        read_filter = request.GET.get('filter', '')
        if read_filter == 'unread':
            notifications = notifications.filter(read=False)
        elif read_filter == 'read':
            notifications = notifications.filter(read=True)
        search_query = request.GET.get('search', '')
        if search_query:
            notifications = notifications.filter(
                Q(message__icontains=search_query) |
                Q(sender__first_name__icontains=search_query) |
                Q(sender__last_name__icontains=search_query)
            )
        paginator = Paginator(notifications, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        total_count = Notification.objects.filter(recipient=user).count()
        unread_count = Notification.objects.filter(recipient=user, read=False).count()
        read_count = total_count - unread_count
        context = {
            'notifications': page_obj,
            'search_query': search_query,
            'read_filter': read_filter,
            'total_count': total_count,
            'unread_count': unread_count,
            'read_count': read_count,
        }
        return render(request, 'core/notifications_list.html', context)

class MarkNotificationReadView(LoginRequiredMixin, View):
    def get(self, request, notification_id):
        user = request.user
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.read = True
            notification.save()
            # Invalidate unread count cache for this user so badges refresh on next render
            try:
                cache.delete(f"unread_count:{user.id}")
            except Exception:
                pass
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            else:
                messages.success(request, 'Notification marked as read.')
                return redirect('core:notifications-list')
        except Notification.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Notification not found'})
            else:
                messages.error(request, 'Notification not found.')
                return redirect('core:notifications-list')

    def post(self, request, notification_id):
        user = request.user
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.read = True
            notification.save()
            # Invalidate unread count cache for this user so badges refresh on next render
            try:
                cache.delete(f"unread_count:{user.id}")
            except Exception:
                pass
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            else:
                messages.success(request, 'Notification marked as read.')
                return redirect('core:notifications-list')
        except Notification.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Notification not found'})
            else:
                messages.error(request, 'Notification not found.')
                return redirect('core:notifications-list')

class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        updated_count = Notification.objects.filter(recipient=user, read=False).update(read=True)
        # Invalidate unread count cache for this user so badges refresh on next render
        try:
            cache.delete(f"unread_count:{user.id}")
        except Exception:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'updated_count': updated_count})
        else:
            messages.success(request, f'{updated_count} notifications marked as read.')
            return redirect('core:notifications-list')
    def get(self, request):
        return redirect('core:notifications-list')

class DeleteNotificationView(LoginRequiredMixin, View):
    def get(self, request, notification_id):
        user = request.user
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.delete()
            # Invalidate unread count cache for this user so badges refresh on next render
            try:
                cache.delete(f"unread_count:{user.id}")
            except Exception:
                pass
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            else:
                messages.success(request, 'Notification deleted.')
                return redirect('core/notifications-list')
        except Notification.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Notification not found'})
            else:
                messages.error(request, 'Notification not found.')
                return redirect('core:notifications-list')

    def post(self, request, notification_id):
        user = request.user
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.delete()
            # Invalidate unread count cache for this user so badges refresh on next render
            try:
                cache.delete(f"unread_count:{user.id}")
            except Exception:
                pass
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            else:
                messages.success(request, 'Notification deleted.')
                return redirect('core:notifications-list')
        except Notification.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Notification not found'})
            else:
                messages.error(request, 'Notification not found.')
                return redirect('core:notifications-list')

class AdminSetPasswordView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        user = request.user
        if user.user_type != 'admin':
            messages.error(request, 'Only admins can change user passwords.')
            return redirect('core:dashboard')
        target_user = get_object_or_404(CustomUser, id=user_id)
        form = AdminSetPasswordForm()
        context = {
            'form': form,
            'target_user': target_user,
        }
        return render(request, 'core/admin_set_password.html', context)

    def post(self, request, user_id):
        user = request.user
        if user.user_type != 'admin':
            messages.error(request, 'Only admins can change user passwords.')
            return redirect('core:dashboard')
        target_user = get_object_or_404(CustomUser, id=user_id)
        form = AdminSetPasswordForm(request.POST)
        if form.is_valid():
            # Capture plaintext password before saving for credential email
            new_password = form.cleaned_data.get('password1')
            form.save(target_user)
            # Create in-app notification for the user (no plaintext password in notification)
            try:
                Notification.objects.create(
                    recipient=target_user,
                    sender=user,
                    message="Your account password was updated by an administrator.",
                    link=self.request.build_absolute_uri(reverse_lazy('core:login'))
                )
            except Exception:
                pass
            # Send credentials email including the new password
            try:
                from django.core.mail import send_mail
                from django.conf import settings as dj_settings
                login_url = self.request.build_absolute_uri(reverse_lazy('core:login'))
                subject = 'Your password has been updated'
                body_lines = [
                    f"Hello {target_user.get_full_name() or target_user.username},",
                    "",
                    "An administrator has updated your account password.",
                    f"Login URL: {login_url}",
                    f"Login Email: {target_user.email}",
                    f"Your New Password is: {new_password}",
                    "",
                ]
                body = "\n".join(body_lines)
                from_email = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None) or getattr(dj_settings, 'EMAIL_HOST_USER', None) or 'no-reply@example.com'
                send_mail(subject=subject, message=body, from_email=from_email, recipient_list=[target_user.email], fail_silently=True)
            except Exception:
                pass
            context = {
                'form': AdminSetPasswordForm(),
                'target_user': target_user,
                'password_updated': True,
            }
            return render(request, 'core/admin_set_password.html', context)
        context = {
            'form': form,
            'target_user': target_user,
        }
        return render(request, 'core/admin_set_password.html', context)

class ProgressReportView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can access progress reports.')
            return redirect('core:dashboard')
        subordinates = CustomUser.objects.filter(under_supervision=user)
        selected_employee_id = request.GET.get('employee')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status_filter = request.GET.get('status', '')
        priority_filter = request.GET.get('priority', '')
        kpi_filter = request.GET.get('kpi', '')
        search_query = request.GET.get('search', '')
        export_type = request.GET.get('export', '')
        selected_employee = None
        tasks = Task.objects.none()
        available_kpis = KPI.objects.filter(created_by=user)
        available_priorities = TaskPriorityType.objects.filter(is_active=True)
        employee_progress_score = None
        progress_period_label = None
        if selected_employee_id:
            try:
                selected_employee = subordinates.get(id=selected_employee_id)
                # Load related KPI and Priority to ensure names are available in the template
                tasks = Task.objects.filter(responsible=selected_employee).select_related('kpi', 'priority')
                if start_date:
                    tasks = tasks.filter(start_date__gte=start_date)
                if end_date:
                    tasks = tasks.filter(close_date__lte=end_date)
                if status_filter:
                    tasks = tasks.filter(status=status_filter)
                if priority_filter:
                    tasks = tasks.filter(priority_id=priority_filter)
                if kpi_filter:
                    tasks = tasks.filter(kpi_id=kpi_filter)
                if search_query:
                    tasks = tasks.filter(issue_action__icontains=search_query)

                # Compute Employee Progress Score for the filtered period (or all-time if dates not provided)
                from django.db.models import Avg
                if start_date and end_date:
                    progress_record = EmployeeProgress.calculate_employee_progress(
                        employee=selected_employee,
                        manager=user,
                        period_start=start_date,
                        period_end=end_date
                    )
                    if progress_record:
                        employee_progress_score = progress_record.total_progress_score
                        progress_period_label = f"{start_date} to {end_date}"
                else:
                    eval_tasks = tasks.filter(evaluation_status='evaluated', final_score__isnull=False)
                    manager_kpis = KPI.objects.filter(created_by=user, is_active=True)
                    total_weighted_score = 0.0
                    total_weight = 0.0
                    for kpi in manager_kpis:
                        avg_score = eval_tasks.filter(kpi=kpi).aggregate(avg=Avg('final_score'))['avg'] or 0
                        total_weighted_score += float(avg_score) * float(kpi.weight)
                        total_weight += float(kpi.weight)
                    if total_weight > 0:
                        employee_progress_score = round(total_weighted_score / total_weight, 2)
                        progress_period_label = "All time (based on current filters)"
            except CustomUser.DoesNotExist:
                selected_employee = None
                tasks = Task.objects.none()
        if export_type and selected_employee:
            if export_type == 'excel':
                # Excel export using openpyxl
                wb = Workbook()
                ws = wb.active
                ws.title = 'Progress Report'
                # Summary header
                ws.append([f"Progress Report for {selected_employee.get_full_name()}"])
                ws.append([f"Period: {progress_period_label or (start_date and end_date and f'{start_date} to {end_date}') or 'Not specified'}"])
                if employee_progress_score is not None:
                    ws.append([f"Employee Progress Score: {employee_progress_score}%"])
                ws.append([])
                ws.append(['Task', 'Status', 'KPI', 'Priority', 'Start Date', 'Close Date', 'Completion (%)'])
                for task in tasks:
                    ws.append([
                        task.issue_action,
                        task.get_status_display(),
                        str(task.kpi) if task.kpi else '',
                        task.priority.name if task.priority else '-',
                        str(task.start_date),
                        str(task.close_date),
                        task.percentage_completion
                    ])
                output = BytesIO()
                wb.save(output)
                output.seek(0)
                filename = f"progress_report_{selected_employee.id}.xlsx"
                response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename={filename}'
                return response
            elif export_type == 'pdf':
                # PDF export using reportlab
                buffer = BytesIO()
                p = canvas.Canvas(buffer)
                p.setFont('Helvetica-Bold', 14)
                p.drawString(40, 800, f"Progress Report for {selected_employee.get_full_name()}")
                p.setFont('Helvetica', 10)
                y = 780
                # Summary lines
                if progress_period_label or (start_date and end_date):
                    p.drawString(40, y, f"Period: {progress_period_label or f'{start_date} to {end_date}'}")
                    y -= 16
                if employee_progress_score is not None:
                    p.drawString(40, y, f"Employee Progress Score: {employee_progress_score}%")
                    y -= 16
                headers = ['Task', 'Status', 'KPI', 'Priority', 'Start Date', 'Close Date', 'Completion (%)']
                for i, header in enumerate(headers):
                    p.drawString(40 + i*80, y, header)
                y -= 20
                for task in tasks:
                    row = [
                        (task.issue_action or '')[:15],
                        task.get_status_display(),
                        str(task.kpi) if task.kpi else '',
                        task.priority.name if task.priority else '-',
                        str(task.start_date),
                        str(task.close_date),
                        str(task.percentage_completion)
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*80, y, str(val))
                    y -= 18
                    if y < 40:
                        p.showPage()
                        y = 800
                p.save()
                buffer.seek(0)
                filename = f"progress_report_{selected_employee.id}.pdf"
                response = HttpResponse(buffer, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename={filename}'
                return response
        # Pagination
        paginator = Paginator(tasks, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        # Preserve other filters in pagination links
        base_query = request.GET.copy()
        if 'page' in base_query:
            base_query.pop('page')
        base_query = base_query.urlencode()
        context = {
            'subordinates': subordinates,
            'selected_employee': selected_employee,
            'tasks': page_obj,
            'start_date': start_date,
            'end_date': end_date,
            'status_filter': status_filter,
            'priority_filter': priority_filter,
            'kpi_filter': kpi_filter,
            'search_query': search_query,
            'available_kpis': available_kpis,
            'available_priorities': available_priorities,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'employee_progress_score': employee_progress_score,
            'progress_period_label': progress_period_label,
            'base_query': base_query,
        }
        return render(request, 'core/progress_report.html', context)

class CloseIncompleteTaskView(LoginRequiredMixin, View):
    """
    View for managers to close incomplete tasks with automatic evaluation
    """
    def get(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        
        if not task.can_user_evaluate(user):
            messages.error(request, 'You do not have permission to close this task.')
            return redirect('core:task-detail', task_id=task_id)
        
        # Check if task is already completed
        if task.percentage_completion >= 100:
            messages.warning(request, 'This task is already completed.')
            return redirect('core:task-detail', task_id=task_id)
        
        # Check if task is already evaluated
        if task.evaluation_status == 'evaluated':
            messages.warning(request, 'This task has already been evaluated.')
            return redirect('core:task-detail', task_id=task_id)
        
        form = TaskEvaluationForm(instance=task)
        context = {
            'task': task,
            'form': form,
            'title': 'Close Incomplete Task',
            'is_manager_closure': True
        }
        return render(request, 'core/evaluate_task.html', context)
    
    def post(self, request, task_id):
        user = request.user
        task = get_object_or_404(Task, id=task_id)
        
        if not task.can_user_evaluate(user):
            messages.error(request, 'You do not have permission to close this task.')
            return redirect('core:task-detail', task_id=task_id)
        
        form = TaskEvaluationForm(request.POST, instance=task)
        
        if form.is_valid():
            # Set completion to current percentage and status to closed
            task.percentage_completion = task.percentage_completion or 0
            task.status = 'closed'
            
            # Save the form data
            task = form.save(commit=False)
            # Align completion_date with the manager-selected close_date to avoid timezone/day drift
            try:
                from datetime import datetime, time as dtime
                from django.utils import timezone as dj_tz
                if getattr(task, 'close_date', None):
                    naive_dt = datetime.combine(task.close_date, dtime(12, 0))
                    task.completion_date = dj_tz.make_aware(naive_dt, dj_tz.get_current_timezone())
            except Exception:
                pass
            
            # Apply automatic evaluation with manager closure penalty
            if task.apply_automatic_evaluation(manager_closure=True):
                task.evaluated_by = user
                task.evaluated_date = timezone.now()
                task.save()
                
                penalty_message = ""
                if task.manager_closure_penalty_applied:
                    penalty_message = f" Manager closure penalty (-20%) applied."
                
                messages.success(
                    request, 
                    f'Task closed successfully! Final Score: {task.final_score:.1f}%{penalty_message}'
                )
            else:
                messages.error(request, 'Failed to evaluate task. Please check quality rating.')
                context = {
                    'task': task, 
                    'form': form, 
                    'title': 'Close Incomplete Task',
                    'is_manager_closure': True
                }
                return render(request, 'core/evaluate_task.html', context)
            
            # Notify employee
            if task.responsible:
                penalty_notice = ""
                if task.manager_closure_penalty_applied:
                    penalty_notice = " (Manager closure penalty applied)"
                
                notification_message = f"Your task '{task.issue_action[:40]}...' has been closed by your manager. Final Score: {task.final_score:.1f}%{penalty_notice}"
                Notification.objects.create(
                    recipient=task.responsible,
                    sender=user,
                    message=notification_message,
                    link=f"/projects/task/{task.id}/"
                )
            
            return redirect('core:task-detail', task_id=task_id)
        else:
            context = {
                'task': task, 
                'form': form, 
                'title': 'Close Incomplete Task',
                'is_manager_closure': True
            }
            return render(request, 'core/evaluate_task.html', context)


# --- Employee Progress Management Views ---
class EmployeeProgressListView(LoginRequiredMixin, View):
    """
    List view for employee progress - managers only
    """
    def get(self, request):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can access employee progress.')
            return redirect('core:dashboard')
        
        subordinates = CustomUser.objects.filter(under_supervision=user)
        selected_employee_id = request.GET.get('employee')
        period_start = request.GET.get('period_start')
        period_end = request.GET.get('period_end')
        
        selected_employee = None
        progress_records = []
        tasks_in_period = []
        tasks_in_period_json = []
        safe_period_start = period_start
        safe_period_end = period_end
        
        if selected_employee_id:
            try:
                selected_employee = subordinates.get(id=selected_employee_id)
                # Get or calculate progress for the selected employee
                from core.models import EmployeeProgress
                # If dates are not provided, default to current month for calculation only
                compute_start, compute_end = period_start, period_end
                if not compute_start or not compute_end:
                    from datetime import date
                    today = date.today()
                    compute_start = today.replace(day=1).strftime('%Y-%m-%d')
                    compute_end = today.strftime('%Y-%m-%d')
                safe_period_start, safe_period_end = compute_start, compute_end
                progress_record = EmployeeProgress.calculate_employee_progress(
                    employee=selected_employee,
                    manager=user,
                    period_start=compute_start,
                    period_end=compute_end
                )
                progress_records = [progress_record]
                # Fetch tasks completed within the selected period for details/charting
                tasks_in_period = Task.objects.filter(
                    responsible=selected_employee,
                    completion_date__date__gte=compute_start,
                    completion_date__date__lte=compute_end,
                    final_score__isnull=False
                ).select_related('kpi', 'priority').order_by('-completion_date')
                # Prepare JSON-serializable data for charts
                tasks_in_period_json = [
                    {
                        'id': t.id,
                        'issue_action': t.issue_action,
                        'final_score': float(t.final_score) if t.final_score is not None else None,
                        'kpi': {'name': t.kpi.name} if t.kpi else None,
                        'completion_date': t.completion_date.isoformat() if t.completion_date else None,
                    }
                    for t in tasks_in_period
                ]
            except CustomUser.DoesNotExist:
                selected_employee = None
        
        # Get total KPI weight for the manager
        total_kpi_weight = KPI.get_total_weight_for_manager(user)
        available_weight = KPI.get_available_weight_for_manager(user)
        
        context = {
            'subordinates': subordinates,
            'selected_employee': selected_employee,
            'progress_records': progress_records,
            'period_start': period_start,
            'period_end': period_end,
            'total_kpi_weight': total_kpi_weight,
            'available_weight': available_weight,
            'tasks_in_period': tasks_in_period,
            'tasks_in_period_json': tasks_in_period_json,
            'safe_period_start': safe_period_start,
            'safe_period_end': safe_period_end,
        }
        return render(request, 'core/employee_progress_list.html', context)


class EmployeeProgressDetailView(LoginRequiredMixin, View):
    """
    Detail view for employee progress - managers only
    """
    def get(self, request, employee_id):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can access employee progress.')
            return redirect('core:dashboard')
        
        try:
            employee = CustomUser.objects.get(id=employee_id, under_supervision=user)
        except CustomUser.DoesNotExist:
            messages.error(request, 'Employee not found.')
            return redirect('core:employee-progress-list')
        
        period_start = request.GET.get('period_start')
        period_end = request.GET.get('period_end')

        # Get or calculate progress only if both dates provided
        from core.models import EmployeeProgress
        progress_record = None
        if period_start and period_end:
            progress_record = EmployeeProgress.calculate_employee_progress(
                employee=employee,
                manager=user,
                period_start=period_start,
                period_end=period_end
            )
        
        # Get historical progress records
        historical_records = EmployeeProgress.objects.filter(
            employee=employee,
            manager=user
        ).order_by('-period_end')[:10]
        
        context = {
            'employee': employee,
            'progress_record': progress_record,
            'historical_records': historical_records,
            'period_start': period_start,
            'period_end': period_end,
        }
        return render(request, 'core/employee_progress_detail.html', context)


class RecalculateProgressView(LoginRequiredMixin, View):
    """
    View to recalculate employee progress - managers only
    """
    def post(self, request, employee_id):
        user = request.user
        if user.user_type != 'manager':
            messages.error(request, 'Only managers can recalculate progress.')
            return redirect('core:dashboard')
        
        try:
            employee = CustomUser.objects.get(id=employee_id, under_supervision=user)
        except CustomUser.DoesNotExist:
            messages.error(request, 'Employee not found.')
            return redirect('core:employee-progress-list')
        
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        
        if not period_start or not period_end:
            messages.error(request, 'Please provide both start and end dates.')
            return redirect('core:employee-progress-detail', employee_id=employee_id)
        
        # Recalculate progress
        from core.models import EmployeeProgress
        progress_record = EmployeeProgress.calculate_employee_progress(
            employee=employee,
            manager=user,
            period_start=period_start,
            period_end=period_end,
            force_recalculate=True
        )
        
        messages.success(request, f'Progress recalculated successfully. Total Score: {progress_record.total_progress_score}%')
        return redirect('core:employee-progress-detail', employee_id=employee_id)
