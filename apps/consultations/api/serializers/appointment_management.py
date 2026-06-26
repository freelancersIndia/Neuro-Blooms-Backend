from rest_framework import serializers
from apps.consultations.models import AppointmentRequest

class AppointmentRequestListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and quick review of appointment requests.
    """
    relationship_to_child_display = serializers.CharField(source='get_relationship_to_child_display', read_only=True)
    appointment_type_display = serializers.CharField(source='get_appointment_type_display', read_only=True)
    primary_concern_display = serializers.CharField(source='get_primary_concern_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AppointmentRequest
        fields = [
            'id',
            'request_number',
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'relationship_to_child_display',
            'mobile_number',
            'child_first_name',
            'child_last_name',
            'preferred_date',
            'preferred_time_slot',
            'appointment_type',
            'appointment_type_display',
            'primary_concern',
            'primary_concern_display',
            'status',
            'status_display',
            'created_at',
        ]
        read_only_fields = fields


class AppointmentRequestDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying the complete details of an appointment request.
    """
    relationship_to_child_display = serializers.CharField(source='get_relationship_to_child_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    appointment_type_display = serializers.CharField(source='get_appointment_type_display', read_only=True)
    primary_concern_display = serializers.CharField(source='get_primary_concern_display', read_only=True)
    booking_source_display = serializers.CharField(source='get_booking_source_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = AppointmentRequest
        fields = [
            'id',
            'request_number',
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'relationship_to_child_display',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'child_first_name',
            'child_last_name',
            'date_of_birth',
            'gender',
            'gender_display',
            'appointment_type',
            'appointment_type_display',
            'primary_concern',
            'primary_concern_display',
            'preferred_date',
            'preferred_time_slot',
            'additional_notes',
            'referral_source',
            'booking_source',
            'booking_source_display',
            'status',
            'status_display',
            'rejection_reason',
            'reviewed_by_email',
            'reviewed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class AppointmentRequestRejectSerializer(serializers.Serializer):
    """
    Serializer to validate input for rejecting an appointment request.
    """
    reason = serializers.CharField(
        max_length=500,
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'Rejection reason is required.',
            'blank': 'Rejection reason cannot be blank.'
        }
    )

    def validate_reason(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Rejection reason cannot be blank.")
        return value.strip()


class AppointmentRequestTimelineSerializer(serializers.Serializer):
    """
    Serializer representing individual timeline events for a request.
    """
    event = serializers.CharField(read_only=True)
    performed_by = serializers.CharField(read_only=True)
    performed_at = serializers.CharField(read_only=True)
