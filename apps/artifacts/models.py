from django.db import models
import uuid

class ProjectArtifact(models.Model):
    BUSINESS_DOCUMENT = 'business_document'
    COMPLIANCE_DOCUMENT = 'compliance_document'
    ARCHITECTURE_DOCUMENT = 'architecture_document'
    IAC_ARTIFACT = 'iac_artifact'
    KUBERNETES_ARTIFACT = 'kubernetes_artifact'
    CONTAINER_ARTIFACT = 'container_artifact'

    ARTIFACT_TYPE_CHOICES = [
        (BUSINESS_DOCUMENT, 'Business Document'),
        (COMPLIANCE_DOCUMENT, 'Compliance & Security Document'),
        (ARCHITECTURE_DOCUMENT, 'Architecture Decisions Document'),
        (IAC_ARTIFACT, 'IaC Artifact'),
        (KUBERNETES_ARTIFACT, 'Kubernetes Configuration'),
        (CONTAINER_ARTIFACT, 'Containerization Configuration'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='artifacts')
    file_name = models.CharField(max_length=255)
    artifact_type = models.CharField(max_length=100, choices=ARTIFACT_TYPE_CHOICES)
    bucket_name = models.CharField(max_length=100)
    storage_path = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    file_size = models.BigIntegerField(default=0)
    upload_status = models.CharField(max_length=50, default='completed')
    uploaded_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_artifacts')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} ({self.get_artifact_type_display()})"
