from django.db import models

import uuid

class Repository(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='repositories')
    url = models.URLField(max_length=2000)
    branch = models.CharField(max_length=255, blank=True, null=True)
    provider = models.CharField(max_length=100) # e.g. GitHub, GitLab, Bitbucket
    status = models.CharField(max_length=100, default='pending')
    metadata = models.JSONField(default=dict, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url
