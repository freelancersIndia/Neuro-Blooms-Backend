from django.contrib import admin
from apps.consultations.models import (
    AppointmentRequest,
    Patient,
    Appointment,
    Consultation,
    AppointmentSlot,
    AppointmentSettings,
    DoctorAvailability,
    AppointmentStatusHistory,
    AppointmentNote,
    AppointmentAttachment,
)

@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = (
        'request_number',
        'parent_first_name',
        'parent_last_name',
        'mobile_number',
        'child_first_name',
        'child_last_name',
        'preferred_date',
        'status',
        'created_at',
    )
    list_filter = ('status', 'booking_source', 'appointment_type', 'preferred_date', 'created_at')
    search_fields = (
        'request_number',
        'parent_first_name',
        'parent_last_name',
        'mobile_number',
        'child_first_name',
        'child_last_name',
        'email',
    )
    readonly_fields = ('request_number', 'booking_source', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Request Metadata', {'fields': ('request_number', 'booking_source', 'status', 'created_at', 'updated_at')}),
        ('Parent Info', {'fields': ('parent_first_name', 'parent_last_name', 'relationship_to_child', 'mobile_number', 'alternate_mobile_number', 'email')}),
        ('Child Info', {'fields': ('child_first_name', 'child_last_name', 'date_of_birth', 'gender')}),
        ('Appointment Details', {'fields': ('appointment_type', 'primary_concern', 'preferred_date', 'preferred_time_slot', 'additional_notes', 'referral_source')}),
        ('Review Info', {'fields': ('rejection_reason', 'reviewed_by', 'reviewed_at')}),
    )

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_number', 'child_first_name', 'child_last_name', 'parent_first_name', 'mobile_number', 'patient_status', 'created_at')
    list_filter = ('patient_status', 'gender', 'created_at')
    search_fields = ('patient_number', 'child_first_name', 'child_last_name', 'parent_first_name', 'parent_last_name', 'mobile_number')
    readonly_fields = ('patient_number', 'created_at', 'updated_at')
    ordering = ('child_last_name', 'child_first_name')
    fieldsets = (
        ('Patient Metadata', {'fields': ('patient_number', 'patient_status', 'created_at', 'updated_at')}),
        ('Parent Info', {'fields': ('parent_first_name', 'parent_last_name', 'relationship_to_child', 'mobile_number', 'alternate_mobile_number', 'email')}),
        ('Child Info', {'fields': ('child_first_name', 'child_last_name', 'date_of_birth', 'gender')}),
        ('Address Info', {'fields': ('address',)}),
    )

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_number', 'patient', 'appointment_type', 'status', 'appointment_date', 'start_time', 'created_at')
    list_filter = ('status', 'appointment_type', 'booking_source', 'appointment_date', 'created_at')
    search_fields = (
        'appointment_number',
        'patient__child_first_name',
        'patient__child_last_name',
        'patient__patient_number',
        'reason_for_visit',
    )
    readonly_fields = ('appointment_number', 'created_at', 'updated_at')
    ordering = ('-appointment_date', '-start_time')
    fieldsets = (
        ('Appointment Metadata', {'fields': ('appointment_number', 'booking_source', 'status', 'created_at', 'updated_at')}),
        ('Patient & Request', {'fields': ('patient', 'appointment_request', 'parent_appointment')}),
        ('Schedule Details', {'fields': ('appointment_type', 'appointment_date', 'start_time', 'end_time')}),
        ('Consultation Context', {'fields': ('reason_for_visit',)}),
        ('Attribution', {'fields': ('approved_by', 'created_by')}),
    )

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'doctor', 'next_review_date', 'followup_required', 'created_at')
    list_filter = ('followup_required', 'next_review_date', 'created_at')
    search_fields = (
        'appointment__appointment_number',
        'doctor__email',
        'doctor__first_name',
        'doctor__last_name',
        'consultation_summary',
        'clinical_observation',
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'slot_date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'slot_date')
    search_fields = ('doctor__email', 'doctor__first_name', 'doctor__last_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('slot_date', 'start_time')

@admin.register(AppointmentSettings)
class AppointmentSettingsAdmin(admin.ModelAdmin):
    list_display = ('slot_duration', 'clinic_start_time', 'clinic_end_time', 'max_bookings_per_slot', 'created_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'weekday', 'start_time', 'end_time', 'is_available')
    list_filter = ('weekday', 'is_available')
    search_fields = ('doctor__email', 'doctor__first_name', 'doctor__last_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('weekday', 'start_time')

@admin.register(AppointmentStatusHistory)
class AppointmentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'previous_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('appointment__appointment_number', 'changed_by__email', 'reason')
    readonly_fields = ('appointment', 'previous_status', 'new_status', 'changed_by', 'reason', 'created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(AppointmentNote)
class AppointmentNoteAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'user', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('appointment__appointment_number', 'user__email', 'note')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(AppointmentAttachment)
class AppointmentAttachmentAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'uploaded_by', 'file', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('appointment__appointment_number', 'uploaded_by__email', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
