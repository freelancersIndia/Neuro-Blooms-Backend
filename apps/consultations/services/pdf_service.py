import io
import datetime
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

class PDFGenerationService:
    @staticmethod
    def generate_request_summary(request_obj) -> bytes:
        """
        Generates a professional PDF summary of the given AppointmentRequest.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # Define custom styles to avoid style conflicts
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0F172A'), # Charcoal / Slate 900
            spaceAfter=15
        )
        
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True
        )
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#475569')
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0F172A')
        )
        
        story = []
        
        # 1. Header (Logo & Clinic Name)
        from apps.consultations.models.clinic_settings import ClinicSettings
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        clinic_name = clinic_settings.clinic_name if clinic_settings else "Neuro Blooms Clinic"
        
        logo_loaded = False
        if clinic_settings and clinic_settings.clinic_logo:
            try:
                # Get the absolute path to the image
                logo_path = clinic_settings.clinic_logo.path
                logo_img = Image(logo_path, width=1.5*inch, height=0.5*inch)
                logo_img.hAlign = 'LEFT'
                story.append(logo_img)
                logo_loaded = True
            except Exception:
                # Fallback to text if image fails to load
                pass
                
        if not logo_loaded:
            story.append(Paragraph(clinic_name, ParagraphStyle(
                'ClinicNameHeader',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2563EB') # Indigo/Blue
            )))
            
        story.append(Spacer(1, 10))
        
        # Title of the PDF
        story.append(Paragraph(f"Appointment Request Summary", title_style))
        story.append(Spacer(1, 5))
        
        # Meta summary table (Request Number, Status, Generated At)
        meta_data = [
            [Paragraph("Request Number:", label_style), Paragraph(request_obj.request_number, value_style)],
            [Paragraph("Status:", label_style), Paragraph(request_obj.get_status_display(), value_style)],
            [Paragraph("Generated Time:", label_style), Paragraph(timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S %Z'), value_style)]
        ]
        meta_table = Table(meta_data, colWidths=[2.0*inch, 5.5*inch])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9'))
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))
        
        # 2. Child and Parent Details
        story.append(Paragraph("Patient & Parent Information", section_heading))
        patient_linked_str = "No"
        patient_code_str = "None"
        if request_obj.patient:
            patient_linked_str = "Yes"
            patient_code_str = request_obj.patient.patient_number
            
        child_dob = request_obj.date_of_birth.strftime('%Y-%m-%d') if request_obj.date_of_birth else "N/A"
        
        info_data = [
            [Paragraph("Child Name:", label_style), Paragraph(f"{request_obj.child_first_name} {request_obj.child_last_name}", value_style),
             Paragraph("Parent Name:", label_style), Paragraph(f"{request_obj.parent_first_name} {request_obj.parent_last_name}", value_style)],
            
            [Paragraph("Date of Birth:", label_style), Paragraph(child_dob, value_style),
             Paragraph("Relationship to Child:", label_style), Paragraph(request_obj.get_relationship_to_child_display(), value_style)],
            
            [Paragraph("Gender:", label_style), Paragraph(request_obj.get_gender_display(), value_style),
             Paragraph("Email:", label_style), Paragraph(request_obj.email, value_style)],
            
            [Paragraph("Mobile Number:", label_style), Paragraph(request_obj.mobile_number, value_style),
             Paragraph("Alternate Mobile:", label_style), Paragraph(request_obj.alternate_mobile_number or "None", value_style)],
            
            [Paragraph("Patient Linked:", label_style), Paragraph(patient_linked_str, value_style),
             Paragraph("Patient Number:", label_style), Paragraph(patient_code_str, value_style)]
        ]
        
        info_table = Table(info_data, colWidths=[1.5*inch, 2.25*inch, 1.5*inch, 2.25*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9'))
        ]))
        story.append(info_table)
        story.append(Spacer(1, 15))
        
        # 3. Request Preference Details
        story.append(Paragraph("Request & Schedule Preferences", section_heading))
        
        # Check for converted appointment
        appt = request_obj.appointments.filter(is_active=True).first()
        appt_str = "None"
        doctor_str = "None"
        if appt:
            appt_str = appt.appointment_number
            if appt.doctor:
                doctor_str = f"Dr. {appt.doctor.first_name} {appt.doctor.last_name} ({appt.doctor.email})"
        
        pref_data = [
            [Paragraph("Appointment Type:", label_style), Paragraph(request_obj.get_appointment_type_display(), value_style)],
            [Paragraph("Booking Source:", label_style), Paragraph(request_obj.get_booking_source_display(), value_style)],
            [Paragraph("Preferred Date:", label_style), Paragraph(request_obj.preferred_date.strftime('%Y-%m-%d') if request_obj.preferred_date else "N/A", value_style)],
            [Paragraph("Preferred Time Slot:", label_style), Paragraph(request_obj.preferred_time_slot, value_style)],
            [Paragraph("Primary Concern:", label_style), Paragraph(request_obj.primary_concern, value_style)],
            [Paragraph("Additional Notes:", label_style), Paragraph(request_obj.additional_notes or "None", value_style)],
            [Paragraph("Converted Appointment:", label_style), Paragraph(appt_str, value_style)],
            [Paragraph("Assigned Doctor:", label_style), Paragraph(doctor_str, value_style)]
        ]
        
        pref_table = Table(pref_data, colWidths=[2.0*inch, 5.5*inch])
        pref_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9'))
        ]))
        story.append(pref_table)
        
        # Build the document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
