import os
import uuid
from django.db import transaction
from apps.analysis.models import AnalysisJob
from apps.knowledge.models import KnowledgeItem, DiscoverySource, KnowledgeItemType

class RepositoryClassificationService:
    def classify_repository(self, analysis_job_id: uuid.UUID) -> dict:
        """
        Fetches all KnowledgeItem nodes created for this job and enriches them
        with categories, extensions, languages, etc., saving statistics on completion.
        """
        try:
            job = AnalysisJob.objects.get(id=analysis_job_id)
        except AnalysisJob.DoesNotExist as e:
            raise ValueError(f"AnalysisJob with id {analysis_job_id} does not exist.") from e

        # Query all items associated with this job
        items = list(KnowledgeItem.objects.filter(analysis_job=job))
        
        stats = {
            "source_code_files": 0,
            "test_files": 0,
            "documentation_files": 0,
            "dependency_manifests": 0,
            "static_assets": 0,
            "configuration_files": 0,
            "infrastructure_files": 0,
            "ci_cd_files": 0,
            "application_entrypoints": 0,
            "api_definitions": 0,
            "database_migrations": 0,
            "build_systems": 0,
            "generated_code_files": 0,
            "third_party_code_files": 0,
            "secrets_templates": 0
        }
        
        items_to_update = []
        
        for item in items:
            if item.item_type not in [KnowledgeItemType.DIRECTORY, KnowledgeItemType.FILE]:
                continue
                
            updates = self.classify_item(item.value, item.item_type)
            if updates:
                # Merge into existing metadata
                current_meta = item.metadata or {}
                merged_meta = {**current_meta, **updates}
                item.metadata = merged_meta
                
                # Update provenance and analysis_job reference
                item.discovered_by = DiscoverySource.REPOSITORY_CLASSIFIER
                item.analysis_job = job
                items_to_update.append(item)
                
                # Update statistics (files only)
                if item.item_type == KnowledgeItemType.FILE:
                    cat = updates.get("category")
                    if cat == "SOURCE_CODE":
                        stats["source_code_files"] += 1
                    elif cat == "TEST":
                        stats["test_files"] += 1
                    elif cat == "DOCUMENTATION":
                        stats["documentation_files"] += 1
                    elif cat == "DEPENDENCY_MANIFEST":
                        stats["dependency_manifests"] += 1
                    elif cat == "STATIC_ASSET":
                        stats["static_assets"] += 1
                    elif cat == "CONFIGURATION":
                        stats["configuration_files"] += 1
                    elif cat == "INFRASTRUCTURE":
                        stats["infrastructure_files"] += 1
                    elif cat == "CI_CD":
                        stats["ci_cd_files"] += 1
                    elif cat == "APPLICATION_ENTRYPOINT":
                        stats["application_entrypoints"] += 1
                    elif cat == "API_DEFINITION":
                        stats["api_definitions"] += 1
                    elif cat == "DATABASE_MIGRATION":
                        stats["database_migrations"] += 1
                    elif cat == "BUILD_SYSTEM":
                        stats["build_systems"] += 1
                    elif cat == "GENERATED_CODE":
                        stats["generated_code_files"] += 1
                    elif cat == "THIRD_PARTY_CODE":
                        stats["third_party_code_files"] += 1
                    elif cat == "SECRETS_TEMPLATE":
                        stats["secrets_templates"] += 1

        # Bulk save changes
        if items_to_update:
            with transaction.atomic():
                batch_size = 500
                for i in range(0, len(items_to_update), batch_size):
                    batch = items_to_update[i:i + batch_size]
                    KnowledgeItem.objects.bulk_update(
                        batch, 
                        fields=["metadata", "discovered_by", "analysis_job"]
                    )
                    
        # Update AnalysisJob metadata with classification results
        current_job_meta = job.metadata or {}
        current_job_meta["classification"] = stats
        job.metadata = current_job_meta
        job.save()
        
        return stats

    def classify_item(self, value: str, item_type: str) -> dict:
        """
        Evaluates a file path or directory name and returns a dictionary of metadata attributes.
        """
        path_lower = value.lower()
        parts = path_lower.split("/")
        filename = parts[-1]
        
        # Extract extension
        _, ext = os.path.splitext(filename)
        
        category = None
        extra_meta = {}

        if item_type == KnowledgeItemType.DIRECTORY:
            # Classify directory names
            if filename in ["docs", "documentation", "doc"]:
                category = "DOCUMENTATION"
            elif filename in ["tests", "__tests__", "test", "spec", "specs"]:
                category = "TEST"
            elif filename in ["terraform", "helm", "k8s", "kubernetes", "ansible", "docker"]:
                category = "INFRASTRUCTURE"
            elif filename in [".github", ".gitlab"]:
                category = "CI_CD"
            elif filename in ["migrations", "alembic", "flyway", "liquibase"]:
                category = "DATABASE_MIGRATION"
            elif filename in ["generated", "gen", "dist", "build", "out", "target"]:
                category = "GENERATED_CODE"
            elif filename in ["vendor", "node_modules", "bower_components", "third_party", "3rdparty"]:
                category = "THIRD_PARTY_CODE"
            elif filename in ["config", "configs", "configuration", "settings"]:
                category = "CONFIGURATION"
        else:
            # Classify files
            # 1. Third Party Code
            if any(p in parts for p in ["vendor", "node_modules", "bower_components", "third_party", "3rdparty"]):
                category = "THIRD_PARTY_CODE"

            # 2. Generated Code
            elif any(p in parts for p in ["generated", "gen", "dist", "build", "out", "target"]) or \
                 filename.endswith("_pb2.py") or filename.endswith("_pb2_grpc.py") or \
                 filename.endswith(".pb.go") or filename.endswith("_grpc.pb.go"):
                category = "GENERATED_CODE"

            # 3. Database Migration
            elif any(p in parts for p in ["migrations", "alembic", "flyway", "liquibase"]) or \
                 (ext == ".sql" and ("migration" in path_lower or (filename.startswith("v") and "__" in filename))):
                category = "DATABASE_MIGRATION"

            # 4. CI/CD
            elif ".github/workflows/" in path_lower or filename in [".gitlab-ci.yml", ".azure-pipelines.yml", "circle.yml"]:
                category = "CI_CD"
            
            # 5. Infrastructure
            elif filename in ["dockerfile", "docker-compose.yml", "docker-compose.yaml", "jenkinsfile", "vagrantfile"] or \
                 any(p in parts for p in ["terraform", "helm", "k8s", "kubernetes", "ansible"]):
                category = "INFRASTRUCTURE"
                if ext == ".tf" or ext == ".tfvars":
                    extra_meta["infra_type"] = "terraform"
                elif filename == "dockerfile":
                    extra_meta["infra_type"] = "dockerfile"
                elif filename.startswith("docker-compose"):
                    extra_meta["infra_type"] = "docker-compose"
                    
            # 6. Secrets Template
            elif filename in [
                ".env.example", ".env.template", ".env.sample", "config.example.json", 
                "settings.example.py"
            ] or (".env." in filename and filename.endswith(".example")):
                category = "SECRETS_TEMPLATE"

            # 7. Application Entrypoint
            elif filename in [
                "main.py", "app.py", "manage.py", "program.cs", "server.js", "index.js", 
                "main.go", "wsgi.py", "asgi.py", "index.tsx", "index.ts", "index.jsx",
                "main.ts", "main.tsx", "main.js"
            ]:
                category = "APPLICATION_ENTRYPOINT"

            # 8. API Definition
            elif filename in [
                "openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.yml", 
                "openapi.json", "swagger.json"
            ]:
                category = "API_DEFINITION"

            # 9. Build System
            elif filename in [
                "makefile", "gradlew", "gradlew.bat", "mvnw", "mvnw.cmd", 
                "webpack.config.js", "vite.config.ts", "vite.config.js", "webpack.config.ts", 
                "rollup.config.js", "gulpfile.js", "gruntfile.js"
            ] or filename in ["build.gradle", "settings.gradle"]:
                category = "BUILD_SYSTEM"

            # 10. Dependency Manifests
            elif filename in [
                "package.json", "requirements.txt", "pyproject.toml", "pom.xml", 
                "cargo.toml", "composer.json", "go.mod", "go.sum", "package-lock.json", 
                "yarn.lock", "pnpm-lock.yaml", "pipfile", "poetry.lock", "gemfile", "mix.exs"
            ]:
                category = "DEPENDENCY_MANIFEST"

            # 11. Documentation
            elif filename in ["readme.md", "readme", "readme.txt", "contributing.md", "changelog.md", "license", "license.md", "license.txt", "security.md", "code_of_conduct.md"] or \
                 "docs/" in path_lower or "documentation/" in path_lower:
                category = "DOCUMENTATION"

            # 12. Tests
            elif "tests/" in path_lower or "__tests__/" in path_lower or "test/" in path_lower or "spec/" in path_lower or \
                 filename.startswith("test_") or filename.endswith("_test") or \
                 ".test." in filename or ".spec." in filename:
                category = "TEST"

            # 13. Static Assets
            elif ext in [
                ".png", ".jpg", ".jpeg", ".svg", ".gif", ".ico", ".webp", 
                ".woff", ".woff2", ".ttf", ".eot", 
                ".mp3", ".mp4", ".wav", ".avi", ".mov",
                ".pdf", ".zip", ".tar", ".gz"
            ]:
                category = "STATIC_ASSET"
                if ext in [".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".ico"]:
                    extra_meta["asset_type"] = "IMAGE"
                elif ext in [".woff", ".woff2", ".ttf", ".eot"]:
                    extra_meta["asset_type"] = "FONT"
                elif ext in [".mp3", ".wav"]:
                    extra_meta["asset_type"] = "AUDIO"
                elif ext in [".mp4", ".avi", ".mov"]:
                    extra_meta["asset_type"] = "VIDEO"
                elif ext == ".pdf":
                    extra_meta["asset_type"] = "PDF"
                else:
                    extra_meta["asset_type"] = "ARCHIVE"

            # 13.5. Configuration
            elif filename in [
                "settings.py", "config.json", "config.yaml", "config.yml", 
                "appsettings.json", "application.properties", "application.yml", "application.yaml",
                "tsconfig.json", "jsconfig.json", ".editorconfig", ".prettierrc", ".eslintrc.js", ".eslintrc.json"
            ] or any(p in parts for p in ["config", "configs", "configuration", "settings"]) or \
                 (ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg", ".properties"] and ext not in [".py"]):
                category = "CONFIGURATION"

            # 14. Source Code
            elif ext in [
                ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", 
                ".go", ".rs", ".java", ".kt", ".kts", ".cs", 
                ".cpp", ".cc", ".cxx", ".h", ".hpp", ".c", 
                ".rb", ".php", ".sh", ".bash", ".zsh", ".swift", 
                ".scala", ".pl", ".pm", ".sql", ".html", ".htm", ".css", ".sass", ".scss"
            ]:
                category = "SOURCE_CODE"

        # If categorised as SOURCE_CODE, TEST or APPLICATION_ENTRYPOINT, extract language details
        if category in ["SOURCE_CODE", "TEST", "APPLICATION_ENTRYPOINT"]:
            extra_meta["is_test"] = (category == "TEST")
            
            # Map extension to language and language_family
            lang_details = {
                ".py": ("python", "python"),
                ".js": ("javascript", "javascript"),
                ".mjs": ("javascript", "javascript"),
                ".cjs": ("javascript", "javascript"),
                ".jsx": ("javascript", "javascript"),
                ".ts": ("typescript", "javascript"),
                ".tsx": ("typescript", "javascript"),
                ".go": ("go", "go"),
                ".rs": ("rust", "rust"),
                ".java": ("java", "jvm"),
                ".kt": ("kotlin", "jvm"),
                ".kts": ("kotlin", "jvm"),
                ".scala": ("scala", "jvm"),
                ".cs": ("csharp", "dotnet"),
                ".cpp": ("cpp", "c_cpp"),
                ".cc": ("cpp", "c_cpp"),
                ".cxx": ("cpp", "c_cpp"),
                ".hpp": ("cpp", "c_cpp"),
                ".h": ("c_header", "c_cpp"),
                ".c": ("c", "c_cpp"),
                ".rb": ("ruby", "ruby"),
                ".php": ("php", "php"),
                ".sh": ("shell", "shell"),
                ".bash": ("shell", "shell"),
                ".zsh": ("shell", "shell"),
                ".swift": ("swift", "swift"),
                ".pl": ("perl", "perl"),
                ".pm": ("perl", "perl"),
                ".sql": ("sql", "sql"),
                ".html": ("html", "html"),
                ".htm": ("html", "html"),
                ".css": ("css", "css"),
                ".scss": ("scss", "css"),
                ".sass": ("sass", "css")
            }
            if ext in lang_details:
                lang, family = lang_details[ext]
                extra_meta["language"] = lang
                extra_meta["language_family"] = family

        updates = {}
        if category:
            updates["category"] = category
        for k, v in extra_meta.items():
            updates[k] = v
            
        return updates
