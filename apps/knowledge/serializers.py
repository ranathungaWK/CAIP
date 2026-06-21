from rest_framework import serializers
from .models import KnowledgeItem, KnowledgeRelationship

class KnowledgeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

class KnowledgeRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeRelationship
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
