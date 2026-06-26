from .base import BaseModel
from .appointment_request import AppointmentRequest
from .patient import Patient
from .appointment import Appointment
from .consultation import Consultation
from .appointment_slot import AppointmentSlot
from .appointment_settings import AppointmentSettings
from .doctor_availability import DoctorAvailability
from .appointment_status_history import AppointmentStatusHistory
from .appointment_note import AppointmentNote
from .appointment_attachment import AppointmentAttachment

__all__ = [
    'BaseModel',
    'AppointmentRequest',
    'Patient',
    'Appointment',
    'Consultation',
    'AppointmentSlot',
    'AppointmentSettings',
    'DoctorAvailability',
    'AppointmentStatusHistory',
    'AppointmentNote',
    'AppointmentAttachment',
]
