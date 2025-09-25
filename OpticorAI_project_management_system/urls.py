"""
URL configuration for OpticorAI_project_management_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    # Expose Django i18n endpoints (set_language) without changing app URLs
    path('i18n/', include('django.conf.urls.i18n')),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Always serve media files from MEDIA_ROOT
# Note: In production this is acceptable for small apps, but for scale or persistence
# you should use a proper object storage (e.g., S3/Cloudinary) or a persistent disk.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)






