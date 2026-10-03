from django.db import models

import uuid
from django.db import models


class LectureRecording(models.Model):
    class ProcessingState(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Completed"
        ERROR = "ERROR", "Failed"

    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    source_file = models.FileField(upload_to="uploads/%Y/%m/")
    spoken_language = models.CharField(max_length=16, blank=True, default="auto")
    status = models.CharField(
        max_length=20,
        choices=ProcessingState.choices,
        default=ProcessingState.QUEUED,
    )
    raw_transcript = models.TextField(blank=True)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    processed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_on"]

    def __str__(self):
        return f"{self.title} ({self.status})"# Create your models here.
