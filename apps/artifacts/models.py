from django.db import models
import uuid

class ProjectArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='artifacts')
    name = models.CharField(max_length=255)
    artifact_type = models.CharField(max_length=100) # e.g. Business, Compliance, Security
    bucket_name = models.CharField(max_length=100)
    storage_path = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    size = models.BigIntegerField(default=0)
    upload_status = models.CharField(max_length=50, default='completed')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.artifact_type})"
