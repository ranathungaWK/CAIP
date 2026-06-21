from django.db import models

import uuid

class AnalysisJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='analysis_jobs')
    repository = models.ForeignKey('repositories.Repository', on_delete=models.CASCADE, null=True, blank=True, related_name='analysis_jobs')
    job_type = models.CharField(max_length=100)
    status = models.CharField(max_length=100) # Pending, Running, Completed, Failed
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_type} ({self.status})"
