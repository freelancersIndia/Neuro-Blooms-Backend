from rest_framework import serializers
from apps.consultations.models.appointment_request import AppointmentRequest
from apps.consultations.choices import RelationshipToChild, Gender, AppointmentType
import datetime

class AppointmentRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentRequest
        fields = [
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
            "appointment_type",
            "primary_concern",
            "preferred_date",
            "preferred_time_slot",
            "additional_notes",
            "referral_source",
        ]

    def validate_date_of_birth(self, value):
        if value > datetime.date.today():
            raise serializers.ValidationError("Child's date of birth cannot be in the future.")
        return value

    def validate_preferred_date(self, value):
        if value < datetime.date.today():
            raise serializers.ValidationError("Preferred appointment date cannot be in the past.")
        return value
