import os
from rest_framework import authentication
from rest_framework import exceptions
from supabase import create_client, Client
from apps.authentication.models import User

class SupabaseAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            return None

        supabase_url = f"https://{os.environ.get('PROJECT_ID')}.supabase.co"
        supabase_key = os.environ.get('ANON_PUBLIC')

        if not supabase_url or not supabase_key:
            raise exceptions.AuthenticationFailed('Supabase credentials not configured.')

        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            response = supabase.auth.get_user(token)
            if not response or not response.user:
                raise exceptions.AuthenticationFailed('Invalid token.')

            user_id = response.user.id
            
            try:
                user = User.objects.get(supabase_user_id=user_id)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User does not exist in backend.')

            return (user, token)
            
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
