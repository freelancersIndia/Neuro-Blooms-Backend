# Patient Module Testing Guide

Details on executing verification test suites and manual validation procedures.

## Automated Testing

To run the automated tests covering permissions, soft delete, CSV streaming export, bulk actions, and duplicate prevention:

```powershell
python manage.py test apps.consultations.tests_patients_management
```

### Coverage Scope

- **Create Patient Validaions**: Future DOB rejection, duplicate mobile + child name rejection.
- **Update Checks**: Preventing editing of read-only fields (patient_number, created_by).
- **Soft Delete**: Confirming DELETE soft-deletes and filters out active listings.
- **Bulk Actions**: Validating permissions for archive, activate, deactivate, and assign doctor.
- **Export**: Validating Streaming CSV format correctness.
- **Statistics**: Single-hit aggregate metrics assertion.

## Manual Testing (Postman Examples)

1. **Get Statistics**:
   - `GET /api/v1/patients/statistics/`
   - Headers: `Authorization: Bearer <token>`
2. **Bulk Archive (Admin)**:
   - `POST /api/v1/patients/bulk-actions/`
   - Payload:
     ```json
     {
       "patient_ids": ["uuid-1"],
       "action": "archive"
     }
     ```
