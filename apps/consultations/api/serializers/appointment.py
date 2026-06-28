from rest_framework import serializers
from apps.consultations.models.appointment import Appointment
from apps.consultations.choices import AppointmentType, AppointmentStatus, BookingSource

class AvailableSlotsQuerySerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=True)
    appointment_date = serializers.DateField(required=True)
    appointment_type = serializers.ChoiceField(choices=AppointmentType.choices, required=False)

class SlotValidationSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=True)
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True, format="%H:%M")

class AppointmentBookingSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField(required=True)
    doctor_id = serializers.UUIDField(required=True)
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True, format="%H:%M")
    appointment_type = serializers.ChoiceField(choices=AppointmentType.choices, required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    booking_source_display = serializers.CharField(source="get_booking_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    appointment_type_display = serializers.CharField(source="get_appointment_type_display", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "appointment_number",
            "patient",
            "patient_name",
            "doctor",
            "doctor_name",
            "appointment_type",
            "appointment_type_display",
            "booking_source",
            "booking_source_display",
            "status",
            "status_display",
            "appointment_date",
            "start_time",
            "end_time",
            "duration_minutes",
            "visit_reason"
        ]

    def get_patient_name(self, obj) -> str:
        if obj.patient:
            return f"{obj.patient.child_first_name} {obj.patient.child_last_name}"
        return ""

    def get_doctor_name(self, obj) -> str:
        if obj.doctor:
            return f"{obj.doctor.first_name} {obj.doctor.last_name}".strip() or obj.doctor.email
        return ""
