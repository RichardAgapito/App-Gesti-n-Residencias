from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')), 
    path('admin_dashboard/', include('complejos.urls')),
    path('visitas/', include('visitas.urls')),
    path('avisos/', include('avisos.urls')),
    path('finanzas/', include('finanzas.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)