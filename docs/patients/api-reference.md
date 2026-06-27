# Patients Management API Reference

Documenting the 12 endpoints of the Patients Management module.

## Endpoints Summary

1. `GET /api/v1/patients/statistics/` — Dashboard statistics metrics.
2. `GET /api/v1/patients/` — Main paginated patients list.
3. `GET /api/v1/patients/{id}/` — Complete patient profile details.
4. `POST /api/v1/patients/` — Manual patient registration.
5. `PATCH /api/v1/patients/{id}/` — Update patient profile (except read-only ID/dates).
6. `DELETE /api/v1/patients/{id}/` — Soft-delete a patient.
7. `GET /api/v1/patients/filter-options/` — Filter dropdown metadata options.
8. `GET /api/v1/patients/search/` — Autocomplete quick search (limit 10).
9. `GET /api/v1/patients/export/` — Stream patient list in CSV format.
10. `GET /api/v1/patients/summary/` — Donut chart data status counts.
11. `POST /api/v1/patients/bulk-actions/` — Bulk assign, activate, deactivate, or archive.
12. `GET /api/v1/patients/recent/` — Top 10 recently registered patients.

---

### 1. Patient Statistics
* **URL:** `/patients/statistics/`
* **Method:** `GET`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist, Doctor
* **Response 200 OK Example:**
```json
{
  "success": true,
  "message": "Patient statistics loaded successfully.",
  "data": {
    "total_patients": 450,
    "active_patients": 320,
    "under_treatment": 80,
    "treatment_completed": 40,
    "inactive_patients": 10,
    "new_this_month": 25,
    "male": 230,
    "female": 220,
    "average_age": 7.5,
    "upcoming_appointments": 15
  }
}
```

### 2. Patients List
* **URL:** `/patients/`
* **Method:** `GET`
* **Query Parameters:** `search`, `status`, `gender`, `doctor`, `age_group`, `registration_date_start`, `registration_date_end`, `has_upcoming_appointment`, `page`, `page_size`, `ordering`
* **Response 200 OK Example:**
```json
{
  "success": true,
  "message": "Patients fetched successfully.",
  "data": {
    "results": [
      {
        "id": "764b8bbd-d34e-4e4f-b67a-115f0ebcd22f",
        "patient_id": "NBP-000001",
        "photo": null,
        "child_name": "Aarav Kumar",
        "age": 6,
        "gender": "MALE",
        "parent_name": "Suresh Kumar",
        "relationship": "FATHER",
        "phone_number": "9876543210",
        "status": "ACTIVE",
        "assigned_doctor": {
          "id": 15,
          "name": "Dr. Sarah Paul",
          "email": "sarah.paul@example.com"
        },
        "last_visit": "2026-06-20",
        "next_appointment": "2026-07-01",
        "created_at": "2026-06-25T12:00:00Z"
      }
    ],
    "pagination": {
      "count": 1,
      "page": 1,
      "page_size": 10,
      "total_pages": 1,
      "next": null,
      "previous": null
    }
  }
}
```

### 3. Patient Details
* **URL:** `/patients/{id}/`
* **Method:** `GET`
* **Response 200 OK Example:**
```json
{
  "success": true,
  "message": "Patient details retrieved successfully.",
  "data": {
    "id": "764b8bbd-d34e-4e4f-b67a-115f0ebcd22f",
    "patient_id": "NBP-000001",
    "photo": null,
    "age": 6,
    "gender": "MALE",
    "date_of_birth": "2020-04-12",
    "child_first_name": "Aarav",
    "child_last_name": "Kumar",
    "parent_first_name": "Suresh",
    "parent_last_name": "Kumar",
    "relationship_to_child": "FATHER",
    "mobile_number": "9876543210",
    "alternate_mobile_number": "",
    "email": "suresh.kumar@example.com",
    "address": "123 Park Lane",
    "preferred_language": "English",
    "referral_source": "Google Search",
    "primary_diagnosis": "Mild Speech Delay",
    "notes": "Needs gentle coaching.",
    "emergency_contact_name": "Alice Kumar",
    "emergency_contact_phone": "9876543219",
    "assigned_doctor": {
      "id": 15,
      "name": "Dr. Sarah Paul",
      "email": "sarah.paul@example.com"
    },
    "latest_appointment": {
      "id": "abc-123",
      "appointment_number": "APT-00001",
      "appointment_date": "2026-06-20",
      "start_time": "10:00:00",
      "status": "COMPLETED",
      "appointment_type": "INITIAL"
    },
    "current_status": "ACTIVE",
    "registration_date": "2026-06-25T12:00:00Z",
    "created_by": {
      "id": 2,
      "name": "Recep User",
      "email": "receptionist@nb.com"
    }
  }
}
```

