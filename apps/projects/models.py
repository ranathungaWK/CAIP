from django.db import models
import uuid

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(
        'authentication.User', 
        on_delete=models.CASCADE, 
        related_name='projects'
    )
    
    # Structured Inputs
    business_context = models.JSONField(default=dict, blank=True)
    goals = models.JSONField(default=dict, blank=True)
    constraints = models.JSONField(default=dict, blank=True)
    compliance = models.JSONField(default=dict, blank=True)
    availability = models.JSONField(default=dict, blank=True)
    repository_data = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
