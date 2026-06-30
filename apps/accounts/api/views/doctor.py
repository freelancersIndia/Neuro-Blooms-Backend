from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.accounts.models.user import User
from apps.accounts.api.serializers.doctor import DoctorListSerializer, DoctorDetailSerializer
from apps.accounts.utils.responses import success_response

class DoctorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Filter users who have the role 'DOCTOR' and are active
        doctors = User.objects.filter(user_roles__role__name='DOCTOR', is_active=True).distinct().order_by('first_name', 'last_name')
        serializer = DoctorListSerializer(doctors, many=True, context={'request': request})
        return success_response(
            message="Doctors retrieved successfully.",
            data=serializer.data
        )

class DoctorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        # Get the doctor user
        doctor = get_object_or_404(User, id=id, user_roles__role__name='DOCTOR')
        serializer = DoctorDetailSerializer(doctor, context={'request': request})
        return success_response(
            message="Doctor details retrieved successfully.",
            data=serializer.data
        )
