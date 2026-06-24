import os
import shutil
import tempfile
import uuid
import git
from pathlib import Path
from django.utils import timezone
from django.db import transaction

from apps.analysis.models import AnalysisJob
from apps.knowledge.models import KnowledgeItem, KnowledgeRelationship, DiscoverySource, KnowledgeItemType

EXCLUDED_DIRECTORIES = [
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build"
]

class RepositoryScannerService:
    def scan_repository(self, analysis_job_id: uuid.UUID) -> dict:
        """
        Main entry point for scanning a repository associated with an AnalysisJob.
        """
        try:
            job = AnalysisJob.objects.get(id=analysis_job_id)
        except AnalysisJob.DoesNotExist as e:
            raise ValueError(f"AnalysisJob with id {analysis_job_id} does not exist.") from e

        job.status = "Running"
        job.started_at = timezone.now()
        job.save()

        repository = job.repository
        if not repository:
            job.status = "Failed"
            job.error_message = "No repository associated with this AnalysisJob."
            job.completed_at = timezone.now()
            job.save()
            return {"status": "Failed", "error": job.error_message}

        project = job.project
        workspace_path = None
        
        try:
            # 1. Create unique temporary workspace
            workspace_dir = tempfile.mkdtemp(prefix=f"caip_{analysis_job_id}_")
            workspace_path = Path(workspace_dir)

            # 2. Clone repository
            self.clone_repository(repository.url, repository.branch, workspace_path)

            # 3. Walk directory tree and prepare nodes
            
            # Create root REPOSITORY node
            repo_name = repository.url.split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            if not repo_name:
                repo_name = "repository"
                
            root_node = KnowledgeItem(
                project=project,
                repository=repository,
                analysis_job=job,
                item_type=KnowledgeItemType.REPOSITORY,
                value=repo_name,
                metadata={
                    "repository_id": str(repository.id),
                    "url": repository.url,
                    "branch": repository.branch or ""
                },
                discovered_by=DiscoverySource.REPOSITORY_SCANNER
            )
            
            nodes_map = {
                "": root_node
            }
            
            # Traverse
            for root, dirs, files in os.walk(workspace_path):
                # Prune excluded directories in-place
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRECTORIES]
                
                # Get path relative to the workspace root
                rel_root = os.path.relpath(root, workspace_path)
                if rel_root == ".":
                    rel_root = ""
                else:
                    rel_root = rel_root.replace("\\", "/")
                
                # Process directories
                for d in dirs:
                    rel_dir_path = os.path.join(rel_root, d).replace("\\", "/")
                    if rel_dir_path.startswith("./"):
                        rel_dir_path = rel_dir_path[2:]
                        
                    dir_node = KnowledgeItem(
                        project=project,
                        repository=repository,
                        analysis_job=job,
                        item_type=KnowledgeItemType.DIRECTORY,
                        value=rel_dir_path,
                        metadata={
                            "name": d,
                            "relative_path": rel_dir_path
                        },
                        discovered_by=DiscoverySource.REPOSITORY_SCANNER
                    )
                    nodes_map[rel_dir_path] = dir_node
                    
                # Process files
                for f in files:
                    # Skip .git files at root if they slip in
                    if f in [".gitignore", ".gitmodules"] or f.startswith(".git"):
                        continue
                        
                    rel_file_path = os.path.join(rel_root, f).replace("\\", "/")
                    if rel_file_path.startswith("./"):
                        rel_file_path = rel_file_path[2:]
                        
                    abs_file_path = Path(root) / f
                    try:
                        file_size = abs_file_path.stat().st_size
                    except OSError:
                        file_size = 0
                        
                    ext = abs_file_path.suffix
                    
                    file_node = KnowledgeItem(
                        project=project,
                        repository=repository,
                        analysis_job=job,
                        item_type=KnowledgeItemType.FILE,
                        value=rel_file_path,
                        metadata={
                            "file_name": f,
                            "extension": ext,
                            "relative_path": rel_file_path,
                            "size": file_size
                        },
                        discovered_by=DiscoverySource.REPOSITORY_SCANNER
                    )
                    nodes_map[rel_file_path] = file_node

            # 4. Save items in bulk
            all_items = list(nodes_map.values())
            with transaction.atomic():
                KnowledgeItem.objects.bulk_create(all_items)
                
            # 5. Build relationships
            relationships = []
            dir_count = 0
            file_count = 0
            
            for rel_path, node in nodes_map.items():
                if rel_path == "":
                    # Root repository node has no parent in repo
                    continue
                    
                # Find parent path
                if "/" in rel_path:
                    parent_path = "/".join(rel_path.split("/")[:-1])
                else:
                    parent_path = ""
                    
                parent_node = nodes_map.get(parent_path)
                if parent_node:
                    rel = KnowledgeRelationship(
                        source_item=parent_node,
                        target_item=node,
                        analysis_job=job,
                        relationship_type="CONTAINS",
                        discovered_by=DiscoverySource.REPOSITORY_SCANNER
                    )
                    relationships.append(rel)
                    
                if node.item_type == KnowledgeItemType.DIRECTORY:
                    dir_count += 1
                elif node.item_type == KnowledgeItemType.FILE:
                    file_count += 1

            # 6. Save relationships in bulk
            with transaction.atomic():
                KnowledgeRelationship.objects.bulk_create(relationships)

            # 7. Save metrics and update job status
            job.status = "Completed"
            job.metadata = {
                "directories": dir_count,
                "files": file_count,
                "relationships": len(relationships)
            }
            job.completed_at = timezone.now()
            job.save()

            return {
                "status": "Completed",
                "directories": dir_count,
                "files": file_count,
                "relationships": len(relationships)
            }

        except Exception as e:
            # Handle failure
            job.status = "Failed"
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise e

        finally:
            # 8. Clean up workspace
            if workspace_path:
                self.cleanup_workspace(workspace_path)

    def clone_repository(self, repo_url: str, branch: str, clone_path: Path):
        """
        Clones repository into the destination path using GitPython.
        """
        try:
            kwargs = {}
            if branch:
                kwargs["branch"] = branch
            git.Repo.clone_from(repo_url, clone_path, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {str(e)}") from e

    def cleanup_workspace(self, workspace_path: Path):
        """
        Safely deletes directory workspace and all contents.
        """
        if workspace_path.exists() and workspace_path.is_dir():
            shutil.rmtree(workspace_path, ignore_errors=True)
