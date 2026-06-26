import re
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers

from apps.consultations.models import AppointmentRequest
from apps.consultations.choices import (
    Gender,
    RelationshipToChild,
    AppointmentType,
    PrimaryConcern,
)

class NormalizingChoiceField(serializers.ChoiceField):
    """
    ChoiceField that accepts display labels or keys, case-insensitively,
    and normalizes them to the corresponding choice key.
    """
    def to_internal_value(self, data):
        if not data:
            return super().to_internal_value(data)
        
        normalized_data = str(data).strip()
        for key, label in self.choices.items():
            if normalized_data.upper() == str(key).upper() or normalized_data.lower() == str(label).lower():
                return key
        
        return super().to_internal_value(data)

class PublicConsultationRequestSerializer(serializers.ModelSerializer):
    relationship_to_child = NormalizingChoiceField(choices=RelationshipToChild.choices)
    gender = NormalizingChoiceField(choices=Gender.choices)
    appointment_type = NormalizingChoiceField(choices=AppointmentType.choices)
    primary_concern = NormalizingChoiceField(choices=PrimaryConcern.choices)
    
    class Meta:
        model = AppointmentRequest
        fields = [
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'child_first_name',
            'child_last_name',
            'date_of_birth',
            'gender',
            'appointment_type',
            'primary_concern',
            'preferred_date',
            'preferred_time_slot',
            'additional_notes',
            'referral_source',
        ]
        extra_kwargs = {
            'parent_first_name': {'max_length': 100, 'required': True},
            'parent_last_name': {'required': True},
            'child_first_name': {'required': True},
            'child_last_name': {'required': True},
            'date_of_birth': {'required': True},
            'preferred_date': {'required': True},
            'preferred_time_slot': {'required': True},
            'additional_notes': {'max_length': 1000, 'required': False, 'allow_blank': True},
            'alternate_mobile_number': {'required': False, 'allow_blank': True, 'allow_null': True},
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
            'referral_source': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate_mobile_number(self, value):
        if not value:
            raise serializers.ValidationError("Mobile number is required.")
        cleaned_value = str(value).strip()
        pattern = re.compile(r'^(?:\+91|91|0)?[6-9]\d{9}$')
        if not pattern.match(cleaned_value):
            raise serializers.ValidationError("Enter a valid mobile number.")
        return cleaned_value

    def validate_alternate_mobile_number(self, value):
        if not value:
            return None
        cleaned_value = str(value).strip()
        pattern = re.compile(r'^(?:\+91|91|0)?[6-9]\d{9}$')
        if not pattern.match(cleaned_value):
            raise serializers.ValidationError("Enter a valid mobile number.")
        return cleaned_value

    def validate_date_of_birth(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Date of birth cannot be a future date.")
        return value

    def validate_preferred_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Preferred date cannot be in the past.")
        return value

    def to_internal_value(self, data):
        # Sanitize and trim string inputs to prevent HTML/Script injection
        sanitized_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Trim whitespace
                cleaned_val = value.strip()
                # Strip HTML tags
                cleaned_val = strip_tags(cleaned_val)
                sanitized_data[key] = cleaned_val
            else:
                sanitized_data[key] = value
                
        return super().to_internal_value(sanitized_data)

    def validate(self, attrs):
        primary_concern = attrs.get('primary_concern')
        additional_notes = attrs.get('additional_notes')
        
        if primary_concern == PrimaryConcern.OTHER:
            if not additional_notes or not additional_notes.strip():
                raise serializers.ValidationError({
                    "additional_notes": ["Additional notes are required when primary concern is 'Other'."]
                })
        return attrs
