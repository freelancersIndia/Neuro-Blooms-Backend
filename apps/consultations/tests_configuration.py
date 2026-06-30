import datetime
import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import Role, UserRole
from apps.accounts.constants.roles import SystemRole
from apps.consultations.models import ClinicSettings, ClinicWeeklySchedule, ClinicHoliday, ClinicBreak
from apps.consultations.choices import Weekday, SlotStatus

User = get_user_model()

class ClinicConfigurationTestCase(APITestCase):

    def setUp(self):
        # Seed Roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # Create Users
        self.admin_user = User.objects.create_user(
            email="admin@test.com", password="password123", first_name="Admin"
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.receptionist_user = User.objects.create_user(
            email="receptionist@test.com", password="password123", first_name="Receptionist"
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.doctor_user = User.objects.create_user(
            email="doctor@test.com", password="password123", first_name="Doctor"
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Clear existing configs to avoid singleton collisions
        ClinicSettings.objects.all().delete()
        ClinicWeeklySchedule.objects.all().delete()
        ClinicHoliday.objects.all().delete()
        ClinicBreak.objects.all().delete()

    # ==========================================
    # 1. CLINIC SETTINGS TESTS
    # ==========================================

    def test_settings_load_and_auto_create(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["clinic_name"], "Neuro Blooms Child Development Center")
        self.assertEqual(response.data["data"]["timezone"], "Asia/Kolkata")
        self.assertEqual(ClinicSettings.objects.filter(is_active=True).count(), 1)

    def test_settings_update_successful(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        data = {
            "clinic_name": "New Name Child Center",
            "timezone": "Europe/London",
            "opening_time": "08:00:00",
            "closing_time": "17:00:00",
            "slot_duration_minutes": 60,
            "booking_window_days": 30,
            "allow_same_day_booking": False,
            "max_daily_appointments": 40
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["clinic_name"], "New Name Child Center")
        self.assertEqual(response.data["data"]["timezone"], "Europe/London")
        self.assertEqual(response.data["data"]["slot_duration_minutes"], 60)

    def test_settings_logo_upload(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        file_obj = io.BytesIO()
        image = Image.new("RGBA", size=(1, 1), color=(255, 0, 0))
        image.save(file_obj, "png")
        file_obj.seek(0)

        logo = SimpleUploadedFile("logo.png", file_obj.read(), content_type="image/png")
        data = {
            "clinic_logo": logo
        }
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["data"]["clinic_logo"])

    def test_settings_invalid_logo_extension(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        bad_logo = SimpleUploadedFile("logo.pdf", b"dummy_pdf", content_type="application/pdf")
        data = {"clinic_logo": bad_logo}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("clinic_logo", response.data["errors"])

    def test_settings_invalid_logo_size(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        large_data = b"a" * (3 * 1024 * 1024) # 3MB
        large_logo = SimpleUploadedFile("logo.jpg", large_data, content_type="image/jpeg")
        data = {"clinic_logo": large_logo}
        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("clinic_logo", response.data["errors"])

    def test_settings_invalid_timezone(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        data = {"timezone": "Invalid/Zone"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timezone", response.data["errors"])

    def test_settings_invalid_opening_closing(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        data = {"opening_time": "17:00:00", "closing_time": "09:00:00"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("closing_time", response.data["errors"])

    def test_settings_invalid_slot_duration(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        data = {"slot_duration_minutes": 25}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slot_duration_minutes", response.data["errors"])

    def test_settings_invalid_booking_window(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        data = {"booking_window_days": 400}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("booking_window_days", response.data["errors"])

    def test_settings_invalid_max_appointments(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-settings")

        data = {"max_daily_appointments": 300}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("max_daily_appointments", response.data["errors"])

    def test_settings_permissions(self):
        url = reverse("clinic-settings")

        # 1. Anonymous Access Denied
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Doctor Denied
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Receptionist Read Only
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(url, {"clinic_name": "Rec Name"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # 2. WEEKLY SCHEDULE TESTS
    # ==========================================

    def test_weekly_schedule_load_and_auto_create(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-weekly-schedule")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 7)
        self.assertEqual(ClinicWeeklySchedule.objects.count(), 7)

    def test_weekly_schedule_bulk_update_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-weekly-schedule")

        # First trigger get to auto-create
        self.client.get(url)

        schedules = [
            {"weekday": Weekday.MONDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.TUESDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.WEDNESDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.THURSDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.FRIDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.SATURDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "12:30:00"},
            {"weekday": Weekday.SUNDAY, "is_open": False, "opening_time": None, "closing_time": None},
        ]
        response = self.client.patch(url, {"schedules": schedules}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"][0]["is_open"])
        self.assertEqual(response.data["data"][0]["opening_time"], "08:30:00")

    def test_weekly_schedule_bulk_update_invalid_time(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-weekly-schedule")
        self.client.get(url)

        # Monday has opening_time > closing_time
        schedules = [
            {"weekday": Weekday.MONDAY, "is_open": True, "opening_time": "18:00:00", "closing_time": "09:00:00"},
            {"weekday": Weekday.TUESDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.WEDNESDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.THURSDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.FRIDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.SATURDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "12:30:00"},
            {"weekday": Weekday.SUNDAY, "is_open": False, "opening_time": None, "closing_time": None},
        ]
        response = self.client.patch(url, {"schedules": schedules}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weekly_schedule_duplicate_weekday(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("clinic-weekly-schedule")
        self.client.get(url)

        # Duplicate Mondays
        schedules = [
            {"weekday": Weekday.MONDAY, "is_open": True, "opening_time": "09:00:00", "closing_time": "17:00:00"},
            {"weekday": Weekday.MONDAY, "is_open": True, "opening_time": "09:00:00", "closing_time": "17:00:00"},
            {"weekday": Weekday.WEDNESDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.THURSDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.FRIDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "17:30:00"},
            {"weekday": Weekday.SATURDAY, "is_open": True, "opening_time": "08:30:00", "closing_time": "12:30:00"},
            {"weekday": Weekday.SUNDAY, "is_open": False, "opening_time": None, "closing_time": None},
        ]
        response = self.client.patch(url, {"schedules": schedules}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # 3. CLINIC HOLIDAYS TESTS
    # ==========================================

    def test_clinic_holiday_crud(self):
        self.client.force_authenticate(user=self.admin_user)
        list_url = reverse("clinic-holiday-list")

        # 1. Create Holiday
        data = {
            "holiday_name": "National Day",
            "holiday_date": "2026-08-15",
            "description": "Celebrate freedom"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        holiday_id = response.data["data"]["id"]

        # 2. Update Holiday
        detail_url = reverse("clinic-holiday-detail", args=[holiday_id])
        update_data = {"holiday_name": "Renamed National Day"}
        response = self.client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["holiday_name"], "Renamed National Day")

        # 3. Delete Holiday (Soft delete check)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ClinicHoliday.objects.filter(id=holiday_id, is_active=True).count(), 0)
        self.assertEqual(ClinicHoliday.objects.filter(id=holiday_id, is_active=False).count(), 1)

    def test_clinic_holiday_duplicate_date(self):
        self.client.force_authenticate(user=self.admin_user)
        list_url = reverse("clinic-holiday-list")

        # Create first holiday
        self.client.post(list_url, {"holiday_name": "H1", "holiday_date": "2026-10-10"})

        # Try duplicate date
        response = self.client.post(list_url, {"holiday_name": "H2", "holiday_date": "2026-10-10"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("holiday_date", response.data["errors"])

    def test_clinic_holiday_update_same_date(self):
        self.client.force_authenticate(user=self.admin_user)
        list_url = reverse("clinic-holiday-list")

        # Create holiday
        response = self.client.post(list_url, {
            "holiday_name": "National Day",
            "holiday_date": "2026-08-15",
            "description": "Celebrate freedom"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        holiday_id = response.data["data"]["id"]

        # Update holiday keeping the same date
        detail_url = reverse("clinic-holiday-detail", args=[holiday_id])
        response = self.client.patch(detail_url, {
            "holiday_name": "National Day Updated",
            "holiday_date": "2026-08-15"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["holiday_name"], "National Day Updated")

    # ==========================================
    # 4. CLINIC BREAKS TESTS
    # ==========================================

    def test_clinic_break_crud(self):
        self.client.force_authenticate(user=self.admin_user)
        
        # Populate settings and weekly schedule to pass operational hours validation
        ClinicSettings.objects.create(
            clinic_name="Test Clinic", opening_time="09:00:00", closing_time="18:00:00"
        )
        ClinicWeeklySchedule.objects.create(
            weekday=Weekday.MONDAY, is_open=True, opening_time="09:00:00", closing_time="18:00:00"
        )

        list_url = reverse("clinic-break-list")

        # 1. Create Break
        data = {
            "break_name": "Lunch Break",
            "weekday": Weekday.MONDAY,
            "start_time": "13:00:00",
            "end_time": "14:00:00"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        break_id = response.data["data"]["id"]

        # 2. Update Break
        detail_url = reverse("clinic-break-detail", args=[break_id])
        update_data = {"break_name": "Quick Coffee Break", "start_time": "15:00:00", "end_time": "15:30:00"}
        response = self.client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["break_name"], "Quick Coffee Break")

        # 3. Delete Break (Soft delete)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ClinicBreak.objects.filter(id=break_id, is_active=True).count(), 0)

    def test_clinic_break_overlap(self):
        self.client.force_authenticate(user=self.admin_user)
        ClinicSettings.objects.create(
            clinic_name="Test Clinic", opening_time="09:00:00", closing_time="18:00:00"
        )
        ClinicWeeklySchedule.objects.create(
            weekday=Weekday.MONDAY, is_open=True, opening_time="09:00:00", closing_time="18:00:00"
        )

        list_url = reverse("clinic-break-list")
        self.client.post(list_url, {
            "break_name": "Break 1", "weekday": Weekday.MONDAY, "start_time": "13:00:00", "end_time": "14:00:00"
        })

        # Overlapping Break
        data = {
            "break_name": "Break 2",
            "weekday": Weekday.MONDAY,
            "start_time": "13:30:00",
            "end_time": "14:30:00"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])

    def test_clinic_break_outside_hours(self):
        self.client.force_authenticate(user=self.admin_user)
        ClinicSettings.objects.create(
            clinic_name="Test Clinic", opening_time="09:00:00", closing_time="18:00:00"
        )
        ClinicWeeklySchedule.objects.create(
            weekday=Weekday.MONDAY, is_open=True, opening_time="09:00:00", closing_time="18:00:00"
        )

        list_url = reverse("clinic-break-list")
        
        # Break starts at 08:00 (clinic opens at 09:00)
        data = {
            "break_name": "Early Break",
            "weekday": Weekday.MONDAY,
            "start_time": "08:00:00",
            "end_time": "09:00:00"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])
