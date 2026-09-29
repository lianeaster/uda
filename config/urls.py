from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Головна «парасолька» — Український центр харчових інновацій (UFIC).
    # Академія дистиляції — його підрозділ, тому живе під /academy/.
    path('', include('center.urls')),
    path('academy/', include('core.urls')),
    # Сторінки Академії до переїзду: посилання на них уже розійшлися
    # (соцмережі, листи), тож ведемо туди, де вони тепер. Якір #zayavka
    # браузер переносить сам.
    path('courses/', RedirectView.as_view(pattern_name='core:courses', permanent=True)),
    path('lecturers/', RedirectView.as_view(pattern_name='core:lecturers', permanent=True)),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('schedule/', include('schedule.urls')),
]

# Фото карток лежать у MEDIA_ROOT. На проді їх віддає веб-сервер, у DEBUG —
# сам Django, інакше свіжозавантажене фото просто не показалося б.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
