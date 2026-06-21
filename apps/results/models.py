from django.db import models

import uuid

class AnalysisResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('analysis.AnalysisJob', on_delete=models.CASCADE, related_name='results')
    repository = models.ForeignKey('repositories.Repository', on_delete=models.CASCADE, related_name='results')
    result_type = models.CharField(max_length=100)
    result_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.result_type} ({self.id})"
