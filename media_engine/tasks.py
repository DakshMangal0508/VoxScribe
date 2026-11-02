import logging
import os

from celery import shared_task
from django.utils import timezone
import whisper

from .models import LectureRecording

logger = logging.getLogger(__name__)
_whisper_model = None
_diarization_pipeline = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        model_name = os.environ.get("WHISPER_MODEL", "base")
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model


def _get_diarization_pipeline():
    """Load pyannote only when a Hugging Face token is configured."""
    global _diarization_pipeline
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        return None
    if _diarization_pipeline is None:
        from pyannote.audio import Pipeline

        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1",
            token=token,
        )
    return _diarization_pipeline


def _format_diarized_transcript(segments, diarization):
    """Attach the speaker with the greatest time overlap to each ASR segment."""
    diarization = getattr(diarization, "speaker_diarization", diarization)
    turns = [
        (turn.start, turn.end, speaker)
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
    lines = []
    for segment in segments:
        start, end = segment.get("start", 0), segment.get("end", 0)
        overlaps = {}
        for turn_start, turn_end, speaker in turns:
            overlap = max(0, min(end, turn_end) - max(start, turn_start))
            if overlap:
                overlaps[speaker] = overlaps.get(speaker, 0) + overlap
        speaker = max(overlaps, key=overlaps.get) if overlaps else None
        text = segment.get("text", "").strip()
        if text:
            lines.append(f"{speaker or 'Unknown speaker'}: {text}")
    return "\n".join(lines)

@shared_task
def transcribe_audio_task(recording_id):
    recording = LectureRecording.objects.get(uid=recording_id)
    recording.status = LectureRecording.ProcessingState.PROCESSING
    recording.save(update_fields=["status"])

    try:
        model = _get_whisper_model()
        transcribe_options = {}
        if recording.spoken_language and recording.spoken_language != "auto":
            transcribe_options["language"] = recording.spoken_language
        result = model.transcribe(recording.source_file.path, **transcribe_options)

        recording.raw_transcript = result["text"].strip()
        try:
            diarization = _get_diarization_pipeline()
            if diarization is not None:
                diarized_text = _format_diarized_transcript(
                    result.get("segments", []), diarization(recording.source_file.path)
                )
                if diarized_text:
                    recording.raw_transcript = diarized_text
            else:
                logger.info(
                    "Speaker diarization skipped for %s: set HF_TOKEN and install pyannote.audio",
                    recording_id,
                )
        except Exception:
            # Diarization is an enhancement: keep the successful Whisper transcript.
            logger.exception("Speaker diarization failed for recording %s", recording_id)
        recording.spoken_language = result.get("language", recording.spoken_language)
        recording.status = LectureRecording.ProcessingState.COMPLETED
        recording.processed_on = timezone.now()
        recording.save(update_fields=["raw_transcript", "spoken_language", "status", "processed_on"])
        return {"status": recording.status, "recording_id": str(recording_id)}
    except Exception as exc:
        logger.exception("Transcription failed for recording %s", recording_id)
        recording.status = LectureRecording.ProcessingState.FAILED
        recording.raw_transcript = f"Transcription failed: {exc}"
        recording.processed_on = timezone.now()
        recording.save(update_fields=["raw_transcript", "status", "processed_on"])
        return {"status": recording.status, "recording_id": str(recording_id)}
