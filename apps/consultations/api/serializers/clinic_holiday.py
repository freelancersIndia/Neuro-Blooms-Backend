from rest_framework import serializers
from apps.consultations.models.clinic_holiday import ClinicHoliday

class ClinicHolidaySerializer(serializers.ModelSerializer):
    holiday_name = serializers.CharField(max_length=150)
    holiday_date = serializers.DateField()

    class Meta:
        model = ClinicHoliday
        fields = ["id", "holiday_name", "holiday_date", "description", "created_at","is_active"]
        read_only_fields = ["id", "is_active", "created_at"]

    def validate_holiday_name(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Holiday name cannot be blank.")
        return value

    def validate_holiday_date(self, value):
        # Prevent active duplicate holidays on the same date
        qs = ClinicHoliday.objects.filter(holiday_date=value, is_active=True)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("Another active holiday is already configured on this date.")
        return value
