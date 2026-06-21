from django.db import models
import uuid

class KnowledgeItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='knowledge_items')
    repository = models.ForeignKey('repositories.Repository', on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_items')
    artifact = models.ForeignKey('artifacts.ProjectArtifact', on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_items')
    
    item_type = models.CharField(max_length=100) # e.g. Compliance Requirement, Goal, Constraint
    value = models.TextField()
    summary = models.TextField(blank=True, null=True)
    confidence_score = models.FloatField(default=1.0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_type}: {self.value[:50]}"

class KnowledgeRelationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_item = models.ForeignKey(KnowledgeItem, on_delete=models.CASCADE, related_name='outgoing_relationships')
    target_item = models.ForeignKey(KnowledgeItem, on_delete=models.CASCADE, related_name='incoming_relationships')
    relationship_type = models.CharField(max_length=100) # e.g. REQUIRES, HAS_GOAL, CALLS
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_item.id} -[{self.relationship_type}]-> {self.target_item.id}"
