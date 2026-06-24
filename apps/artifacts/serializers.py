from rest_framework import serializers
from django.core.exceptions import ValidationError
import os
from .models import ProjectArtifact

class ProjectArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectArtifact
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

    def validate(self, data):
        project = data.get('project')
        artifact_type = data.get('artifact_type')
        file_name = data.get('file_name')
        file_size = data.get('file_size')

        if not file_name:
            raise serializers.ValidationError({"file_name": "File name is required."})

        # 1. Duplicate detection
        # Check if another artifact with the same file_name exists in the project for this type
        instance_id = self.instance.id if self.instance else None
        queryset = ProjectArtifact.objects.filter(
            project=project,
            artifact_type=artifact_type,
            file_name=file_name
        )
        if instance_id:
            queryset = queryset.exclude(id=instance_id)
        if queryset.exists():
            raise serializers.ValidationError(
                {"file_name": f"An artifact with the name '{file_name}' already exists in this category."}
            )

        # Helper to get file extension
        _, ext = os.path.splitext(file_name.lower())

        # 2. File validation rules by category
        if artifact_type == ProjectArtifact.IAC_ARTIFACT:
            # Limits: Max 20 files, Max 5 MB (5 * 1024 * 1024 bytes)
            # Supported extensions: .tf, .tfvars, .yaml, .yml, .json
            allowed_exts = ['.tf', '.tfvars', '.yaml', '.yml', '.json']
            if ext not in allowed_exts:
                raise serializers.ValidationError(
                    {"file_name": f"Unsupported file type. Supported extensions for IaC: {', '.join(allowed_exts)}"}
                )
            if file_size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"file_size": "File size exceeds the maximum limit of 5 MB."}
                )
            # Count validation
            count = ProjectArtifact.objects.filter(project=project, artifact_type=artifact_type).count()
            if not instance_id and count >= 20:
                raise serializers.ValidationError(
                    {"file_name": "Maximum file upload limit of 20 files reached for IaC artifacts."}
                )

        elif artifact_type == ProjectArtifact.KUBERNETES_ARTIFACT:
            # Limits: Max 50 files, Max 2 MB (2 * 1024 * 1024 bytes)
            # Supported extensions: .yaml, .yml
            allowed_exts = ['.yaml', '.yml']
            if ext not in allowed_exts:
                raise serializers.ValidationError(
                    {"file_name": f"Unsupported file type. Supported extensions for Kubernetes: {', '.join(allowed_exts)}"}
                )
            if file_size > 2 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"file_size": "File size exceeds the maximum limit of 2 MB."}
                )
            # Count validation
            count = ProjectArtifact.objects.filter(project=project, artifact_type=artifact_type).count()
            if not instance_id and count >= 50:
                raise serializers.ValidationError(
                    {"file_name": "Maximum file upload limit of 50 files reached for Kubernetes configuration."}
                )

        elif artifact_type == ProjectArtifact.CONTAINER_ARTIFACT:
            # Limits: Max 20 files, Max 1 MB (1 * 1024 * 1024 bytes)
            # Supported filenames/extensions: Dockerfile, docker-compose.yml, docker-compose.yaml, or Dockerfile.*
            name_lower = file_name.lower()
            is_valid_name = (
                name_lower == 'dockerfile' or 
                name_lower == 'docker-compose.yml' or 
                name_lower == 'docker-compose.yaml' or 
                name_lower.startswith('dockerfile.')
            )
            if not is_valid_name:
                raise serializers.ValidationError(
                    {"file_name": "Unsupported file. Must be a Dockerfile, docker-compose.yml, docker-compose.yaml, or Dockerfile.*"}
                )
            if file_size > 1 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"file_size": "File size exceeds the maximum limit of 1 MB."}
                )
            # Count validation
            count = ProjectArtifact.objects.filter(project=project, artifact_type=artifact_type).count()
            if not instance_id and count >= 20:
                raise serializers.ValidationError(
                    {"file_name": "Maximum file upload limit of 20 files reached for Containerization configuration."}
                )

        # For business, compliance, and architecture documents, check if they are PDFs
        elif artifact_type in [ProjectArtifact.BUSINESS_DOCUMENT, ProjectArtifact.COMPLIANCE_DOCUMENT, ProjectArtifact.ARCHITECTURE_DOCUMENT]:
            if ext != '.pdf':
                raise serializers.ValidationError(
                    {"file_name": "Only PDF files are allowed for business, compliance, and architecture documents."}
                )
            # Standard PDF size limit (e.g. 10 MB)
            if file_size > 10 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"file_size": "File size exceeds the maximum limit of 10 MB."}
                )
            # Count limit
            count = ProjectArtifact.objects.filter(project=project, artifact_type=artifact_type).count()
            if not instance_id and count >= 5:
                raise serializers.ValidationError(
                    {"file_name": f"Maximum file upload limit reached for {artifact_type.replace('_', ' ').title()}."}
                )

        return data
