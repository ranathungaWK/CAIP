from rest_framework import serializers
from .models import ProjectArtifact

class ProjectArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectArtifact
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at']
