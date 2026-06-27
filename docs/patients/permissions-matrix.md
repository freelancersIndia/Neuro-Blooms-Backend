# Patient Module Permissions Matrix

Role-Based Access Control (RBAC) configurations mapping the Roles in the system to patient endpoints.

## Roles Mapping Table

| Endpoint | Action / Method | Admin | Receptionist | Doctor |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/patients/statistics/` | Read Stats | Allowed | Allowed | Allowed |
| `GET /api/v1/patients/` | Read List | Allowed | Allowed | Allowed |
| `GET /api/v1/patients/{id}/` | Read Details | Allowed | Allowed | Allowed |
| `POST /api/v1/patients/` | Manual Create | Allowed | Allowed | Forbidden (403) |
| `PATCH /api/v1/patients/{id}/` | Edit profile | Allowed | Allowed | Forbidden (403) |
| `DELETE /api/v1/patients/{id}/` | Soft delete | Allowed | Forbidden (403) | Forbidden (403) |
| `GET /api/v1/patients/filter-options/` | Filter dropdowns | Allowed | Allowed | Allowed |
| `GET /api/v1/patients/search/` | Autocomplete search | Allowed | Allowed | Allowed |
| `GET /api/v1/patients/export/` | Export data | Allowed | Allowed | Allowed |
| `GET /api/v1/patients/summary/` | Chart summary | Allowed | Allowed | Allowed |
| `POST /api/v1/patients/bulk-actions/` | Bulk updates | Allowed | Allowed (no archive) | Forbidden (403) |
| `GET /api/v1/patients/recent/` | Dashboard widget | Allowed | Allowed | Allowed |

---

## Action Rules

### Write Restrictions
1. **Creation/Updation**: Only users with the role `ADMIN` or `RECEPTIONIST` are allowed to write or modify records. If a `DOCTOR` tries to invoke POST or PATCH, a `403 Forbidden` response is returned.
2. **Soft Delete**: Only `ADMIN` can mark patient records as deleted. If a `RECEPTIONIST` tries to call DELETE, a `403 Forbidden` response is returned.

### Read/Export Capabilities
1. `DOCTOR` users have full view capabilities on all patient details, statistics, and charts.
2. Export features are accessible to all three authenticated roles to allow doctors and receptionists to generate report sheets.
