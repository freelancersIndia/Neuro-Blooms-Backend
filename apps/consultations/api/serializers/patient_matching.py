from rest_framework import serializers
from apps.consultations.models.patient import Patient
from apps.consultations.choices import Gender, RelationshipToChild, PatientStatus

class PatientMatchingQuerySerializer(serializers.Serializer):
    request_id = serializers.UUIDField(required=True)

class PatientLinkSerializer(serializers.Serializer):
    request_id = serializers.UUIDField(required=True)
    patient_id = serializers.UUIDField(required=True)

class PatientCreateSerializer(serializers.Serializer):
    request_id = serializers.UUIDField(required=True)

class PatientSearchQuerySerializer(serializers.Serializer):
    search = serializers.CharField(
        required=True,
        min_length=2,
        max_length=100,
        error_messages={
            "min_length": "Search query must be at least 2 characters.",
            "max_length": "Search query cannot exceed 100 characters."
        }
    )

class PatientSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "patient_number",
            "parent_first_name",
            "parent_last_name",
            "relationship_to_child",
            "mobile_number",
            "alternate_mobile_number",
            "email",
            "child_first_name",
            "child_last_name",
            "date_of_birth",
            "gender",
            "address",
            "patient_status"
        ]
