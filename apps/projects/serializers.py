from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'created_at', 'updated_at',
            'business_context', 'goals', 'constraints', 'compliance', 'availability', 'repository_data'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']
