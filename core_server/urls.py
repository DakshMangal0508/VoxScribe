from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from media_engine import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard_view, name="dashboard"),
    path("recording/<uuid:uid>/", views.recording_detail_view, name="recording_detail"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)