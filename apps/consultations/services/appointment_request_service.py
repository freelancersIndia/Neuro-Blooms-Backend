import logging
import datetime
from django.db import models, transaction
from django.utils import timezone

from apps.consultations.models import AppointmentRequest
from apps.consultations.choices import AppointmentRequestStatus, BookingSource
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.services.email_service import EmailService

logger = logging.getLogger(__name__)

class DuplicateRequestException(Exception):
    """
    Raised when a duplicate pending appointment request is found.
    """
    pass

class ConflictException(Exception):
    """
    Raised when an action conflicts with the current state of a resource.
    """
    pass

def mask_email(email: str) -> str:
    if not email or '@' not in email:
        return "N/A"
    parts = email.split('@')
    name = parts[0]
    domain = parts[1]
    if len(name) <= 2:
        masked_name = "*" * len(name)
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"

def mask_mobile(mobile: str) -> str:
    if not mobile:
        return "N/A"
    cleaned = str(mobile).strip()
    if len(cleaned) <= 4:
        return "*" * len(cleaned)
    return "*" * (len(cleaned) - 4) + cleaned[-4:]

class AppointmentRequestService:
    @staticmethod
    def check_duplicate_request(mobile_number: str, child_first_name: str, child_last_name: str, preferred_date) -> bool:
        """
        Check if a pending request exists with same mobile number, child name, and preferred date.
        """
        return AppointmentRequest.objects.filter(
            status=AppointmentRequestStatus.PENDING,
            mobile_number=mobile_number,
            child_first_name__iexact=child_first_name,
            child_last_name__iexact=child_last_name,
            preferred_date=preferred_date
        ).exists()

    @staticmethod
    def generate_request_number(year: int) -> str:
        """
        Generates a unique request number sequentially in the format REQ-YYYY-XXXXXX.
        Must be called within an active transaction block.
        """
        prefix = f"REQ-{year}-"
        # Select for update to lock rows for the current year, preventing concurrent duplicate sequence generation
        last_request = AppointmentRequest.objects.select_for_update().filter(
            request_number__startswith=prefix
        ).order_by('-request_number').first()

        if last_request:
            try:
                # Extract sequence number from last segment
                last_seq = int(last_request.request_number.split('-')[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1

        return f"{prefix}{new_seq:06d}"

    @classmethod
    def create_public_request(cls, validated_data: dict, ip_address: str = None) -> AppointmentRequest:
        """
        Verifies duplicate constraints, generates a request number,
        saves the appointment request, creates an activity log entry,
        and triggers a confirmation email.
        """
        mobile_number = validated_data.get('mobile_number')
        child_first_name = validated_data.get('child_first_name')
        child_last_name = validated_data.get('child_last_name')
        preferred_date = validated_data.get('preferred_date')
        parent_email = validated_data.get('email')
        parent_first_name = validated_data.get('parent_first_name')
        parent_last_name = validated_data.get('parent_last_name')
        parent_name = f"{parent_first_name} {parent_last_name}"

        # 1. Duplicate Prevention check
        if cls.check_duplicate_request(mobile_number, child_first_name, child_last_name, preferred_date):
            masked_mob = mask_mobile(mobile_number)
            logger.warning(
                f"Duplicate request detected for child {child_first_name} {child_last_name} "
                f"on {preferred_date} with mobile {masked_mob}."
            )
            raise DuplicateRequestException(
                "A consultation request already exists for this child on the selected date."
            )

        # 2. Sequential Request Number generation & Database save inside transaction
        current_year = datetime.datetime.now().year
        with transaction.atomic():
            request_number = cls.generate_request_number(current_year)
            
            # Instantiate request model and assign auto-generated fields
            appointment_request = AppointmentRequest(
                request_number=request_number,
                booking_source=BookingSource.WEBSITE,
                status=AppointmentRequestStatus.PENDING,
                **validated_data
            )
            appointment_request.save()

        # Log successful request creation
        masked_mob = mask_mobile(mobile_number)
        masked_email_str = mask_email(parent_email) if parent_email else "N/A"
        logger.info(
            f"Successfully created appointment request {request_number} "
            f"for child {child_first_name} {child_last_name}. "
            f"Mobile: {masked_mob}, Email: {masked_email_str}"
        )

        # 3. Create Activity Log (Anonymous user action)
        try:
            ActivityLog.objects.create(
                user=None,
                action=ActivityType.CONSULTATION_REQUEST_CREATED,
                description=f"Public consultation request submitted. Request Number: {request_number}",
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Failed to log activity for appointment request {request_number}: {str(e)}", exc_info=True)

        # 4. Trigger Email Hook (Must not fail request if sending fails)
        if parent_email:
            try:
                EmailService.send_appointment_request_confirmation(
                    email=parent_email,
                    parent_name=parent_name,
                    request_number=request_number
                )
            except Exception as e:
                # Log the error but do not raise, keeping API response resilient
                logger.error(
                    f"Failed to send confirmation email for request {request_number} to {masked_email_str}: {str(e)}",
                    exc_info=True
                )

        return appointment_request

    @staticmethod
    def get_filtered_requests(params: dict):
        """
        Retrieves, filters, searches, and orders AppointmentRequest objects.
        """
        queryset = AppointmentRequest.objects.select_related('reviewed_by')
        
        # Searching
        search_term = params.get('search')
        if search_term:
            search_term = str(search_term).strip()
            queryset = queryset.filter(
                models.Q(request_number__icontains=search_term) |
                models.Q(parent_first_name__icontains=search_term) |
                models.Q(parent_last_name__icontains=search_term) |
                models.Q(child_first_name__icontains=search_term) |
                models.Q(child_last_name__icontains=search_term) |
                models.Q(mobile_number__icontains=search_term) |
                models.Q(email__icontains=search_term)
            )
            
        # Filtering
        status_val = params.get('status')
        if status_val:
            queryset = queryset.filter(status=status_val.strip())
            
        appt_type = params.get('appointment_type')
        if appt_type:
            queryset = queryset.filter(appointment_type=appt_type.strip())
            
        pref_date = params.get('preferred_date')
        if pref_date:
            queryset = queryset.filter(preferred_date=pref_date.strip())
            
        concern = params.get('primary_concern')
        if concern:
            queryset = queryset.filter(primary_concern=concern.strip())
            
        # Ordering
        ordering = params.get('ordering')
        allowed_ordering = [
            'created_at', '-created_at',
            'preferred_date', '-preferred_date',
            'parent_first_name', '-parent_first_name',
            'child_first_name', '-child_first_name'
        ]
        if ordering and ordering.strip() in allowed_ordering:
            queryset = queryset.order_by(ordering.strip())
        else:
            queryset = queryset.order_by('-created_at')
            
        return queryset

    @staticmethod
    def get_statistics() -> dict:
        """
        Calculates aggregate statistics for appointment requests.
        """
        from django.db.models import Count, Q
        
        stats = AppointmentRequest.objects.aggregate(
            total_requests=Count('id'),
            pending_review=Count('id', filter=Q(status=AppointmentRequestStatus.PENDING)),
            approved=Count('id', filter=Q(status=AppointmentRequestStatus.APPROVED)),
            rejected=Count('id', filter=Q(status=AppointmentRequestStatus.REJECTED))
        )
        return stats

    @classmethod
    def approve_request(cls, request_id: str, user, ip_address: str = None) -> AppointmentRequest:
        """
        Approves a PENDING appointment request.
        Raises ConflictException if request is already approved or rejected.
        """
        with transaction.atomic():
            try:
                appt_request = AppointmentRequest.objects.select_for_update().get(id=request_id)
            except AppointmentRequest.DoesNotExist:
                raise AppointmentRequest.DoesNotExist("Appointment request not found.")
                
            if appt_request.status == AppointmentRequestStatus.APPROVED:
                raise ConflictException("Appointment request already approved.")
            if appt_request.status == AppointmentRequestStatus.REJECTED:
                raise ConflictException("Appointment request already rejected.")
            if appt_request.status != AppointmentRequestStatus.PENDING:
                raise ConflictException("Only pending requests can be approved.")
                
            # Perform transition
            appt_request.status = AppointmentRequestStatus.APPROVED
            appt_request.reviewed_by = user
            appt_request.reviewed_at = timezone.now()
            appt_request.save()
            
            # Create Activity Log
            ActivityLog.objects.create(
                user=user,
                action='APPOINTMENT_REQUEST_APPROVED',
                description=f"Appointment request approved. Request Number: {appt_request.request_number}",
                ip_address=ip_address
            )
            
            # Log it (masked)
            masked_mob = mask_mobile(appt_request.mobile_number)
            masked_email_str = mask_email(appt_request.email) if appt_request.email else "N/A"
            logger.info(
                f"Appointment request {appt_request.request_number} approved by {user.email}. "
                f"Child: {appt_request.child_first_name} {appt_request.child_last_name}, "
                f"Mobile: {masked_mob}, Email: {masked_email_str}"
            )
            
            # Trigger Approved Email Hook safely
            if appt_request.email:
                try:
                    parent_name = f"{appt_request.parent_first_name} {appt_request.parent_last_name}"
                    EmailService.send_appointment_request_approved(
                        email=appt_request.email,
                        parent_name=parent_name,
                        request_number=appt_request.request_number
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send approval email for request {appt_request.request_number}: {str(e)}",
                        exc_info=True
                    )
                    
            # Placeholder for WhatsApp service call (Do NOT implement WhatsApp)
            logger.info(f"[WhatsApp Placeholder] Notification triggered for approved request {appt_request.request_number}")
            
            return appt_request

    @classmethod
    def reject_request(cls, request_id: str, reason: str, user, ip_address: str = None) -> AppointmentRequest:
        """
        Rejects a PENDING appointment request.
        Raises ConflictException if request is already approved or rejected.
        """
        with transaction.atomic():
            try:
                appt_request = AppointmentRequest.objects.select_for_update().get(id=request_id)
            except AppointmentRequest.DoesNotExist:
                raise AppointmentRequest.DoesNotExist("Appointment request not found.")
                
            if appt_request.status == AppointmentRequestStatus.APPROVED:
                raise ConflictException("Appointment request already approved.")
            if appt_request.status == AppointmentRequestStatus.REJECTED:
                raise ConflictException("Appointment request already rejected.")
            if appt_request.status != AppointmentRequestStatus.PENDING:
                raise ConflictException("Only pending requests can be rejected.")
                
            # Perform transition
            appt_request.status = AppointmentRequestStatus.REJECTED
            appt_request.rejection_reason = reason
            appt_request.reviewed_by = user
            appt_request.reviewed_at = timezone.now()
            appt_request.save()
            
            # Create Activity Log
            ActivityLog.objects.create(
                user=user,
                action='APPOINTMENT_REQUEST_REJECTED',
                description=f"Appointment request rejected. Reason: {reason}. Request Number: {appt_request.request_number}",
                ip_address=ip_address
            )
            
            # Log it (masked)
            masked_mob = mask_mobile(appt_request.mobile_number)
            masked_email_str = mask_email(appt_request.email) if appt_request.email else "N/A"
            logger.info(
                f"Appointment request {appt_request.request_number} rejected by {user.email} for reason: {reason}. "
                f"Child: {appt_request.child_first_name} {appt_request.child_last_name}, "
                f"Mobile: {masked_mob}, Email: {masked_email_str}"
            )
            
            # Trigger Rejection Email Hook safely (Placeholder only)
            logger.info(f"[Email Placeholder] Rejection email triggered for request {appt_request.request_number} to {masked_email_str}")
            
            return appt_request

    @staticmethod
    def get_timeline(request_id: str) -> list:
        """
        Generates request lifecycle timeline events from ActivityLog entries.
        """
        try:
            appt_request = AppointmentRequest.objects.get(id=request_id)
        except AppointmentRequest.DoesNotExist:
            raise AppointmentRequest.DoesNotExist("Appointment request not found.")
            
        req_num = appt_request.request_number
        
        # Search activity logs containing the request number in their description
        logs = ActivityLog.objects.filter(description__icontains=req_num).order_by('created_at')
        
        timeline = []
        for log in logs:
            if log.action == ActivityType.CONSULTATION_REQUEST_CREATED:
                event = "Submitted"
                performed_by = "Website"
            elif log.action == 'APPOINTMENT_REQUEST_VIEWED':
                event = "Viewed"
                performed_by = log.user.email if log.user else "Anonymous Admin"
            elif log.action == 'APPOINTMENT_REQUEST_APPROVED':
                event = "Approved"
                performed_by = log.user.email if log.user else "Anonymous Admin"
            elif log.action == 'APPOINTMENT_REQUEST_REJECTED':
                event = "Rejected"
                performed_by = log.user.email if log.user else "Anonymous Admin"
            else:
                event = log.action.replace('_', ' ').title()
                performed_by = log.user.email if log.user else "System"
                
            timeline.append({
                "event": event,
                "performed_by": performed_by,
                "performed_at": log.created_at.isoformat()
            })
        return timeline
