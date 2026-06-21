from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import redirect
import os
import time
import jwt
import requests
from .models import GithubInstallation

class GithubInstallCallbackView(APIView):
    """
    Handles the redirect from GitHub after a user installs the GitHub App.
    """
    # Note: Depending on your auth setup, the redirect might not include the auth token.
    # For now, we will allow any to handle the redirect, but in production,
    # you might need to extract state or match the user session.
    permission_classes = [] 

    def get(self, request):
        installation_id = request.query_params.get('installation_id')
        setup_action = request.query_params.get('setup_action')
        
        if not installation_id:
            return Response({"error": "installation_id is missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        # If user is authenticated, save it properly. Otherwise, you might need a different flow.
        # For this prototype, we'll just save it to the first user or skip if no user.
        # Ideally, we should redirect to the frontend with the installation_id so the frontend
        # can send it back with the user's auth token.
        
        frontend_url = "http://localhost:5173" # Update if running on 3000
        return redirect(f"{frontend_url}/projects?github_installed=true&installation_id={installation_id}")


def get_github_app_jwt():
    app_id = os.getenv('GITHUB_APP_ID')
    private_key = os.getenv('GITHUB_PRIVATE_KEY')
    
    if private_key and "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")

    now = int(time.time())
    payload = {
        'iat': now - 60,
        'exp': now + (10 * 60),
        'iss': app_id
    }
    
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    return encoded_jwt

def get_installation_access_token(installation_id):
    encoded_jwt = get_github_app_jwt()
    headers = {
        'Authorization': f'Bearer {encoded_jwt}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    response = requests.post(url, headers=headers)
    if response.status_code == 201:
        return response.json()['token']
    return None

class GithubRepositoriesView(APIView):
    """
    Fetches repositories accessible by the given installation.
    """
    permission_classes = [] # we allow any for now for prototyping without auth flow setup

    def get(self, request):
        installation_id = request.query_params.get('installation_id')
        if not installation_id:
            return Response({"error": "installation_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        access_token = get_installation_access_token(installation_id)
        if not access_token:
            return Response({"error": "Failed to authenticate with GitHub App"}, status=status.HTTP_401_UNAUTHORIZED)
            
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = 'https://api.github.com/installation/repositories?per_page=100'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return Response({"error": "Failed to fetch repositories"}, status=response.status_code)
            
        data = response.json()
        print("GITHUB API REPOS RESPONSE:", data)
        repos = data.get('repositories', [])
        
        # Format the response to match the frontend expectations
        formatted_repos = []
        for repo in repos:
            formatted_repos.append({
                "id": repo['id'],
                "name": repo['name'],
                "fullName": repo['full_name'],
                "language": repo.get('language') or "Unknown",
                "private": repo.get('private', False),
                "defaultBranch": repo['default_branch'],
                "updatedAt": repo.get('updated_at', '')
            })
            
        return Response(formatted_repos, status=status.HTTP_200_OK)

class GithubBranchesView(APIView):
    def get(self, request):
        installation_id = request.query_params.get('installation_id')
        repo = request.query_params.get('repo')
        
        if not installation_id or not repo:
            return Response({"error": "installation_id and repo are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        access_token = get_installation_access_token(installation_id)
        if not access_token:
            return Response({"error": "Failed to authenticate with GitHub App"}, status=status.HTTP_401_UNAUTHORIZED)
            
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f'https://api.github.com/repos/{repo}/branches?per_page=100'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return Response({"error": f"Failed to fetch branches: {response.text}"}, status=response.status_code)
            
        branches_data = response.json()
        branches = [b['name'] for b in branches_data]
        
        return Response(branches, status=status.HTTP_200_OK)
