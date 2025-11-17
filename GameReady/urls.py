"""
URL configuration for GameReady project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from core.views import CustomLoginView, CustomPasswordResetView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Password reset URLs (with rate limiting)
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]

# Serve static files (both development and production)
# Ensure STATIC_ROOT is a string for static() function
static_root = str(settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') else settings.STATIC_ROOT
urlpatterns += static(settings.STATIC_URL, document_root=static_root)

# Serve media files explicitly (works in both development and production)
# Django's static() helper only works with DEBUG=True, so we use serve() view directly
media_root = str(settings.MEDIA_ROOT) if hasattr(settings, 'MEDIA_ROOT') else settings.MEDIA_ROOT
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': media_root}),
]
