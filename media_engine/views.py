import os

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import LectureRecording
from .tasks import transcribe_audio_task

def dashboard_view(request):
    if request.method == 'POST' and request.FILES.get('source_file'):
        audio_file = request.FILES['source_file']
        recording = LectureRecording.objects.create(
            title=request.POST.get('title') or audio_file.name,
            source_file=audio_file,
            spoken_language=request.POST.get('spoken_language', 'auto'),
        )
        broker_url = settings.CELERY_BROKER_URL
        if not broker_url or any(token in broker_url for token in ('YOUR_UPSTASH', ':PORT')):
            recording.status = LectureRecording.ProcessingState.FAILED
            recording.raw_transcript = (
                'Background transcription is not configured. Set CELERY_BROKER_URL '
                'to a valid Redis URL and restart the server.'
            )
            recording.save(update_fields=['status', 'raw_transcript'])
        else:
            try:
                transcribe_audio_task.delay(str(recording.uid))
            except Exception as exc:
                recording.status = LectureRecording.ProcessingState.FAILED
                recording.raw_transcript = f'Could not queue transcription: {exc}'
                recording.save(update_fields=['status', 'raw_transcript'])
        return redirect('recording_detail', uid=recording.uid)

    recordings = LectureRecording.objects.all()
    return render(request, 'media_engine/dashboard.html', {'recordings': recordings})

def detail_view(request, uid):
    recording = get_object_or_404(LectureRecording, uid=uid)
    diarization_enabled = bool(
        os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
    )
    return render(request, 'media_engine/detail.html', {
        'recording': recording,
        'diarization_enabled': diarization_enabled,
    })


@require_POST
def retry_transcription_view(request, uid):
    recording = get_object_or_404(LectureRecording, uid=uid)
    if recording.status not in (
        LectureRecording.ProcessingState.FAILED,
        LectureRecording.ProcessingState.COMPLETED,
    ):
        return redirect('recording_detail', uid=recording.uid)

    broker_url = settings.CELERY_BROKER_URL
    if not broker_url or any(token in broker_url for token in ('YOUR_UPSTASH', '<upstash-')):
        recording.raw_transcript = (
            'Background transcription is not configured. Set CELERY_BROKER_URL in .env '
            'to a valid Redis URL, then restart Django and the Celery worker.'
        )
        recording.save(update_fields=['raw_transcript'])
        return redirect('recording_detail', uid=recording.uid)

    recording.status = LectureRecording.ProcessingState.QUEUED
    recording.raw_transcript = ''
    recording.processed_on = None
    recording.save(update_fields=['status', 'raw_transcript', 'processed_on'])
    try:
        transcribe_audio_task.delay(str(recording.uid))
    except Exception as exc:
        recording.status = LectureRecording.ProcessingState.FAILED
        recording.raw_transcript = f'Could not queue transcription: {exc}'
        recording.processed_on = timezone.now()
        recording.save(update_fields=['status', 'raw_transcript', 'processed_on'])

    return redirect('recording_detail', uid=recording.uid)
