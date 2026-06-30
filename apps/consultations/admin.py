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
    ClinicHoliday,
    DoctorLeave,
    ClinicSettings,
    ClinicWeeklySchedule,
    ClinicBreak,
    DoctorWorkingDay,
    DoctorBlockedSlot,
    AppointmentTimeline,
    PatientTimeline,
    ConsultationAttachment,
    ConsultationActivityLog,
    ConsultationAuditLog,
    TreatmentCase,
)

class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'child_first_name', 'child_last_name', 'date_of_birth', 'gender', 'parent_first_name', 'parent_last_name', 'mobile_number', 'preferred_date', 'preferred_time_slot', 'status')
    list_filter = ('status', 'gender', 'preferred_date')
    search_fields = ('request_number', 'child_first_name', 'child_last_name', 'parent_first_name', 'parent_last_name', 'mobile_number', 'email')

class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_number', 'child_first_name', 'child_last_name', 'date_of_birth', 'gender', 'parent_first_name', 'parent_last_name', 'mobile_number', 'patient_status')
    list_filter = ('patient_status', 'gender')
    search_fields = ('patient_number', 'child_first_name', 'child_last_name', 'parent_first_name', 'parent_last_name', 'mobile_number')

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_number', 'patient', 'doctor', 'appointment_type', 'status', 'appointment_date', 'start_time', 'end_time', 'priority')
    list_filter = ('status', 'appointment_type', 'priority', 'appointment_date', 'doctor')
    search_fields = ('appointment_number', 'patient__child_first_name', 'patient__child_last_name', 'doctor__email')

class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'chief_complaint', 'diagnosis', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('appointment__appointment_number', 'chief_complaint', 'diagnosis')

class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'slot_date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'slot_date', 'doctor')

class AppointmentSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'slot_duration', 'clinic_start_time', 'clinic_end_time', 'max_bookings_per_slot', 'buffer_minutes')

class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'accepts_appointments', 'consultation_duration_minutes', 'max_daily_patients')
    list_filter = ('accepts_appointments',)
    search_fields = ('doctor__email',)

class AppointmentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'previous_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status', 'created_at')

class AppointmentNoteAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'visibility', 'user', 'created_at')
    list_filter = ('visibility', 'created_at')

class AppointmentAttachmentAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'file', 'uploaded_by', 'created_at')

class ClinicHolidayAdmin(admin.ModelAdmin):
    list_display = ('holiday_name', 'holiday_date', 'description')
    list_filter = ('holiday_date',)

class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_date', 'end_date', 'reason')
    list_filter = ('start_date', 'doctor')

class ClinicSettingsAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'opening_time', 'closing_time', 'slot_duration_minutes', 'booking_window_days', 'allow_same_day_booking', 'max_daily_appointments')

class ClinicWeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'is_open', 'opening_time', 'closing_time')
    list_filter = ('is_open', 'weekday')

class ClinicBreakAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'break_name', 'start_time', 'end_time')
    list_filter = ('weekday',)

class DoctorWorkingDayAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'weekday', 'is_working', 'start_time', 'end_time')
    list_filter = ('is_working', 'weekday', 'doctor')

class DoctorBlockedSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'block_date', 'start_time', 'end_time', 'reason')
    list_filter = ('block_date', 'doctor')

class AppointmentTimelineAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'event', 'description', 'created_at')
    list_filter = ('event', 'created_at')

class PatientTimelineAdmin(admin.ModelAdmin):
    list_display = ('patient', 'event', 'description', 'created_at')
    list_filter = ('event', 'created_at')

class ConsultationAttachmentAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'original_name', 'file', 'file_size', 'uploaded_by', 'created_at')

class ConsultationActivityLogAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'consultation', 'action', 'created_at')
    list_filter = ('action', 'created_at')

class ConsultationAuditLogAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'field_name', 'old_value', 'new_value', 'modified_by', 'created_at')
    list_filter = ('field_name', 'created_at')

class TreatmentCaseAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'status', 'primary_diagnosis', 'start_date', 'end_date')
    list_filter = ('status', 'start_date', 'doctor')

# Register all models with their respective admin classes
admin.site.register(AppointmentRequest, AppointmentRequestAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(Appointment, AppointmentAdmin)
admin.site.register(Consultation, ConsultationAdmin)
admin.site.register(AppointmentSlot, AppointmentSlotAdmin)
admin.site.register(AppointmentSettings, AppointmentSettingsAdmin)
admin.site.register(DoctorAvailability, DoctorAvailabilityAdmin)
admin.site.register(AppointmentStatusHistory, AppointmentStatusHistoryAdmin)
admin.site.register(AppointmentNote, AppointmentNoteAdmin)
admin.site.register(AppointmentAttachment, AppointmentAttachmentAdmin)
admin.site.register(ClinicHoliday, ClinicHolidayAdmin)
admin.site.register(DoctorLeave, DoctorLeaveAdmin)
admin.site.register(ClinicSettings, ClinicSettingsAdmin)
admin.site.register(ClinicWeeklySchedule, ClinicWeeklyScheduleAdmin)
admin.site.register(ClinicBreak, ClinicBreakAdmin)
admin.site.register(DoctorWorkingDay, DoctorWorkingDayAdmin)
admin.site.register(DoctorBlockedSlot, DoctorBlockedSlotAdmin)
admin.site.register(AppointmentTimeline, AppointmentTimelineAdmin)
admin.site.register(PatientTimeline, PatientTimelineAdmin)
admin.site.register(ConsultationAttachment, ConsultationAttachmentAdmin)
admin.site.register(ConsultationActivityLog, ConsultationActivityLogAdmin)
admin.site.register(ConsultationAuditLog, ConsultationAuditLogAdmin)
admin.site.register(TreatmentCase, TreatmentCaseAdmin)
