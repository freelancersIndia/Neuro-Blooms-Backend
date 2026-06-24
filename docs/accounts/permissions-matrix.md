# Neuro Blooms Healthcare Management System
## Accounts Module Roles & Permissions Matrix

---

## Table of Contents
1. [Overview](#1-overview)
2. [Role Profiles](#2-role-profiles)
    - [ADMIN](#admin)
    - [DOCTOR](#doctor)
    - [RECEPTIONIST](#receptionist)
3. [System Permissions Matrix](#3-system-permissions-matrix)
4. [Multi-Role Architecture & Support](#4-multi-role-architecture--support)
5. [Permission Evaluation Flow](#5-permission-evaluation-flow)
    - [Code-Level Permission Helper Methods](#code-level-permission-helper-methods)
    - [Custom API Permission Classes](#custom-api-permission-classes)
6. [Best Practices & Security Hardening Guidelines](#6-best-practices--security-hardening-guidelines)

---

## 1. Overview
The Neuro Blooms Healthcare Management System manages access to medical records, scheduling tools, and system configurations using a **Role-Based Access Control (RBAC)** model. 

Access is restricted at the API endpoint level using custom permission classes. This ensures that users can only view or modify resources that match their professional duties. This document outlines the responsibilities, allowed actions, and restrictions for the three system roles: `ADMIN`, `DOCTOR`, and `RECEPTIONIST`.

---

## 2. Role Profiles

---

### ADMIN
#### Responsibilities
The `ADMIN` (System Administrator) is responsible for managing system configurations, creating and auditing user accounts, viewing security ledgers, and resolving account lockouts.

#### Allowed Actions
* Create, read, update, and delete all user accounts.
* Manually unlock user accounts locked due to brute-force protection.
* View, search, and filter the global security audit trail (`ActivityLog`).
* Manage system roles and global application configurations.
* Modify all fields on any user account, including assigning or revoking roles.

#### Restricted Actions
* **Clinical Decoupling**: Administrators cannot view detailed patient clinical files or write medical notes unless they are explicitly assigned the `DOCTOR` role as well (via multi-role membership).

---

### DOCTOR
#### Responsibilities
The `DOCTOR` (Medical Practitioner) manages patient care. They are responsible for writing clinical notes, reviewing medical histories, prescribing treatments, and managing their own patient appointment schedules.

#### Allowed Actions
* Access and edit patient clinical records, medical histories, and treatment plans.
* Write, sign, and update clinical notes.
* View and manage their own clinical appointment calendar.
* Access their own user profile and session settings.

#### Restricted Actions
* Cannot access the user administration interface.
* Cannot view security logs or unlock user accounts.
* Cannot create new user accounts or modify system roles.
* Cannot view appointment schedules or patient details belonging to other doctors unless explicitly shared.

---

### RECEPTIONIST
#### Responsibilities
The `RECEPTIONIST` manages clinic scheduling and patient intake. They are responsible for registering new patients, managing appointment bookings, checking in patients, and handling front-desk communications.

#### Allowed Actions
* Register new patient files and update basic demographic details (non-clinical).
* Create, reschedule, and cancel appointments across the clinic's calendar.
* Access their own user profile and session settings.

#### Restricted Actions
* **Clinical Block**: Receptionists are strictly blocked from viewing clinical notes, medical histories, and treatment details.
* Cannot access user administration or view security logs.
* Cannot modify user accounts or assign roles.

---

## 3. System Permissions Matrix

The table below maps the three system roles to the various features of the Neuro Blooms platform. It outlines the specific CRUD (Create, Read, Update, Delete) permissions enforced at the API gateway and view layers.

| Feature Area | ADMIN | DOCTOR | RECEPTIONIST | Enforced Constraints / Business Rules |
| :--- | :---: | :---: | :---: | :--- |
| **Dashboard** | **CRUD** | **R** | **R** | Admin sees system metrics; Doctor and Receptionist see role-specific calendars and task lists. |
| **Users** | **CRUD** | **None** | **None** | Only Admins can access user management endpoints (`/api/v1/users/`). |
| **Roles** | **R** | **None** | **None** | Roles are static; Admins can assign them but cannot delete standard system roles. |
| **Appointments** | **R** | **CRUD** | **CRUD** | Receptionists manage all bookings; Doctors manage their own schedules; Admins have read-only audit access. |
| **Patients** | **R** | **CRUD** | **CRU** | Receptionists manage demographics; only Doctors can access clinical fields (medical histories, notes). |
| **Security Logs** | **R** | **None** | **None** | Only Admins can view the security ledger (`/api/v1/security-logs/`). Logs are read-only. |
| **Profile** | **RU** | **RU** | **RU** | Users can view and update their own profiles. Admins can update any user's profile. |
| **Sessions** | **CRUD** | **RU** | **RU** | Users can list and revoke their own active sessions. Admins can revoke any session. |
| **Website Content**| **CRUD** | **None** | **None** | Only Admins can modify global website settings and public content templates. |

### Legend
* **C**: Create
* **R**: Read
* **U**: Update
* **D**: Delete
* **None**: Access Blocked (returns `403 Forbidden`)

---

## 4. Multi-Role Architecture & Support

The Neuro Blooms Accounts Module supports **Multi-Role Membership**. This allows a single user to be assigned multiple roles simultaneously (e.g., a user can be both a `DOCTOR` and an `ADMIN`).

### How Multi-Role Works
* **Database Representation**: Implemented as a Many-to-Many relationship using the `UserRole` join table.
* **Token Claims**: When a user authenticates, all their active roles are encoded into the JWT payload and returned in the user metadata:
  ```json
  {
    "user": {
      "email": "dr.smith@neuroblooms.com",
      "roles": ["DOCTOR", "ADMIN"]
    }
  }
  ```
* **Privilege Accumulation**: The permission system is additive. A user with multiple roles inherits the combined permissions of all their assigned roles. For example, a user who is both a `DOCTOR` and an `ADMIN` can manage user accounts **and** access clinical patient files.

---

## 5. Permission Evaluation Flow

When a client makes an API request, the server evaluates their permissions using a multi-layered check:

```
                  API Request Received
                           │
                           ▼
             Is the User Authenticated?
               /                    \
            (Yes)                   (No)
             /                        \
            ▼                          ▼
    Evaluate Custom              Return 401 Unauthorized
    Permission Classes
      /           \
  (Passed)      (Failed)
    /               \
   ▼                 ▼
Execute View     Return 403 Forbidden
and return DTO   Log SECURITY_VIOLATION
```

### Code-Level Permission Helper Methods
The custom `User` model provides helper methods to simplify role checks in the application code:

#### 1. `has_role(role_name)`
Checks if the user has a specific role.
```python
# Model Definition
def has_role(self, role_name: str) -> bool:
    return self.user_roles.filter(role__name=role_name).exists()
```
*Example Usage*:
```python
if request.user.has_role('ADMIN'):
    # Execute administrator-only logic
    pass
```

#### 2. `has_any_role(list_of_roles)`
Checks if the user has at least one of the roles in a provided list.
```python
# Model Definition
def has_any_role(self, list_of_roles: list) -> bool:
    return self.user_roles.filter(role__name__in=list_of_roles).exists()
```
*Example Usage*:
```python
if request.user.has_any_role(['DOCTOR', 'RECEPTIONIST']):
    # Allow access to scheduling features
    pass
```

### Custom API Permission Classes
At the API view layer, custom permission classes enforce role restrictions:

#### 1. `IsAdmin` Permission Class
Blocks access to any user who does not have the `ADMIN` role.
```python
from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to users with the ADMIN role.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_role('ADMIN')
        )
```

#### 2. `IsSuperAdmin` Permission Class
Allows access to superusers (users with `is_superuser = True`) or users with the `ADMIN` role.
```python
class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to superusers or users with the ADMIN role.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.has_role('ADMIN'))
        )
```

---

## 6. Best Practices & Security Hardening Guidelines

1. **Additive Permissions**: Ensure that custom permissions are always additive. A user's access level should be the union of all their assigned roles' permissions.
2. **Endpoint-Level Protection**: Apply permission classes directly to views or viewsets. Never rely solely on frontend UI hiding to secure endpoints.
3. **Explicit Role Checks**: Use `has_role()` or `has_any_role()` for granular, conditional checks within views, ensuring role validation is consistent across the codebase.
4. **Regular Access Reviews**: Administrators should perform regular reviews of user role assignments to ensure users do not accumulate unnecessary privileges over time.
