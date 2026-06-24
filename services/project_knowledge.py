from apps.projects.models import Project
from apps.artifacts.models import ProjectArtifact

def get_project_knowledge_base(project_id, user):
    """
    Retrieves a unified view of the project's knowledge base,
    including configuration input JSON fields and associated documents.
    """
    try:
        project = Project.objects.get(id=project_id, owner=user)
    except (Project.DoesNotExist, ValueError, TypeError):
        return None

    # Fetch associated artifacts
    artifacts = ProjectArtifact.objects.filter(project=project)
    
    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "knowledge_base": {
            "business_context": project.business_context,
            "goals": project.goals,
            "constraints": project.constraints,
            "compliance": project.compliance,
            "availability": project.availability
        },
        "documents": [
            {
                "name": art.file_name,
                "category": art.artifact_type
            }
            for art in artifacts
        ]
    }
