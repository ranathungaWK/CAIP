import os
import shutil
import tempfile
import uuid
from unittest import mock
from django.test import TestCase
from django.utils import timezone

from apps.authentication.models import User
from apps.projects.models import Project
from apps.repositories.models import Repository
from apps.analysis.models import AnalysisJob
from apps.knowledge.models import KnowledgeItem, KnowledgeRelationship, KnowledgeItemType, DiscoverySource
from services.repository_scanner import RepositoryScannerService
from services.repository_classifier import RepositoryClassificationService

class RepositoryScannerTestCase(TestCase):
    def setUp(self):
        # Create a test user, project, repository, and job
        self.user = User.objects.create(
            supabase_user_id="e2bdf27b-e1c5-430b-ad6e-b6b88b209a32",
            email="test@example.com",
            full_name="Test User"
        )
        self.project = Project.objects.create(
            name="Test Project",
            owner=self.user
        )
        self.repository = Repository.objects.create(
            project=self.project,
            url="https://github.com/test/repo.git",
            branch="main",
            provider="GitHub"
        )
        self.job = AnalysisJob.objects.create(
            project=self.project,
            repository=self.repository,
            job_type="scan",
            status="Pending"
        )
        self.service = RepositoryScannerService()

    @mock.patch("git.Repo.clone_from")
    def test_successful_scan(self, mock_clone):
        def side_effect_clone(url, path, **kwargs):
            # Create a mock file system structure inside the temp path
            os.makedirs(os.path.join(path, ".git"), exist_ok=True)
            os.makedirs(os.path.join(path, "node_modules"), exist_ok=True)
            os.makedirs(os.path.join(path, "backend", "auth"), exist_ok=True)
            
            with open(os.path.join(path, "README.md"), "w") as f:
                f.write("Hello World")
            with open(os.path.join(path, "backend", "main.py"), "w") as f:
                f.write("import os")
            with open(os.path.join(path, "backend", "auth", "service.py"), "w") as f:
                f.write("class AuthService:")
            with open(os.path.join(path, "node_modules", "package.json"), "w") as f:
                f.write("{}")

        mock_clone.side_effect = side_effect_clone

        # Run the scanner
        # Capture cleanup_workspace to verify it gets called
        with mock.patch.object(self.service, "cleanup_workspace", wraps=self.service.cleanup_workspace) as mock_cleanup:
            result = self.service.scan_repository(self.job.id)
            
            # Verify cleanup was called on the temp path
            mock_cleanup.assert_called_once()
            called_path = mock_cleanup.call_args[0][0]
            # The temp path should no longer exist
            self.assertFalse(called_path.exists())

        # Fetch job and assert completions
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "Completed")
        self.assertIsNotNone(self.job.started_at)
        self.assertIsNotNone(self.job.completed_at)
        self.assertIsNone(self.job.error_message)
        
        # Check metadata/statistics
        self.assertEqual(self.job.metadata["directories"], 2)  # backend, backend/auth
        self.assertEqual(self.job.metadata["files"], 3)        # README.md, backend/main.py, backend/auth/service.py
        
        # Verify created nodes in DB
        items = KnowledgeItem.objects.filter(analysis_job=self.job)
        # 1 REPOSITORY + 2 DIRECTORY + 3 FILE = 6 items
        self.assertEqual(items.count(), 6)
        
        repo_nodes = items.filter(item_type=KnowledgeItemType.REPOSITORY)
        self.assertEqual(repo_nodes.count(), 1)
        repo_node = repo_nodes.first()
        self.assertEqual(repo_node.value, "repo")
        self.assertEqual(repo_node.metadata["url"], self.repository.url)
        self.assertEqual(repo_node.discovered_by, DiscoverySource.REPOSITORY_SCANNER)
        
        dir_nodes = items.filter(item_type=KnowledgeItemType.DIRECTORY)
        self.assertEqual(dir_nodes.count(), 2)
        dir_paths = [d.value for d in dir_nodes]
        self.assertIn("backend", dir_paths)
        self.assertIn("backend/auth", dir_paths)
        
        file_nodes = items.filter(item_type=KnowledgeItemType.FILE)
        self.assertEqual(file_nodes.count(), 3)
        file_paths = [f.value for f in file_nodes]
        self.assertIn("README.md", file_paths)
        self.assertIn("backend/main.py", file_paths)
        self.assertIn("backend/auth/service.py", file_paths)
        
        # Verify exclusions
        self.assertNotIn("node_modules", dir_paths)
        self.assertNotIn(".git", dir_paths)
        
        # Verify relationships
        rels = KnowledgeRelationship.objects.filter(analysis_job=self.job)
        self.assertEqual(rels.count(), 5) # repo->README.md, repo->backend, backend->main.py, backend->auth, auth->service.py
        for r in rels:
            self.assertEqual(r.relationship_type, "CONTAINS")
            self.assertEqual(r.discovered_by, DiscoverySource.REPOSITORY_SCANNER)

    @mock.patch("git.Repo.clone_from")
    def test_clone_failure(self, mock_clone):
        # Simulate a clone error
        mock_clone.side_effect = Exception("Auth failure / Network unreachable")
        
        # Capture cleanup_workspace to verify it gets called even on exception
        with mock.patch.object(self.service, "cleanup_workspace", wraps=self.service.cleanup_workspace) as mock_cleanup:
            with self.assertRaises(Exception):
                self.service.scan_repository(self.job.id)
            
            # Verify cleanup was called
            mock_cleanup.assert_called_once()
            
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "Failed")
        self.assertIn("Auth failure / Network unreachable", self.job.error_message)
        self.assertIsNotNone(self.job.completed_at)
        
        # Verify no items or relationships are saved
        self.assertEqual(KnowledgeItem.objects.filter(analysis_job=self.job).count(), 0)
        self.assertEqual(KnowledgeRelationship.objects.filter(analysis_job=self.job).count(), 0)

    def test_job_not_found(self):
        fake_id = uuid.uuid4()
        with self.assertRaises(ValueError):
            self.service.scan_repository(fake_id)

class RepositoryClassifierTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            supabase_user_id="e2bdf27b-e1c5-430b-ad6e-b6b88b209a32",
            email="test-classifier@example.com",
            full_name="Classifier Test User"
        )
        self.project = Project.objects.create(
            name="Classifier Test Project",
            owner=self.user
        )
        self.repository = Repository.objects.create(
            project=self.project,
            url="https://github.com/test/classifier-repo.git",
            branch="main",
            provider="GitHub"
        )
        self.job = AnalysisJob.objects.create(
            project=self.project,
            repository=self.repository,
            job_type="scan",
            status="Running"
        )
        self.classifier_service = RepositoryClassificationService()

    def test_classification_and_enrichment(self):
        from services.repository_classifier import RepositoryClassificationService
        
        # Create different file/directory types in DB
        items_data = [
            (KnowledgeItemType.FILE, "README.md", {"file_name": "README.md", "extension": ".md", "size": 150}),
            (KnowledgeItemType.FILE, "package.json", {"file_name": "package.json"}),
            (KnowledgeItemType.FILE, "backend/settings.py", {"file_name": "settings.py"}),
            (KnowledgeItemType.FILE, "Dockerfile", {"file_name": "Dockerfile"}),
            (KnowledgeItemType.FILE, "backend/auth/service.py", {"file_name": "service.py", "extension": ".py"}),
            (KnowledgeItemType.FILE, "tests/test_service.py", {"file_name": "test_service.py"}),
            (KnowledgeItemType.FILE, "assets/logo.png", {"file_name": "logo.png", "extension": ".png"}),
            (KnowledgeItemType.FILE, ".github/workflows/deploy.yml", {"file_name": "deploy.yml"}),
            (KnowledgeItemType.DIRECTORY, "docs", {}),
            (KnowledgeItemType.DIRECTORY, "src", {}),
            
            # New Step 02 categories
            (KnowledgeItemType.FILE, "backend/main.py", {"file_name": "main.py"}),
            (KnowledgeItemType.FILE, "frontend/index.tsx", {"file_name": "index.tsx", "extension": ".tsx"}),
            (KnowledgeItemType.FILE, "docs/openapi.yaml", {"file_name": "openapi.yaml"}),
            (KnowledgeItemType.FILE, "backend/migrations/0001_initial.py", {"file_name": "0001_initial.py"}),
            (KnowledgeItemType.FILE, "Makefile", {"file_name": "Makefile"}),
            (KnowledgeItemType.FILE, "generated/demo_pb2.py", {"file_name": "demo_pb2.py"}),
            (KnowledgeItemType.FILE, "node_modules/lodash/index.js", {"file_name": "index.js"}),
            (KnowledgeItemType.FILE, ".env.example", {"file_name": ".env.example"}),
        ]
        
        db_items = []
        for itype, val, meta in items_data:
            db_items.append(
                KnowledgeItem(
                    project=self.project,
                    repository=self.repository,
                    analysis_job=self.job,
                    item_type=itype,
                    value=val,
                    metadata=meta,
                    discovered_by=DiscoverySource.REPOSITORY_SCANNER
                )
            )
        KnowledgeItem.objects.bulk_create(db_items)
        
        # Run classification
        stats = self.classifier_service.classify_repository(self.job.id)
        
        # Verify stats return
        self.assertEqual(stats["source_code_files"], 1) # backend/auth/service.py
        self.assertEqual(stats["test_files"], 1) # tests/test_service.py
        self.assertEqual(stats["documentation_files"], 1) # README.md
        self.assertEqual(stats["dependency_manifests"], 1) # package.json
        self.assertEqual(stats["static_assets"], 1) # assets/logo.png
        self.assertEqual(stats["configuration_files"], 1) # backend/settings.py
        self.assertEqual(stats["infrastructure_files"], 1) # Dockerfile
        self.assertEqual(stats["ci_cd_files"], 1) # .github/workflows/deploy.yml
        self.assertEqual(stats["application_entrypoints"], 2) # backend/main.py, frontend/index.tsx
        self.assertEqual(stats["api_definitions"], 1) # docs/openapi.yaml
        self.assertEqual(stats["database_migrations"], 1) # backend/migrations/0001_initial.py
        self.assertEqual(stats["build_systems"], 1) # Makefile
        self.assertEqual(stats["generated_code_files"], 1) # generated/demo_pb2.py
        self.assertEqual(stats["third_party_code_files"], 1) # node_modules/lodash/index.js
        self.assertEqual(stats["secrets_templates"], 1) # .env.example

        # Reload job and verify metadata stats
        self.job.refresh_from_db()
        self.assertEqual(self.job.metadata["classification"], stats)
        
        # Verify enriched items in database
        readme = KnowledgeItem.objects.get(analysis_job=self.job, value="README.md")
        self.assertEqual(readme.metadata["category"], "DOCUMENTATION")
        self.assertEqual(readme.metadata["extension"], ".md")
        self.assertEqual(readme.metadata["size"], 150)
        self.assertEqual(readme.discovered_by, DiscoverySource.REPOSITORY_CLASSIFIER)
        
        package_json = KnowledgeItem.objects.get(analysis_job=self.job, value="package.json")
        self.assertEqual(package_json.metadata["category"], "DEPENDENCY_MANIFEST")
        
        settings_py = KnowledgeItem.objects.get(analysis_job=self.job, value="backend/settings.py")
        self.assertEqual(settings_py.metadata["category"], "CONFIGURATION")
        
        dockerfile = KnowledgeItem.objects.get(analysis_job=self.job, value="Dockerfile")
        self.assertEqual(dockerfile.metadata["category"], "INFRASTRUCTURE")
        self.assertEqual(dockerfile.metadata["infra_type"], "dockerfile")
        
        service_py = KnowledgeItem.objects.get(analysis_job=self.job, value="backend/auth/service.py")
        self.assertEqual(service_py.metadata["category"], "SOURCE_CODE")
        self.assertEqual(service_py.metadata["language"], "python")
        self.assertEqual(service_py.metadata["language_family"], "python")
        self.assertEqual(service_py.metadata["is_test"], False)
        
        test_py = KnowledgeItem.objects.get(analysis_job=self.job, value="tests/test_service.py")
        self.assertEqual(test_py.metadata["category"], "TEST")
        self.assertEqual(test_py.metadata["is_test"], True)
        
        logo = KnowledgeItem.objects.get(analysis_job=self.job, value="assets/logo.png")
        self.assertEqual(logo.metadata["category"], "STATIC_ASSET")
        self.assertEqual(logo.metadata["asset_type"], "IMAGE")
        
        deploy_yml = KnowledgeItem.objects.get(analysis_job=self.job, value=".github/workflows/deploy.yml")
        self.assertEqual(deploy_yml.metadata["category"], "CI_CD")
        
        docs_dir = KnowledgeItem.objects.get(analysis_job=self.job, value="docs")
        self.assertEqual(docs_dir.metadata["category"], "DOCUMENTATION")
        
        # Verify new categories and language family logic
        main_py = KnowledgeItem.objects.get(analysis_job=self.job, value="backend/main.py")
        self.assertEqual(main_py.metadata["category"], "APPLICATION_ENTRYPOINT")
        self.assertEqual(main_py.metadata["language"], "python")
        self.assertEqual(main_py.metadata["language_family"], "python")
        self.assertEqual(main_py.metadata["is_test"], False)

        index_tsx = KnowledgeItem.objects.get(analysis_job=self.job, value="frontend/index.tsx")
        self.assertEqual(index_tsx.metadata["category"], "APPLICATION_ENTRYPOINT")
        self.assertEqual(index_tsx.metadata["language"], "typescript")
        self.assertEqual(index_tsx.metadata["language_family"], "javascript")
        self.assertEqual(index_tsx.metadata["is_test"], False)

        openapi = KnowledgeItem.objects.get(analysis_job=self.job, value="docs/openapi.yaml")
        self.assertEqual(openapi.metadata["category"], "API_DEFINITION")

        migration = KnowledgeItem.objects.get(analysis_job=self.job, value="backend/migrations/0001_initial.py")
        self.assertEqual(migration.metadata["category"], "DATABASE_MIGRATION")

        makefile = KnowledgeItem.objects.get(analysis_job=self.job, value="Makefile")
        self.assertEqual(makefile.metadata["category"], "BUILD_SYSTEM")

        gen_code = KnowledgeItem.objects.get(analysis_job=self.job, value="generated/demo_pb2.py")
        self.assertEqual(gen_code.metadata["category"], "GENERATED_CODE")

        third_party = KnowledgeItem.objects.get(analysis_job=self.job, value="node_modules/lodash/index.js")
        self.assertEqual(third_party.metadata["category"], "THIRD_PARTY_CODE")

        sec_temp = KnowledgeItem.objects.get(analysis_job=self.job, value=".env.example")
        self.assertEqual(sec_temp.metadata["category"], "SECRETS_TEMPLATE")

    def test_reset_analysis(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from apps.projects.views import ProjectViewSet
        
        repo = Repository.objects.create(
            project=self.project,
            url="https://github.com/test/to-reset.git",
            status="done"
        )
        job = AnalysisJob.objects.create(
            project=self.project,
            repository=repo,
            job_type="scan",
            status="Completed"
        )
        item = KnowledgeItem.objects.create(
            project=self.project,
            repository=repo,
            analysis_job=job,
            item_type=KnowledgeItemType.FILE,
            value="main.py"
        )
        rel = KnowledgeRelationship.objects.create(
            source_item=item,
            target_item=item,
            analysis_job=job,
            relationship_type="CONTAINS"
        )
        
        self.project.repository_data = [{"id": "r1", "url": repo.url, "status": "done", "lastAnalyzed": "some-date"}]
        self.project.save()
        
        factory = APIRequestFactory()
        request = factory.post(f"/api/projects/{self.project.id}/reset-analysis/")
        force_authenticate(request, user=self.user)
        
        view = ProjectViewSet.as_view({"post": "reset_analysis"})
        response = view(request, pk=str(self.project.id))
        
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(KnowledgeItem.objects.filter(project=self.project).count(), 0)
        self.assertEqual(KnowledgeRelationship.objects.filter(analysis_job=job).count(), 0)
        self.assertEqual(AnalysisJob.objects.filter(project=self.project).count(), 0)
        
        repo.refresh_from_db()
        self.assertEqual(repo.status, "ready")
        
        self.project.refresh_from_db()
        self.assertEqual(self.project.repository_data[0]["status"], "ready")
        self.assertNotIn("lastAnalyzed", self.project.repository_data[0])
