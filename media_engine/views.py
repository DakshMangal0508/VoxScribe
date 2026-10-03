from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import LectureRecording
from scripts.poc_transcribe import run_local_asr


def dashboard_view(request):
    """Displays uploaded recordings and handles synchronous Stage 2 transcription."""
    if request.method == "POST" and request.FILES.get("source_file"):
        media_file = request.FILES["source_file"]
        title = request.POST.get("title") or media_file.name
        lang_choice = request.POST.get("spoken_language", "auto")

        recording = LectureRecording.objects.create(
            title=title,
            source_file=media_file,
            spoken_language=lang_choice,
            status=LectureRecording.ProcessingState.PROCESSING,
        )

        try:
            lang_arg = None if lang_choice == "auto" else lang_choice
            asr_output = run_local_asr(
                recording.source_file.path,
                model_tier="tiny",
                lang=lang_arg,
            )
            recording.raw_transcript = asr_output.get("text", "").strip()
            recording.spoken_language = asr_output.get("language", lang_choice)
            recording.status = LectureRecording.ProcessingState.READY
            recording.processed_on = timezone.now()
            recording.save()
        except Exception as exc:
            recording.raw_transcript = f"Transcription failed: {exc}"
            recording.status = LectureRecording.ProcessingState.ERROR
            recording.save()

        return redirect("recording_detail", uid=recording.uid)

    recordings = LectureRecording.objects.all()
    return render(request, "media_engine/dashboard.html", {"recordings": recordings})


def recording_detail_view(request, uid):
    recording = get_object_or_404(LectureRecording, uid=uid)
    return render(request, "media_engine/detail.html", {"recording": recording})