import datetime
import uuid
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.accounts.models.user import User
from apps.consultations.models.appointment_request import AppointmentRequest
from apps.consultations.services.booking_service import BookingService
from apps.accounts.services.email_service import EmailService

class PublicDoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    accepts_appointments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'profile_image', 'qualification', 
            'specialization', 'experience', 'accepts_appointments'
        ]

    def get_full_name(self, obj) -> str:
        first = obj.first_name or ""
        last = obj.last_name or ""
        return f"{first} {last}".strip()

    def get_profile_image(self, obj) -> str:
        if not obj.profile_image:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url

    def get_accepts_appointments(self, obj) -> bool:
        avail = getattr(obj, 'active_availability', None)
        if avail and len(avail) > 0:
            return avail[0].accepts_appointments
        # Fallback if not prefetched
        from apps.consultations.models.doctor_availability import DoctorAvailability
        avail_record = DoctorAvailability.objects.filter(doctor=obj, is_active=True).first()
        return avail_record.accepts_appointments if avail_record else False


class AppointmentRequestPublicCreateSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = AppointmentRequest
        fields = [
            "doctor_id",
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

    def validate(self, attrs):
        # Validate using BookingService
        try:
            BookingService.validate_booking(attrs)
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF ValidationError
            if hasattr(e, 'message_dict'):
                raise serializers.ValidationError(e.message_dict)
            else:
                raise serializers.ValidationError({"non_field_errors": e.messages})
        return attrs

    def create(self, validated_data):
        doctor_id = validated_data.pop("doctor_id")
        
        # Fetch doctor to append preference to notes
        doctor = User.objects.filter(id=doctor_id).first()
        if doctor:
            doctor_name = f"{doctor.first_name or ''} {doctor.last_name or ''}".strip()
        else:
            doctor_name = "Unknown Clinician"
        
        pref_note = f"[Preferred Doctor: {doctor_name}]"
        existing_notes = validated_data.get("additional_notes", "")
        if existing_notes:
            validated_data["additional_notes"] = f"{pref_note} {existing_notes}"
        else:
            validated_data["additional_notes"] = pref_note

        # Generate request number inside atomic transaction
        with transaction.atomic():
            today_str = datetime.date.today().strftime("%Y%m%d")
            unique_suffix = uuid.uuid4().hex[:4].upper()
            request_number = f"REQ-{today_str}-{unique_suffix}"
            
            appointment_request = AppointmentRequest.objects.create(
                request_number=request_number,
                status="PENDING",
                booking_source="WEBSITE",
                **validated_data
            )

        # Trigger confirmation email asynchronously/safely
        try:
            parent_name = f"{appointment_request.parent_first_name} {appointment_request.parent_last_name}"
            EmailService.send_appointment_request_confirmation(
                email=appointment_request.email,
                parent_name=parent_name,
                request_number=appointment_request.request_number
            )
        except Exception:
            pass

        return appointment_request
