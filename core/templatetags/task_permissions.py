from django import template

register = template.Library()

@register.filter
def can_user_edit(task, user):
    """Check if user can edit the task"""
    return task.can_user_edit(user)

@register.filter
def can_user_upload_file(task, user):
    """Check if user can upload files to the task"""
    return task.can_user_upload_file(user)

@register.filter
def can_user_download_file(task, user):
    """Check if user can download files from the task"""
    return task.can_user_download_file(user)

@register.filter
def can_user_evaluate(task, user):
    """Check if user can evaluate the task"""
    return task.can_user_evaluate(user) 