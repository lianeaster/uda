from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('schedule/', include('schedule.urls')),
]

# Фото карток лежать у MEDIA_ROOT. На проді їх віддає веб-сервер, у DEBUG —
# сам Django, інакше свіжозавантажене фото просто не показалося б.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
