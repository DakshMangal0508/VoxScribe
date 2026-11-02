from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path

from media_engine.models import LectureRecording
from media_engine import views


def check_status_api(request, pk):
    recording = get_object_or_404(LectureRecording, uid=pk)
    return JsonResponse({
        "status": recording.status,
        "transcript": recording.raw_transcript if recording.status == 'COMPLETED' else "",
        "error": recording.raw_transcript if recording.status == 'FAILED' else "",
    })


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard_view, name="dashboard"),
    path("recording/<uuid:uid>/", views.detail_view, name="recording_detail"),
    path("recording/<uuid:uid>/retry/", views.retry_transcription_view, name="retry_transcription"),
    path("api/status/<uuid:pk>/", check_status_api, name="check_status_api"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
