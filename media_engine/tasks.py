import whisper
from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import LectureRecording

@shared_task(bind=True)
def run_whisper_transcription(self, record_id, file_path):
    record = None
    try:
        record = LectureRecording.objects.get(uid=record_id)
        record.status = LectureRecording.ProcessingState.PROCESSING
        record.save()

        # Load Whisper model locally
        model = whisper.load_model("base")
        full_path = default_storage.path(file_path)
        
        # Run transcription
        result = model.transcribe(full_path)
        
        # Save results
        record.raw_transcript = result["text"].strip()
        record.spoken_language = result.get("language", record.spoken_language)
        record.status = LectureRecording.ProcessingState.READY
        record.processed_on = timezone.now()
        record.save()
    except Exception as e:
        if record is not None:
            record.status = LectureRecording.ProcessingState.ERROR
            record.raw_transcript = f"Transcription failed: {e}"
            record.save()
        raise
