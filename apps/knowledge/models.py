from django.db import models
import uuid

class DiscoverySource(models.TextChoices):
    REPOSITORY_SCANNER = "REPOSITORY_SCANNER", "Repository Scanner"
    TECH_DISCOVERY = "TECH_DISCOVERY", "Technology Discovery"
    TREE_SITTER = "TREE_SITTER", "Tree-sitter Analyzer"
    LSP_ANALYZER = "LSP_ANALYZER", "LSP Analyzer"
    AI_ANALYZER = "AI_ANALYZER", "AI Analyzer"
    USER_INPUT = "USER_INPUT", "User Input"
    REPOSITORY_CLASSIFIER = "REPOSITORY_CLASSIFIER", "Repository Classifier"

class KnowledgeItemType:
    PROJECT = "PROJECT"
    REPOSITORY = "REPOSITORY"
    DIRECTORY = "DIRECTORY"
    FILE = "FILE"
    TECHNOLOGY = "TECHNOLOGY"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    INTERFACE = "INTERFACE"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    QUEUE = "QUEUE"
    API = "API"
    ENDPOINT = "ENDPOINT"
    DEPLOYMENT = "DEPLOYMENT"
    CONTAINER = "CONTAINER"
    KUBERNETES_RESOURCE = "KUBERNETES_RESOURCE"
    TERRAFORM_RESOURCE = "TERRAFORM_RESOURCE"
    CONFIGURATION = "CONFIGURATION"
    DOCUMENT = "DOCUMENT"

class KnowledgeItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='knowledge_items')
    repository = models.ForeignKey('repositories.Repository', on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_items')
    artifact = models.ForeignKey('artifacts.ProjectArtifact', on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_items')
    analysis_job = models.ForeignKey('analysis.AnalysisJob', on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_items', db_index=True)
    
    item_type = models.CharField(max_length=100, db_index=True)
    value = models.TextField()
    summary = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    confidence_score = models.FloatField(default=1.0)
    discovered_by = models.CharField(max_length=50, choices=DiscoverySource.choices, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["repository", "item_type"]),
            models.Index(fields=["repository", "analysis_job"]),
            models.Index(fields=["analysis_job"]),
        ]

    def __str__(self):
        return f"{self.item_type}: {self.value[:50]}"

class KnowledgeRelationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_item = models.ForeignKey(KnowledgeItem, on_delete=models.CASCADE, related_name='outgoing_relationships')
    target_item = models.ForeignKey(KnowledgeItem, on_delete=models.CASCADE, related_name='incoming_relationships')
    analysis_job = models.ForeignKey('analysis.AnalysisJob', on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_relationships', db_index=True)
    
    relationship_type = models.CharField(max_length=100, db_index=True)
    confidence = models.FloatField(default=1.0)
    metadata = models.JSONField(default=dict, blank=True)
    discovered_by = models.CharField(max_length=50, choices=DiscoverySource.choices, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["relationship_type"]),
            models.Index(fields=["discovered_by"]),
            models.Index(fields=["analysis_job"]),
            models.Index(fields=["source_item", "relationship_type"]),
            models.Index(fields=["target_item", "relationship_type"]),
        ]

    def __str__(self):
        return f"{self.source_item.id} -[{self.relationship_type}]-> {self.target_item.id}"