### 4. Create Patient
* **URL:** `/patients/`
* **Method:** `POST`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist
* **Payload:**
```json
{
  "child_first_name": "Daisy",
  "child_last_name": "Miller",
  "parent_first_name": "David",
  "parent_last_name": "Miller",
  "relationship_to_child": "FATHER",
  "mobile_number": "0987654321",
  "date_of_birth": "2019-03-11",
  "gender": "FEMALE",
  "address": "Miller House",
  "patient_status": "ACTIVE"
}
```
* **Response 201 Created Example:**
```json
{
  "success": true,
  "message": "Patient registered successfully.",
  "data": {
    "patient_id": "NBP-000002"
  }
}
```

### 5. Update Patient
* **URL:** `/patients/{id}/`
* **Method:** `PATCH`
* **Permissions:** Admin, Receptionist (Blocks read-only field edits like ID/dates)
* **Payload:**
```json
{
  "mobile_number": "1112223334",
  "patient_status": "UNDER_TREATMENT"
}
```
* **Response 200 OK Example:**
```json
{
  "success": true,
  "message": "Patient profile updated successfully.",
  "data": {
    "current_status": "UNDER_TREATMENT"
  }
}
```

### 6. Delete Patient
* **URL:** `/patients/{id}/`
* **Method:** `DELETE`
* **Permissions:** Admin Only (Soft-delete only. Sets `is_deleted=True`)
* **Response 200 OK:**
```json
{
  "success": true,
  "message": "Patient archived successfully."
}
```

### 7. Filter Options Metadata
* **URL:** `/patients/filter-options/`
* **Method:** `GET`
* **Response 200 OK Example:**
```json
{
  "success": true,
  "message": "Filter options retrieved successfully.",
  "data": {
    "statuses": [{"key": "ACTIVE", "label": "Active"}, ...],
    "genders": [{"key": "MALE", "label": "Male"}, ...],
    "doctors": [{"id": 15, "name": "Dr. Sarah Paul"}],
    "age_groups": [{"key": "0-3", "label": "0-3 Years"}],
    "languages": ["English", "Hindi"],
    "referral_sources": ["Google Search"]
  }
}
```

### 8. Quick Autocomplete Search
* **URL:** `/patients/search/`
* **Method:** `GET`
* **Query Parameters:** `search` (Search on Child, Parent, Phone, Patient ID)
* **Response 200 OK:** Returns maximum 10 records without pagination envelope.

### 9. Export Patients
* **URL:** `/patients/export/`
* **Method:** `GET`
* **Response:** Streamed CSV file download `patients_export.csv`.

### 10. Summary Chart
* **URL:** `/patients/summary/`
* **Method:** `GET`
* **Response 200 OK:**
```json
{
  "success": true,
  "message": "Patient status breakdown summary retrieved.",
  "data": {
    "Under Treatment": 80,
    "Completed": 40,
    "Inactive": 10,
    "Active": 320
  }
}
```

### 11. Bulk Actions
* **URL:** `/patients/bulk-actions/`
* **Method:** `POST`
* **Payload:**
```json
{
  "patient_ids": ["764b8bbd-d34e-4e4f-b67a-115f0ebcd22f"],
  "action": "assign_doctor",
  "doctor_id": "764b8bbd-d34e-4e4f-b67a-115f0ebcd221"
}
```
* **Response 200 OK:**
```json
{
  "success": true,
  "message": "Successfully assigned Dr. Sarah Paul to 1 patients."
}
```

### 12. Recent Patients
* **URL:** `/patients/recent/`
* **Method:** `GET`
* **Response 200 OK:** List of top 10 recently registered patients.
