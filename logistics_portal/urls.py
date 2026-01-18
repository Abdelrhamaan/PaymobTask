"""
URL configuration for logistics_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
from redis import Redis


def health_check(request):
    """Health check endpoint to verify DB, Redis, and Celery."""
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'redis': 'unknown',
        'celery': 'unknown'
    }
    
    # Check database
    try:
        connection.ensure_connection()
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check Redis
    try:
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        health_status['redis'] = 'connected'
    except Exception as e:
        health_status['redis'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check Celery (basic check - just verify we can import)
    try:
        from logistics_portal.celery import app
        health_status['celery'] = 'configured'
    except Exception as e:
        health_status['celery'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    return JsonResponse(health_status)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('health/', health_check, name='health_check'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
