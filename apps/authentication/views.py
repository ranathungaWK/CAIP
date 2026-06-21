from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User

class SyncUserView(APIView):
    def post(self, request):
        supabase_user_id = request.data.get('supabase_user_id')
        email = request.data.get('email')
        full_name = request.data.get('full_name', '')

        if not supabase_user_id or not email:
            return Response(
                {"error": "supabase_user_id and email are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create or update user
        user, created = User.objects.update_or_create(
            supabase_user_id=supabase_user_id,
            defaults={
                'email': email,
                'full_name': full_name
            }
        )

        return Response({
            "message": "User synced successfully",
            "user_id": str(user.id),
            "created": created
        }, status=status.HTTP_200_OK)


