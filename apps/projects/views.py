from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer
from apps.authentication.authentication import SupabaseAuthentication
from services.project_knowledge import get_project_knowledge_base

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'], url_path='knowledge-base')
    def knowledge_base(self, request, pk=None):
        data = get_project_knowledge_base(pk, request.user)
        if data is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)

    @action(detail=True, methods=['post'], url_path='analyze')
    def analyze(self, request, pk=None):
        project = self.get_object()
        repos_data = project.repository_data or []
        
        if not repos_data:
            return Response({"detail": "No repositories configured for this project."}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.repositories.models import Repository
        from apps.analysis.models import AnalysisJob
        from django.utils import timezone
        import threading
        from services.repository_scanner import RepositoryScannerService
        
        jobs = []
        for r_data in repos_data:
            # Handle either direct url or fullName (github repo name)
            url = r_data.get('url') or r_data.get('fullName')
            if url and not url.startswith("http"):
                url = f"https://github.com/{url}.git"
            if not url:
                continue
                
            branch = r_data.get('branch') or 'main'
            provider = r_data.get('provider') or 'GitHub'
            
            repo, _ = Repository.objects.get_or_create(
                project=project,
                url=url,
                defaults={
                    "branch": branch,
                    "provider": provider,
                    "status": "ready"
                }
            )
            
            # Create AnalysisJob
            job = AnalysisJob.objects.create(
                project=project,
                repository=repo,
                job_type="scan",
                status="Pending"
            )
            jobs.append(job)
            
            scanner = RepositoryScannerService()
            def run_scan_thread(job_id, r_info):
                try:
                    scanner.scan_repository(job_id)
                    from services.repository_classifier import RepositoryClassificationService
                    classifier = RepositoryClassificationService()
                    classifier.classify_repository(job_id)
                    try:
                        proj = Project.objects.get(id=project.id)
                        data_list = proj.repository_data or []
                        for item in data_list:
                            if item.get('id') == r_info.get('id'):
                                item['status'] = 'done'
                                item['lastAnalyzed'] = timezone.now().isoformat()
                        proj.repository_data = data_list
                        proj.save()
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        proj = Project.objects.get(id=project.id)
                        data_list = proj.repository_data or []
                        for item in data_list:
                            if item.get('id') == r_info.get('id'):
                                item['status'] = 'failed'
                                item['error'] = str(e)
                        proj.repository_data = data_list
                        proj.save()
                    except Exception:
                        pass
            
            threading.Thread(target=run_scan_thread, args=(job.id, r_data)).start()
            
        return Response({
            "detail": "Analysis started.",
            "jobs": [{"id": str(j.id), "status": j.status} for j in jobs]
        })

    @action(detail=True, methods=['get'], url_path='analysis-jobs')
    def analysis_jobs(self, request, pk=None):
        project = self.get_object()
        from apps.analysis.models import AnalysisJob
        jobs = AnalysisJob.objects.filter(project=project).order_by('-started_at')
        return Response([
            {
                "id": str(job.id),
                "repository": job.repository.url if job.repository else None,
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "metadata": job.metadata
            }
            for job in jobs
        ])

    @action(detail=True, methods=['post'], url_path='reset-analysis')
    def reset_analysis(self, request, pk=None):
        project = self.get_object()
        
        from apps.knowledge.models import KnowledgeItem
        items_deleted, _ = KnowledgeItem.objects.filter(project=project).delete()
        
        from apps.analysis.models import AnalysisJob
        jobs_deleted, _ = AnalysisJob.objects.filter(project=project).delete()
        
        repos_data = project.repository_data or []
        for r in repos_data:
            r['status'] = 'ready'
            if 'lastAnalyzed' in r:
                del r['lastAnalyzed']
            if 'error' in r:
                del r['error']
        project.repository_data = repos_data
        project.save()
        
        from apps.repositories.models import Repository
        Repository.objects.filter(project=project).update(status='ready')
        
        return Response({
            "detail": "Analysis data reset successfully.",
            "deleted_items_count": items_deleted,
            "deleted_jobs_count": jobs_deleted
        })

