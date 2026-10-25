from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import LectureRecording
from .tasks import run_whisper_transcription


def dashboard_view(request):
    if request.method == "POST" and request.FILES.get("source_file"):
        media_file = request.FILES["source_file"]
        lang_choice = request.POST.get("spoken_language", "auto")
        recording = LectureRecording.objects.create(
            title=request.POST.get("title") or media_file.name,
            source_file=media_file,
            spoken_language=lang_choice,
            status=LectureRecording.ProcessingState.QUEUED,
        )
        run_whisper_transcription.delay(str(recording.uid), recording.source_file.name)
        return redirect("recording_detail", uid=recording.uid)

    recordings = LectureRecording.objects.all()
    return render(request, "media_engine/dashboard.html", {"recordings": recordings})


def recording_detail_view(request, uid):
    recording = get_object_or_404(LectureRecording, uid=uid)
    return render(request, "media_engine/detail.html", {"recording": recording})
