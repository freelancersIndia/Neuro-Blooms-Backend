# Neuro Blooms Hospital Management System - Enterprise API Contract

This document serves as the official, binding **API Contract** between the Frontend, Backend, QA, and Integrations teams for the **Neuro Blooms Hospital Management System**. 

## Table of Contents

1. [Authentication Module](#1-authentication-module)
   * [1.1 User Login](#11-user-login)
   * [1.2 Token Refresh](#12-token-refresh)
   * [1.3 User Logout](#13-user-logout)
2. [User & Role Management Module](#2-user--role-management-module)
   * [2.1 Create User](#21-create-user)
3. [Clinic Management Module](#3-clinic-management-module)
   * [3.1 Get Clinic Settings](#31-get-clinic-settings)
   * [3.2 Update Clinic Settings](#32-update-clinic-settings)
   * [3.3 Manage Weekly Schedule](#33-manage-weekly-schedule)
   * [3.4.1 List Clinic Holidays](#341-list-clinic-holidays)
   * [3.4.2 Create Clinic Holiday](#342-create-clinic-holiday)
   * [3.4.3 Delete Clinic Holiday](#343-delete-clinic-holiday)
4. [Doctor Scheduling Module](#4-doctor-scheduling-module)
   * [4.1 Update Doctor Availability Preferences](#41-update-doctor-availability-preferences)
   * [4.2 Update Doctor Working Days](#42-update-doctor-working-days)
   * [4.3.1 List Doctor Leaves](#431-list-doctor-leaves)
   * [4.3.2 Create Doctor Leave](#432-create-doctor-leave)
   * [4.3.3 Delete Doctor Leave](#433-delete-doctor-leave)
   * [4.4.1 List Doctor Blocked Slots](#441-list-doctor-blocked-slots)
   * [4.4.2 Create Doctor Blocked Slot](#442-create-doctor-blocked-slot)
   * [4.4.3 Delete Doctor Blocked Slot](#443-delete-doctor-blocked-slot)
5. [Appointment Requests Module](#5-appointment-requests-module)
   * [5.1 Submit Appointment Request](#51-submit-appointment-request)
   * [5.2 List Appointment Requests](#52-list-appointment-requests)
6. [Patient Matching Module](#6-patient-matching-module)
   * [6.1 Get Patient Matches](#61-get-patient-matches)
   * [6.2 Link Existing Patient](#62-link-existing-patient)
   * [6.3 Create New Patient from Request](#63-create-new-patient-from-request)
7. [Patient Management Module](#7-patient-management-module)
   * [7.1 Manual Patient Search](#71-manual-patient-search)
   * [7.2 Get Patient Details](#72-get-patient-details)
8. [Appointment Management Module](#8-appointment-management-module)
   * [8.1 List Appointments](#81-list-appointments)
   * [8.2 Edit Appointment](#82-edit-appointment)
   * [8.3 Check-in Patient](#83-check-in-patient)
   * [8.4 Start Doctor Consultation](#84-start-doctor-consultation)
   * [8.5 Cancel Appointment](#85-cancel-appointment)
9. [Clinical Consultation Module](#9-clinical-consultation-module)
   * [9.1 Open Consultation Session](#91-open-consultation-session)
   * [9.2 Create Consultation](#92-create-consultation)
   * [9.3 Complete Consultation](#93-complete-consultation)
10. [Follow-up & Case Management Module](#10-follow-up--case-management-module)
    * [10.1 Record Follow-up Decision](#101-record-follow-up-decision)
    * [10.2 Create Follow-up](#102-create-follow-up)
    * [10.3 Update Follow-up](#103-update-follow-up)
    * [10.4 Cancel Follow-up](#104-cancel-follow-up)
    * [10.5 Get Patient Treatment Journey](#105-get-patient-treatment-journey)
    * [10.6 Close Treatment Case](#106-close-treatment-case)
    * [10.7 Reopen Treatment Case](#107-reopen-treatment-case)
11. [File Uploads Module](#11-file-uploads-module)
    * [11.1 Upload Consultation Document](#111-upload-consultation-document)
12. [Timeline Module](#12-timeline-module)
    * [12.1 Get Patient Timeline](#121-get-patient-timeline)
13. [Reports & Analytics Module](#13-reports--analytics-module)
    * [13.1 Get Clinic Daily Metrics](#131-get-clinic-daily-metrics)
14. [Comprehensive Error Responses Section](#14-comprehensive-error-responses-section)

---

## 1. Authentication Module

### 1.1 User Login
* **API Name**: User Login
* **Module**: Authentication
* **Purpose**: Authenticates system users (Admins, Receptionists, Doctors) and issues JWT access/refresh token pairs.
* **Business Context**: Core entry point for securing the application. Enforces credential checks and tracks system access.
* **Endpoint**: `/api/v1/auth/login/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: None (Public)
* **Authorization (Allowed Roles)**: Anyone
* **Preconditions**: 
  * User account must exist in `accounts_user`.
  * User account must have `is_active = True`.
* **Business Rules**:
  * Max 5 failed login attempts per email per minute (IP-based and email-based rate limit).
  * Inactive/suspended accounts must be rejected with an explicit unauthorized response.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "email": "doctor@neuroblooms.com",
    "password": "Password123"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `email` | String | Yes | Valid email format, max 255 chars | The user's registered email address. |
  | `password` | String | Yes | Min 8 characters, max 128 chars | The plain-text password. |
* **Example Request**:
  ```http
  POST /api/v1/auth/login/ HTTP/1.1
  Host: api.neuroblooms.com
  Content-Type: application/json

  {
    "email": "doctor@neuroblooms.com",
    "password": "Password123"
  }
  ```
* **Processing Workflow**:
  1. Parse request body and run field-level validations.
  2. Query `accounts_user` by email. If not found, return `401 Unauthorized`.
  3. Validate password using Django's PBKDF2 hasher. If invalid, increment rate limit counter and return `401 Unauthorized`.
  4. Verify `is_active` is `True`. If `False`, return `401 Unauthorized`.
  5. Generate JWT Access Token (expires in 15 minutes) and Refresh Token (expires in 7 days).
  6. Create an entry in `accounts_activity_log` for the successful login.
  7. Return `200 OK` with tokens and user details.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Login successful.",
      "data": {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZDNiMDczODQtZDExMy00OTU2LWE1ZDgtNDcyZDdkNTY2M2RlIiwiZXhwIjoxODAwMDAwMDAwfQ...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZDNiMDczODQtZDExMy00OTU2LWE1ZDgtNDcyZDdkNTY2M2RlIiwiZXhwIjoxODAwMDAwMDAwfQ...",
        "user": {
          "id": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "email": "doctor@neuroblooms.com",
          "first_name": "John",
          "last_name": "Smith",
          "roles": ["DOCTOR"]
        }
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `success` | Boolean | Indicates successful execution. |
  | `message` | String | Human-readable success message. |
  | `data.access` | String | JWT access token (short-lived, 15 mins). |
  | `data.refresh` | String | JWT refresh token (long-lived, 7 days). |
  | `data.user.id` | UUID | Unique ID of the authenticated user. |
  | `data.user.email` | String | Registered email address. |
  | `data.user.roles` | Array of Strings | System roles assigned to the user. |
* **Side Effects**: Logs login timestamp and IP address to activity logs.
* **Database Changes**:
  * `accounts_activity_log`: INSERT (Login Event)
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `USER_LOGIN`, Level: `INFO`, Description: `User doctor@neuroblooms.com logged in successfully.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Rate-limited to 5 requests/min per IP/Email.
  * Password is never logged or cached.
  * Tokens are signed with HS256 using a secure server key.
* **Performance Considerations**:
  * Fast database lookup on indexed `email` field.
  * Argon2/PBKDF2 hashing is CPU-bound but optimized.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Authentication`
  * Operation ID: `user_login`

---

### 1.2 Token Refresh
* **API Name**: Token Refresh
* **Module**: Authentication
* **Purpose**: Generates a new short-lived JWT access token using a valid long-lived refresh token.
* **Business Context**: Enables silent re-authentication to maintain user sessions without prompting for credentials.
* **Endpoint**: `/api/v1/auth/token/refresh/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: None (Public - requires token in body)
* **Authorization (Allowed Roles)**: Anyone
* **Preconditions**:
  * Provided refresh token must not be expired or blacklisted.
* **Business Rules**:
  * Blacklisted tokens must be rejected immediately.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE4MDAwMDAwMDB9..."
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `refresh` | String | Yes | Valid JWT string | The refresh token issued during login. |
* **Example Request**:
  ```http
  POST /api/v1/auth/token/refresh/ HTTP/1.1
  Host: api.neuroblooms.com
  Content-Type: application/json

  {
    "refresh": "eyJ...refresh_token_payload..."
  }
  ```
* **Processing Workflow**:
  1. Validate refresh token signature and expiration.
  2. Query `django_blacklisted_token` to check if token is blacklisted.
  3. Generate a new JWT access token.
  4. Return `200 OK` with the new access token.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Token refreshed successfully.",
      "data": {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access_token_payload..."
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `success` | Boolean | Status of the operation. |
  | `message` | String | Success details. |
  | `data.access` | String | Newly generated short-lived JWT access token. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Refresh token rotation (RTR) can be enabled to mitigate token theft.
* **Performance Considerations**:
  * Pure cryptographic verification. No database hits if caching is used for blacklists.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Authentication`
  * Operation ID: `token_refresh`

---

### 1.3 User Logout
* **API Name**: User Logout
* **Module**: Authentication
* **Purpose**: Invalidates and blacklists the user's refresh token.
* **Business Context**: Securely ends the user session, mitigating session hijacking risks.
* **Endpoint**: `/api/v1/auth/logout/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: IsAuthenticated (All roles)
* **Preconditions**:
  * User must be authenticated.
* **Business Rules**:
  * The provided refresh token must be blacklisted.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <access_token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token_to_blacklist..."
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `refresh` | String | Yes | Valid JWT | The refresh token to invalidate. |
* **Example Request**:
  ```http
  POST /api/v1/auth/logout/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5c...
  Content-Type: application/json

  {
    "refresh": "eyJ...token..."
  }
  ```
* **Processing Workflow**:
  1. Verify the access token in the `Authorization` header.
  2. Extract the refresh token from the request body.
  3. Add the refresh token to the database blacklist table.
  4. Log logout activity.
  5. Return `204 No Content`.
* **Success Response**:
  * **HTTP Status**: `204 No Content`
  * **Body**: (Empty)
* **Response Field Documentation**: N/A
* **Side Effects**: Disables subsequent refresh requests using this token.
* **Database Changes**:
  * `django_blacklisted_token`: INSERT (Blacklisted token hash)
  * `accounts_activity_log`: INSERT (Logout Event)
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `USER_LOGOUT`, Level: `INFO`, Description: `User logged out and token blacklisted.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Prevents replay attacks by ensuring refresh tokens cannot be reused.
* **Performance Considerations**:
  * Write operation to the blacklist table; index on token signature is utilized.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Authentication`
  * Operation ID: `user_logout`

---

## 2. User & Role Management Module

### 2.1 Create User
* **API Name**: Create User
* **Module**: User & Role Management
* **Purpose**: Registers a new administrative or clinical staff user with roles.
* **Business Context**: Admin control panel operation to onboard new doctors, receptionists, or administrators.
* **Endpoint**: `/api/v1/admin/users/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`
* **Preconditions**:
  * Authenticated user must have admin permissions.
* **Business Rules**:
  * Email must be globally unique.
  * Roles must belong to the permitted set: `ADMIN`, `RECEPTIONIST`, `DOCTOR`.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "email": "sarah.connor@neuroblooms.com",
    "first_name": "Sarah",
    "last_name": "Connor",
    "roles": ["RECEPTIONIST"]
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `email` | String | Yes | Unique email, max 255 chars | User's unique email. |
  | `first_name` | String | Yes | Max 50 chars, alphanumeric | First name. |
  | `last_name` | String | Yes | Max 50 chars, alphanumeric | Last name. |
  | `roles` | Array of Strings | Yes | Min 1 role, must match valid roles | List of roles to assign. |
* **Example Request**:
  ```http
  POST /api/v1/admin/users/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "email": "sarah.connor@neuroblooms.com",
    "first_name": "Sarah",
    "last_name": "Connor",
    "roles": ["RECEPTIONIST"]
  }
  ```
* **Processing Workflow**:
  1. Validate authentication and verify requester role is `SUPER_ADMIN` or `ADMIN`.
  2. Parse and validate fields. Check if email already exists in `accounts_user`.
  3. Create user record in `accounts_user` with a randomized temporary password.
  4. Associate roles via the user-role mapping table.
  5. If the role includes `DOCTOR`, automatically trigger `doctor_availability` default record creation.
  6. Dispatch user onboarding email notification.
  7. Return `201 Created` with user details.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "User created successfully.",
      "data": {
        "id": "e5b8a1c2-d3f4-4a5b-6c7d-8e9f0a1b2c3d",
        "email": "sarah.connor@neuroblooms.com",
        "first_name": "Sarah",
        "last_name": "Connor",
        "roles": ["RECEPTIONIST"],
        "is_active": true
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `success` | Boolean | Status of the operation. |
  | `message` | String | Confirmation message. |
  | `data.id` | UUID | Generated user unique ID. |
  | `data.email` | String | User's registered email. |
  | `data.roles` | Array | Roles assigned to the user. |
  | `data.is_active` | Boolean | Active status of the account. |
* **Side Effects**: Automatically generates default schedule preferences if the user is a Doctor. Triggers password reset / invitation email.
* **Database Changes**:
  * `accounts_user`: INSERT
  * `consultations_doctor_availability` (if DOCTOR): INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `USER_CREATED`, Level: `INFO`, Description: `User sarah.connor@neuroblooms.com created by Admin.`
* **Audit Logs Generated**:
  * Table: `accounts_user`, Action: `CREATE`, Payload: `{email: sarah.connor@neuroblooms.com, roles: [RECEPTIONIST]}`
* **Notification Events Triggered (Current/Future)**:
  * Event: `user_onboarding_invitation` (sends activation link to user's email).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Enforces strict administrative checks.
  * Inputs are HTML-escaped.
* **Performance Considerations**:
  * Database transaction wrapping is used to ensure user and roles are created atomically.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `User Management`
  * Operation ID: `create_user`

---

## 3. Clinic Management Module

### 3.1 Get Clinic Settings
* **API Name**: Get Clinic Settings
* **Module**: Clinic Management
* **Purpose**: Retrieves global clinic settings (operating hours, slot durations, booking parameters).
* **Business Context**: Used by frontends to configure scheduling forms, date pickers, and calendar boundaries.
* **Endpoint**: `/api/v1/admin/clinic/settings/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**:
  * Clinic settings record must exist.
* **Business Rules**:
  * Only active staff members can access the settings.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/admin/clinic/settings/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate access token.
  2. Query `consultations_clinic_settings` table (typically fetches the single active config row).
  3. Return `200 OK` with settings payload.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Clinic settings retrieved successfully.",
      "data": {
        "id": "a92e105e-862d-4bfd-ba09-42b719491a92",
        "clinic_name": "Neuro Blooms",
        "opening_time": "09:00:00",
        "closing_time": "17:00:00",
        "slot_duration_minutes": 30,
        "booking_window_days": 30,
        "allow_same_day_booking": true,
        "max_daily_appointments": 50,
        "timezone": "Asia/Kolkata"
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.clinic_name` | String | Name of the hospital/clinic. |
  | `data.opening_time` | String | Daily opening time (HH:MM:SS). |
  | `data.closing_time` | String | Daily closing time (HH:MM:SS). |
  | `data.slot_duration_minutes` | Integer | Default time slot increment. |
  | `data.booking_window_days` | Integer | Number of days in advance booking is allowed. |
  | `data.allow_same_day_booking` | Boolean | True if bookings can be made for the current date. |
  | `data.timezone` | String | Operating timezone. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Read-only endpoint but restricted to authenticated staff.
* **Performance Considerations**:
  * Cached in redis to prevent database hits on every dashboard reload.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinic Management`
  * Operation ID: `get_clinic_settings`

---

### 3.2 Update Clinic Settings
* **API Name**: Update Clinic Settings
* **Module**: Clinic Management
* **Purpose**: Modifies the global operating configuration of the clinic.
* **Business Context**: Allows administrators to adjust capacity, operational hours, and scheduling windows.
* **Endpoint**: `/api/v1/admin/clinic/settings/`
* **HTTP Method**: `PATCH`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`
* **Preconditions**:
  * Settings record must exist in database.
* **Business Rules**:
  * `opening_time` must be chronologically before `closing_time`.
  * `slot_duration_minutes` must be 15, 30, 45, or 60.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "opening_time": "08:30:00",
    "closing_time": "18:00:00",
    "slot_duration_minutes": 30,
    "booking_window_days": 45,
    "allow_same_day_booking": false
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `clinic_name` | String | No | Max 100 chars | Name of the clinic. |
  | `opening_time` | String | No | Time format HH:MM:SS | Daily opening hour. |
  | `closing_time` | String | No | Time format HH:MM:SS | Daily closing hour. |
  | `slot_duration_minutes` | Integer | No | Min 10, Max 120 | Appointment slot size. |
  | `booking_window_days` | Integer | No | Min 1 | Horizon for future bookings. |
  | `allow_same_day_booking` | Boolean | No | - | Toggle for same-day bookings. |
* **Example Request**:
  ```http
  PATCH /api/v1/admin/clinic/settings/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "opening_time": "08:30:00",
    "closing_time": "18:00:00"
  }
  ```
* **Processing Workflow**:
  1. Validate admin permissions.
  2. Parse the patch parameters.
  3. Run business checks (e.g. verify `opening_time` < `closing_time`).
  4. Update the single settings row in `consultations_clinic_settings`.
  5. Clear clinic settings redis cache.
  6. Return `200 OK` with updated settings object.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Clinic settings updated successfully.",
      "data": {
        "id": "a92e105e-862d-4bfd-ba09-42b719491a92",
        "clinic_name": "Neuro Blooms",
        "opening_time": "08:30:00",
        "closing_time": "18:00:00",
        "slot_duration_minutes": 30,
        "booking_window_days": 45,
        "allow_same_day_booking": false,
        "max_daily_appointments": 50,
        "timezone": "Asia/Kolkata"
      }
    }
    ```
* **Response Field Documentation**: Same as `GET /api/v1/admin/clinic/settings/`.
* **Side Effects**: Invalidates settings cache. Future slot computations immediately use the new rules.
* **Database Changes**:
  * `consultations_clinic_settings`: UPDATE
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `CLINIC_SETTINGS_UPDATED`, Level: `WARNING`, Description: `Clinic settings updated by admin.`
* **Audit Logs Generated**:
  * Table: `consultations_clinic_settings`, Action: `UPDATE`, Changes: `{opening_time: 08:30:00, closing_time: 18:00:00}`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Enforce strict role validation. Sanitizes all text fields.
* **Performance Considerations**:
  * Cache eviction is cheap but critical to ensure consistency.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinic Management`
  * Operation ID: `update_clinic_settings`

---

### 3.3 Manage Weekly Schedule
* **API Name**: Manage Weekly Schedule
* **Module**: Clinic Management
* **Purpose**: Configures the days of the week the clinic is operational and their specific hours.
* **Business Context**: Controls the baseline calendar template for the hospital (e.g. closed on Sundays).
* **Endpoint**: `/api/v1/admin/clinic/weekly-schedule/`
* **HTTP Method**: `PATCH`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`
* **Preconditions**:
  * The weekdays provided must be valid enums.
* **Business Rules**:
  * Opening time must be before closing time for operational days.
  * Non-operational days must have opening and closing times set to `null`.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "schedules": [
      {
        "weekday": "MONDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "17:00:00"
      },
      {
        "weekday": "SUNDAY",
        "is_open": false,
        "opening_time": null,
        "closing_time": null
      }
    ]
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `schedules` | Array | Yes | Min 1 schedule item | List of weekday modifications. |
  | `schedules[].weekday` | String | Yes | Must match `Weekday` enum | Day to modify (e.g., `MONDAY`). |
  | `schedules[].is_open` | Boolean | Yes | - | Is the clinic open on this day. |
  | `schedules[].opening_time` | String | No | HH:MM:SS or null | Operating start time. |
  | `schedules[].closing_time` | String | No | HH:MM:SS or null | Operating end time. |
* **Example Request**:
  ```http
  PATCH /api/v1/admin/clinic/weekly-schedule/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "schedules": [
      {
        "weekday": "SATURDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "13:00:00"
      }
    ]
  }
  ```
* **Processing Workflow**:
  1. Validate admin authorization.
  2. Loop through `schedules` array and validate each item.
  3. Query `consultations_clinic_weekly_schedule` for the matching day.
  4. Perform atomic bulk updates using a database transaction.
  5. Clear weekly schedule cache.
  6. Return `200 OK`.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Weekly schedule updated successfully."
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `success` | Boolean | Status of update. |
  | `message` | String | Details of operation outcome. |
* **Side Effects**: Affects global slot availability calculation.
* **Database Changes**:
  * `consultations_clinic_weekly_schedule`: UPDATE
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `CLINIC_WEEKLY_SCHEDULE_UPDATED`, Level: `INFO`, Description: `Weekly schedule updated by admin.`
* **Audit Logs Generated**:
  * Table: `consultations_clinic_weekly_schedule`, Action: `BULK_UPDATE`, Payload: `[schedules updated]`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Restrict to admins. Standard input validation.
* **Performance Considerations**:
  * Wrapped in a single database transaction. Uses bulk updates.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinic Management`
  * Operation ID: `update_weekly_schedule`

---

### 3.4.1 List Clinic Holidays
* **API Name**: List Clinic Holidays
* **Module**: Clinic Management
* **Purpose**: Retrieves all registered clinic holidays.
* **Business Context**: Displays non-operational dates on the calendar to prevent scheduling.
* **Endpoint**: `/api/v1/admin/clinic/holidays/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**: None
* **Business Rules**:
  * Returns holidays sorted by date descending.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**:
  * `year` (Integer, Optional) - Filter by specific calendar year.
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/admin/clinic/holidays/?year=2026 HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Retrieve active user profile and verify authentication.
  2. Query `consultations_clinic_holiday` table, applying year filter if present.
  3. Return list.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Holidays retrieved successfully.",
      "data": [
        {
          "id": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "holiday_name": "Independence Day",
          "holiday_date": "2026-08-15",
          "description": "National Holiday"
        }
      ]
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data[].id` | UUID | Unique ID of the holiday record. |
  | `data[].holiday_name` | String | Display name of the holiday. |
  | `data[].holiday_date` | Date | The date of the holiday (YYYY-MM-DD). |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**:
  * Filtering by `year`. Sorting defaults to `holiday_date` ascending.
* **Security Notes**: Public viewable internally, restricted to staff.
* **Performance Considerations**:
  * Index on `holiday_date` is utilized.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinic Management`
  * Operation ID: `list_clinic_holidays`

---

### 3.4.2 Create Clinic Holiday
* **API Name**: Create Clinic Holiday
* **Module**: Clinic Management
* **Purpose**: Registers a new clinic-wide holiday.
* **Business Context**: Block out dates for festivals, maintenance, or national events.
* **Endpoint**: `/api/v1/admin/clinic/holidays/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`
* **Preconditions**:
  * The holiday date must not be in the past.
* **Business Rules**:
  * No two holidays can be registered on the same date.
  * If a holiday is registered on a date with existing appointments, the system must return a warning listing the affected appointments (or the client must confirm force-rescheduling).
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "holiday_name": "New Year Day",
    "holiday_date": "2027-01-01",
    "description": "Start of calendar year"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `holiday_name` | String | Yes | Max 100 chars | Name of holiday. |
  | `holiday_date` | Date | Yes | YYYY-MM-DD, future date | Date of holiday. |
  | `description` | String | No | Max 250 chars | Details about holiday. |
* **Example Request**:
  ```http
  POST /api/v1/admin/clinic/holidays/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "holiday_name": "New Year Day",
    "holiday_date": "2027-01-01"
  }
  ```
* **Processing Workflow**:
  1. Validate administrator access.
  2. Check if a holiday already exists on `holiday_date`.
  3. Scan `consultations_appointments` for any active appointments on `holiday_date`.
  4. If appointments exist, throw a `422 Unprocessable Entity` listing the conflicts (unless `force_confirm` is passed).
  5. Insert holiday into `consultations_clinic_holiday`.
  6. Invalidate calendar availability cache.
  7. Return `201 Created`.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Holiday created successfully.",
      "data": {
        "id": "c2b3a4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
        "holiday_name": "New Year Day",
        "holiday_date": "2027-01-01",
        "description": ""
      }
    }
    ```
* **Response Field Documentation**: Same as list.
* **Side Effects**: Automatically flags affected appointments for rescheduling.
* **Database Changes**:
  * `consultations_clinic_holiday`: INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `CLINIC_HOLIDAY_CREATED`, Level: `WARNING`, Description: `Holiday New Year Day created for 2027-01-01.`
* **Audit Logs Generated**:
  * Table: `consultations_clinic_holiday`, Action: `CREATE`, Payload: `{holiday_date: 2027-01-01}`
* **Notification Events Triggered (Current/Future)**:
  * Future: Notifications to patients whose bookings are affected by the holiday.
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Enforces admin role check.
* **Performance Considerations**:
  * Verifies conflicts using an indexed query on `appointment_date`.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinic Management`
  * Operation ID: `create_clinic_holiday`

---

### 3.4.3 Delete Clinic Holiday
* **API Name**: Delete Clinic Holiday
* **Module**: Clinic Management
* **Purpose**: Removes a registered holiday.
* **Business Context**: Used if a holiday was scheduled in error or the clinic decides to open.
* **Endpoint**: `/api/v1/admin/clinic/holidays/{id}/`
* **HTTP Method**: `DELETE`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`
* **Preconditions**:
  * The holiday record must exist.
* **Business Rules**:
  * Past holidays cannot be deleted (they must remain in the system for historical auditing).
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `id` (UUID, Required) - Unique ID of the holiday.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  DELETE /api/v1/admin/clinic/holidays/b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate admin credentials.
  2. Fetch holiday by ID. If not found, return `404 Not Found`.
  3. Verify if `holiday_date` is in the past. If yes, return `422 Unprocessable Entity`.
  4. Delete the holiday record.
  5. Evict cache.
  6. Return `204 No Content`.
* **Success Response**:
  * **HTTP Status**: `204 No Content`
  * **Body**: (Empty)
* **Response Field Documentation**: N/A
* **Side Effects**: Frees up the date for bookings.
* **Database Changes**:
  * `consultations_clinic_holiday`: DELETE
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `CLINIC_HOLIDAY_DELETED`, Level: `WARNING`, Description: `Holiday deleted.`
* **Audit Logs Generated**:
  * Table: `consultations_clinic_holiday`, Action: `DELETE`, ID: `b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restricted to admins.
* **Performance Considerations**: Fast primary key lookup.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinic Management`
  * Operation ID: `delete_clinic_holiday`

---

## 4. Doctor Scheduling Module

### 4.1 Update Doctor Availability Preferences
* **API Name**: Update Doctor Availability Preferences
* **Module**: Doctor Scheduling
* **Purpose**: Configures slot parameters and general settings for a doctor.
* **Business Context**: Used to toggle a doctor's booking status, session duration, and daily limits.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/availability/`
* **HTTP Method**: `PATCH`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * The target user must exist and have the `DOCTOR` role.
* **Business Rules**:
  * `consultation_duration_minutes` must be at least 15 minutes.
  * `max_daily_patients` must be a positive integer.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - ID of the doctor user.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "accepts_appointments": true,
    "consultation_duration_minutes": 45,
    "max_daily_patients": 10
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `accepts_appointments` | Boolean | No | - | Toggle to enable/disable scheduling. |
  | `consultation_duration_minutes` | Integer | No | Min 15 | Time per appointment. |
  | `max_daily_patients` | Integer | No | Min 1 | Patient cap per day. |
* **Example Request**:
  ```http
  PATCH /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/availability/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "consultation_duration_minutes": 30
  }
  ```
* **Processing Workflow**:
  1. Verify authorization. If role is DOCTOR, check if `doctor_id` matches the token user ID.
  2. Retrieve `consultations_doctor_availability` record for the doctor.
  3. Validate fields.
  4. Update database.
  5. Return `200 OK` with updated availability parameters.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Doctor availability updated successfully.",
      "data": {
        "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
        "accepts_appointments": true,
        "consultation_duration_minutes": 30,
        "max_daily_patients": 10
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.doctor_id` | UUID | ID of the doctor. |
  | `data.accepts_appointments` | Boolean | Scheduling availability status. |
  | `data.consultation_duration_minutes` | Integer | Duration per slot. |
  | `data.max_daily_patients` | Integer | Max patients per day. |
* **Side Effects**: Re-evaluates upcoming slot listings for this doctor.
* **Database Changes**:
  * `consultations_doctor_availability`: UPDATE
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `DOCTOR_AVAILABILITY_UPDATED`, Level: `INFO`, Description: `Availability updated for doctor.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Strict ownership validation (doctors cannot update other doctors' settings).
* **Performance Considerations**: Low impact. Fast indexed update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `update_doctor_availability`

---

### 4.2 Update Doctor Working Days
* **API Name**: Update Doctor Working Days
* **Module**: Doctor Scheduling
* **Purpose**: Configures specific operating hours for each day of the week for a doctor.
* **Business Context**: Controls the doctor's weekly routine (e.g., works Mon-Fri, 09:00 to 17:00).
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/working-days/`
* **HTTP Method**: `PATCH`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Doctor availability record must exist.
* **Business Rules**:
  * `start_time` must be before `end_time`.
  * Working hours must fall within the clinic's global opening and closing times.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - ID of the doctor.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "working_days": [
      {
        "weekday": "MONDAY",
        "is_working": true,
        "start_time": "09:00:00",
        "end_time": "17:00:00"
      }
    ]
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `working_days` | Array | Yes | Min 1 item | List of working days. |
  | `working_days[].weekday` | String | Yes | `Weekday` enum | Day of the week. |
  | `working_days[].is_working` | Boolean | Yes | - | Is doctor working on this day. |
  | `working_days[].start_time` | String | No | HH:MM:SS or null | Work start time. |
  | `working_days[].end_time` | String | No | HH:MM:SS or null | Work end time. |
* **Example Request**:
  ```http
  PATCH /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/working-days/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "working_days": [
      {
        "weekday": "TUESDAY",
        "is_working": true,
        "start_time": "10:00:00",
        "end_time": "16:00:00"
      }
    ]
  }
  ```
* **Processing Workflow**:
  1. Validate permissions (admin or doctor owner).
  2. Parse the payload. Verify start/end times against global clinic settings.
  3. Perform bulk update in `consultations_doctor_working_day` for this doctor.
  4. Return `200 OK`.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Working days updated successfully."
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `success` | Boolean | Success flag. |
  | `message` | String | Feedback details. |
* **Side Effects**: Triggers regeneration of slot matrices.
* **Database Changes**:
  * `consultations_doctor_working_day`: UPDATE / INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `DOCTOR_WORKING_DAYS_UPDATED`, Level: `INFO`, Description: `Working days updated for doctor.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Checked against doctor owner.
* **Performance Considerations**: Fast indexed updates.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `update_doctor_working_days`

---

### 4.3.1 List Doctor Leaves
* **API Name**: List Doctor Leaves
* **Module**: Doctor Scheduling
* **Purpose**: Retrieves all upcoming leaves registered for a specific doctor.
* **Business Context**: Used to audit leave calendars and verify availability.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/leaves/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Doctor must exist.
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - Doctor ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/leaves/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate credentials.
  2. Query `consultations_doctor_leave` table for `doctor_id`.
  3. Return list sorted by `start_date` ascending.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Leaves retrieved successfully.",
      "data": [
        {
          "id": "e4f5a6b7-c8d9-0e1f-2a3b-4c5d6e7f8a9b",
          "start_date": "2026-07-10",
          "end_date": "2026-07-12",
          "reason": "Medical conference"
        }
      ]
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data[].id` | UUID | Unique ID of the leave. |
  | `data[].start_date` | Date | Start of leave. |
  | `data[].end_date` | Date | End of leave. |
  | `data[].reason` | String | Reason. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: Default sorting by `start_date`.
* **Security Notes**: Doctors can only list their own leaves. Admins/Receptionists can list any.
* **Performance Considerations**: Fast query using index on `doctor_id`.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `list_doctor_leaves`

---

### 4.3.2 Create Doctor Leave
* **API Name**: Create Doctor Leave
* **Module**: Doctor Scheduling
* **Purpose**: Registers a new leave period for a doctor.
* **Business Context**: Blocks out doctor's schedule due to vacation, illness, or professional events.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/leaves/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Doctor must exist.
* **Business Rules**:
  * `end_date` must be greater than or equal to `start_date`.
  * Leave dates must not overlap with existing leaves.
  * If there are appointments scheduled during the leave, the system will return a validation error containing a list of conflicting appointments.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - Doctor ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "start_date": "2026-07-10",
    "end_date": "2026-07-12",
    "reason": "Medical conference"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `start_date` | Date | Yes | YYYY-MM-DD, future date | Leave start. |
  | `end_date` | Date | Yes | YYYY-MM-DD, >= start_date | Leave end. |
  | `reason` | String | No | Max 250 chars | Reason. |
* **Example Request**:
  ```http
  POST /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/leaves/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "start_date": "2026-07-10",
    "end_date": "2026-07-12",
    "reason": "Medical conference"
  }
  ```
* **Processing Workflow**:
  1. Check permissions.
  2. Validate dates (`end_date` >= `start_date`).
  3. Query `consultations_doctor_leave` for overlapping leaves. If found, throw conflict error.
  4. Query `consultations_appointments` for active bookings in the date range. If found, return list of conflicts.
  5. Save the leave record.
  6. Return `201 Created`.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Leave registered successfully.",
      "data": {
        "id": "e4f5a6b7-c8d9-0e1f-2a3b-4c5d6e7f8a9b",
        "start_date": "2026-07-10",
        "end_date": "2026-07-12",
        "reason": "Medical conference"
      }
    }
    ```
* **Response Field Documentation**: Same as list.
* **Side Effects**: Marks doctor slots as unavailable for the duration.
* **Database Changes**:
  * `consultations_doctor_leave`: INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `DOCTOR_LEAVE_CREATED`, Level: `WARNING`, Description: `Leave created for Doctor from 2026-07-10 to 2026-07-12.`
* **Audit Logs Generated**:
  * Table: `consultations_doctor_leave`, Action: `CREATE`, Payload: `{doctor_id: d3b07384-d113-4956-a5d8-472d7d56637e, start_date: 2026-07-10, end_date: 2026-07-12}`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Strict ownership and role validation.
* **Performance Considerations**: Evaluates overlaps using index on `doctor_id` and date range.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `create_doctor_leave`

---

### 4.3.3 Delete Doctor Leave
* **API Name**: Delete Doctor Leave
* **Module**: Doctor Scheduling
* **Purpose**: Deletes a doctor's leave record.
* **Business Context**: Used if a leave is cancelled and the doctor is now available to work.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/leaves/{id}/`
* **HTTP Method**: `DELETE`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Leave record must exist.
* **Business Rules**:
  * Past leaves cannot be deleted.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - Doctor ID.
  * `id` (UUID, Required) - Leave ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  DELETE /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/leaves/e4f5a6b7-c8d9-0e1f-2a3b-4c5d6e7f8a9b/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate access.
  2. Retrieve leave. Verify `doctor_id` and check if it's in the past.
  3. Delete the record.
  4. Return `204 No Content`.
* **Success Response**:
  * **HTTP Status**: `204 No Content`
  * **Body**: (Empty)
* **Response Field Documentation**: N/A
* **Side Effects**: Re-opens doctor's slots for booking.
* **Database Changes**:
  * `consultations_doctor_leave`: DELETE
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `DOCTOR_LEAVE_DELETED`, Level: `INFO`, Description: `Leave deleted.`
* **Audit Logs Generated**:
  * Table: `consultations_doctor_leave`, Action: `DELETE`, ID: `e4f5a6b7-c8d9-0e1f-2a3b-4c5d6e7f8a9b`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Checked against doctor owner.
* **Performance Considerations**: Fast key lookup.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `delete_doctor_leave`

---

### 4.4.1 List Doctor Blocked Slots
* **API Name**: List Doctor Blocked Slots
* **Module**: Doctor Scheduling
* **Purpose**: Retrieves all custom blocked slots for a doctor.
* **Business Context**: Displays blocked time blocks (like lunch hours or seminars) on the scheduler.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/blocked-slots/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Doctor must exist.
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - Doctor ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/blocked-slots/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Authenticate user.
  2. Query `consultations_doctor_blocked_slot` for the doctor.
  3. Return list.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Blocked slots retrieved successfully.",
      "data": [
        {
          "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "blocked_date": "2026-06-30",
          "start_time": "12:00:00",
          "end_time": "13:00:00",
          "reason": "Staff meeting"
        }
      ]
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data[].id` | UUID | Unique ID of blocked slot. |
  | `data[].blocked_date` | Date | Date blocked. |
  | `data[].start_time` | Time | Block start. |
  | `data[].end_time` | Time | Block end. |
  | `data[].reason` | String | Reason for block. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: Default sorting by date and start time.
* **Security Notes**: Ownership check enforced.
* **Performance Considerations**: Fast indexed query.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `list_doctor_blocked_slots`

---

### 4.4.2 Create Doctor Blocked Slot
* **API Name**: Create Doctor Blocked Slot
* **Module**: Doctor Scheduling
* **Purpose**: Block a specific time range on a specific day for a doctor.
* **Business Context**: Prevents appointments from being booked during meetings, breaks, or personal time.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/blocked-slots/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Doctor must exist.
* **Business Rules**:
  * `end_time` must be after `start_time`.
  * Blocked slot must not overlap with another blocked slot or leave.
  * If there are appointments in the blocked window, return a list of conflicting appointments.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - Doctor ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "blocked_date": "2026-06-30",
    "start_time": "12:00:00",
    "end_time": "13:00:00",
    "reason": "Staff meeting"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `blocked_date` | Date | Yes | YYYY-MM-DD | Date to block. |
  | `start_time` | String | Yes | HH:MM:SS | Start time. |
  | `end_time` | String | Yes | HH:MM:SS | End time. |
  | `reason` | String | No | Max 250 chars | Description. |
* **Example Request**:
  ```http
  POST /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/blocked-slots/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "blocked_date": "2026-06-30",
    "start_time": "12:00:00",
    "end_time": "13:00:00",
    "reason": "Staff meeting"
  }
  ```
* **Processing Workflow**:
  1. Validate credentials.
  2. Verify start/end times.
  3. Check overlapping blocked slots or leaves.
  4. Check if active appointments exist. If yes, return conflicts.
  5. Save the blocked slot.
  6. Return `201 Created`.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Slot blocked successfully.",
      "data": {
        "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "blocked_date": "2026-06-30",
        "start_time": "12:00:00",
        "end_time": "13:00:00",
        "reason": "Staff meeting"
      }
    }
    ```
* **Response Field Documentation**: Same as list.
* **Side Effects**: Blocked slots are removed from available booking slots.
* **Database Changes**:
  * `consultations_doctor_blocked_slot`: INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `DOCTOR_SLOT_BLOCKED`, Level: `INFO`, Description: `Time slot blocked for doctor.`
* **Audit Logs Generated**:
  * Table: `consultations_doctor_blocked_slot`, Action: `CREATE`, Payload: `{doctor_id, blocked_date, start_time, end_time}`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Ownership check.
* **Performance Considerations**: Fast range query.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `create_doctor_blocked_slot`

---

### 4.4.3 Delete Doctor Blocked Slot
* **API Name**: Delete Doctor Blocked Slot
* **Module**: Doctor Scheduling
* **Purpose**: Removes a blocked slot.
* **Business Context**: Frees up the blocked time window so it can be booked again.
* **Endpoint**: `/api/v1/admin/doctors/{doctor_id}/blocked-slots/{id}/`
* **HTTP Method**: `DELETE`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR` (only their own ID)
* **Preconditions**:
  * Blocked slot must exist.
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `doctor_id` (UUID, Required) - Doctor ID.
  * `id` (UUID, Required) - Blocked Slot ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  DELETE /api/v1/admin/doctors/d3b07384-d113-4956-a5d8-472d7d56637e/blocked-slots/a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate authorization.
  2. Retrieve blocked slot. Verify `doctor_id`.
  3. Delete blocked slot record.
  4. Return `204 No Content`.
* **Success Response**:
  * **HTTP Status**: `204 No Content`
  * **Body**: (Empty)
* **Response Field Documentation**: N/A
* **Side Effects**: Slots in this time range become available.
* **Database Changes**:
  * `consultations_doctor_blocked_slot`: DELETE
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `DOCTOR_SLOT_UNBLOCKED`, Level: `INFO`, Description: `Blocked slot removed.`
* **Audit Logs Generated**:
  * Table: `consultations_doctor_blocked_slot`, Action: `DELETE`, ID: `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Ownership validation.
* **Performance Considerations**: Fast key deletion.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Doctor Scheduling`
  * Operation ID: `delete_doctor_blocked_slot`

---

## 5. Appointment Requests Module

### 5.1 Submit Appointment Request
* **API Name**: Submit Appointment Request
* **Module**: Appointment Requests
* **Purpose**: Creates an initial booking request from the public website or a receptionist.
* **Business Context**: Captures new patient demographic details and their preferred slot before a receptionist approves it.
* **Endpoint**: `/api/v1/appointment-requests/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: None (Public) or Bearer JWT Access Token (if submitted by receptionist)
* **Authorization (Allowed Roles)**: Anyone
* **Preconditions**:
  * Preferred doctor must be active and accepting appointments.
* **Business Rules**:
  * The requested date must be in the future.
  * The date must fall within the clinic's booking window (e.g. up to 30 days in advance).
  * If same-day booking is disabled in clinic settings, the preferred date must be at least tomorrow.
* **State Transition Rules**:
  * Initial State: `PENDING`
* **Request Headers**:
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "child_first_name": "Tommy",
    "child_last_name": "Helper",
    "date_of_birth": "2020-05-15",
    "gender": "MALE",
    "parent_first_name": "Peter",
    "parent_last_name": "Helper",
    "parent_mobile": "+919876543210",
    "parent_email": "peter.helper@example.com",
    "preferred_doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
    "preferred_date": "2026-07-10",
    "preferred_time": "10:30",
    "primary_concern": "SPEECH_DELAY"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `child_first_name` | String | Yes | Max 50 chars, alphabetic | First name of child. |
  | `child_last_name` | String | Yes | Max 50 chars, alphabetic | Last name of child. |
  | `date_of_birth` | Date | Yes | YYYY-MM-DD, must be in past | Date of birth. |
  | `gender` | String | Yes | `Gender` enum | Gender. |
  | `parent_first_name` | String | Yes | Max 50 chars | Parent's first name. |
  | `parent_last_name` | String | Yes | Max 50 chars | Parent's last name. |
  | `parent_mobile` | String | Yes | Phone regex (E.164) | Contact number. |
  | `parent_email` | String | Yes | Email format | Email address. |
  | `preferred_doctor_id` | UUID | Yes | Active Doctor ID | Target doctor. |
  | `preferred_date` | Date | Yes | YYYY-MM-DD, future date | Date requested. |
  | `preferred_time` | String | Yes | HH:MM | Start time. |
  | `primary_concern` | String | Yes | `PrimaryConcern` enum | Reason for booking. |
* **Example Request**:
  ```http
  POST /api/v1/appointment-requests/ HTTP/1.1
  Host: api.neuroblooms.com
  Content-Type: application/json

  {
    "child_first_name": "Tommy",
    "child_last_name": "Helper",
    "date_of_birth": "2020-05-15",
    "gender": "MALE",
    "parent_first_name": "Peter",
    "parent_last_name": "Helper",
    "parent_mobile": "+919876543210",
    "parent_email": "peter.helper@example.com",
    "preferred_doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
    "preferred_date": "2026-07-10",
    "preferred_time": "10:30",
    "primary_concern": "SPEECH_DELAY"
  }
  ```
* **Processing Workflow**:
  1. Validate inputs and formats.
  2. Verify doctor exists and accepts appointments.
  3. Validate date against booking window and same-day booking constraints.
  4. Generate a unique `request_number` (format: `REQ-YYYYMMDD-XXXX`).
  5. Insert record into `consultations_appointment_request` with status `PENDING`.
  6. Trigger notification event to alert reception.
  7. Return `201 Created`.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Appointment request submitted successfully.",
      "data": {
        "id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
        "request_number": "REQ-20260628-A1B2",
        "status": "PENDING",
        "child_first_name": "Tommy",
        "child_last_name": "Helper",
        "preferred_date": "2026-07-10",
        "preferred_time": "10:30:00"
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.id` | UUID | Unique ID of the request. |
  | `data.request_number` | String | Readable request identifier. |
  | `data.status` | String | Status (`PENDING`). |
* **Side Effects**: Queues email/SMS confirmation to the parent.
* **Database Changes**:
  * `consultations_appointment_request`: INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `APPOINTMENT_REQUEST_SUBMITTED`, Level: `INFO`, Description: `Appointment request REQ-20260628-A1B2 submitted.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_request_received` (SMS/Email to parent).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Public endpoint protected by rate-limiting (e.g. max 20 submissions per IP per hour).
* **Performance Considerations**:
  * Fast inserts. No heavy joins.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Requests`
  * Operation ID: `submit_appointment_request`

---

### 5.2 List Appointment Requests
* **API Name**: List Appointment Requests
* **Module**: Appointment Requests
* **Purpose**: Retrieves a paginated list of appointment requests.
* **Business Context**: Used by receptionists to view, filter, and process incoming booking requests.
* **Endpoint**: `/api/v1/appointment-requests/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**: None
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**:
  * `status` (String, Optional) - Filter by request status (`PENDING`, `APPROVED`, etc.).
  * `search` (String, Optional) - Search by patient name, email, or phone.
  * `ordering` (String, Optional) - Sort field (e.g. `-created_at`).
  * `limit` (Integer, Optional) - Page size.
  * `offset` (Integer, Optional) - Pagination offset.
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/appointment-requests/?status=PENDING&limit=10 HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Verify receptionist/admin permissions.
  2. Parse filter and pagination parameters.
  3. Query `consultations_appointment_request` table.
  4. Return paginated array of requests.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Appointment requests retrieved successfully.",
      "data": {
        "count": 45,
        "next": "https://api.neuroblooms.com/api/v1/appointment-requests/?limit=10&offset=10",
        "previous": null,
        "results": [
          {
            "id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
            "request_number": "REQ-20260628-A1B2",
            "status": "PENDING",
            "child_first_name": "Tommy",
            "child_last_name": "Helper",
            "parent_first_name": "Peter",
            "parent_last_name": "Helper",
            "parent_mobile": "+919876543210",
            "preferred_date": "2026-07-10",
            "preferred_time": "10:30:00",
            "created_at": "2026-06-28T10:15:00Z"
          }
        ]
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.count` | Integer | Total records matching filters. |
  | `data.results` | Array | List of request objects. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**:
  * Fully supports limit-offset pagination, search on text fields, and sorting.
* **Security Notes**: Access restricted to scheduling staff.
* **Performance Considerations**:
  * Utilizes indexes on `status` and `created_at`.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Requests`
  * Operation ID: `list_appointment_requests`

---

## 6. Patient Matching Module

### 6.1 Get Patient Matches
* **API Name**: Get Patient Matches
* **Module**: Patient Matching
* **Purpose**: Calculates potential matching patient records from the database using fuzzy scoring.
* **Business Context**: Helps receptionists identify if a new appointment request is for an existing patient, preventing duplicate records.
* **Endpoint**: `/api/v1/patient-matching/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**:
  * The target `request_id` must exist.
* **Business Rules**:
  * Scoring is based on matches across: first name, last name, date of birth, and parent mobile.
  * A score >= 80% is considered a strong match.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**:
  * `request_id` (UUID, Required) - ID of the appointment request.
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/patient-matching/?request_id=c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Fetch the appointment request details.
  2. Query `consultations_patient` table.
  3. Execute fuzzy matching algorithm comparing names, DOB, and phone numbers.
  4. Assign a match score (0-100) to each candidate.
  5. Sort candidates by score descending and return.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Matches calculated successfully.",
      "data": {
        "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
        "matches": [
          {
            "patient_id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
            "patient_number": "PAT-000001",
            "child_name": "Tommy Helper",
            "parent_name": "Peter Helper",
            "match_score": 95,
            "matched_fields": ["last_name", "parent_mobile", "dob"]
          }
        ]
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.request_id` | UUID | Original request ID. |
  | `data.matches[].patient_id` | UUID | Matched patient record ID. |
  | `data.matches[].match_score` | Integer | Fuzzy match percentage (0-100). |
  | `data.matches[].matched_fields` | Array | List of fields that matched. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restrict access to scheduling staff.
* **Performance Considerations**:
  * Uses database indexes for initial candidate filtering (Trigram index or phone index) to avoid scanning the entire patient table.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Patient Matching`
  * Operation ID: `get_patient_matches`

---

### 6.2 Link Existing Patient
* **API Name**: Link Existing Patient
* **Module**: Patient Matching
* **Purpose**: Links an appointment request to an existing patient record and approves the booking.
* **Business Context**: Confirms the booking without creating a duplicate patient.
* **Endpoint**: `/api/v1/patient-matching/link/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**:
  * Both `request_id` and `patient_id` must exist.
  * The request must be in `PENDING` state.
* **Business Rules**:
  * Transition request status to `APPROVED`.
  * Create a new `CONFIRMED` appointment record associated with the patient.
* **State Transition Rules**:
  * Appointment Request: `PENDING` $\rightarrow$ `APPROVED` (then `PATIENT_LINKED`)
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
    "patient_id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `request_id` | UUID | Yes | Must exist, PENDING | The request to link. |
  | `patient_id` | UUID | Yes | Must exist | The target patient. |
* **Example Request**:
  ```http
  POST /api/v1/patient-matching/link/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
    "patient_id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d"
  }
  ```
* **Processing Workflow**:
  1. Authenticate user.
  2. Start database transaction.
  3. Lock and retrieve appointment request and patient records.
  4. Update request status to `PATIENT_LINKED`.
  5. Perform slot availability check for the doctor on the requested date and time.
  6. Create a new record in `consultations_appointments` with status `CONFIRMED`, linking it to the patient.
  7. Generate Patient and Appointment Timeline entries.
  8. Commit transaction.
  9. Dispatch booking confirmation notifications.
  10. Return `200 OK`.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Patient successfully linked to the request."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: Generates a confirmed appointment. Dispatches notification event.
* **Database Changes**:
  * `consultations_appointment_request`: UPDATE (status = 'PATIENT_LINKED')
  * `consultations_appointments`: INSERT
* **Timeline Entries Generated**:
  * Patient Timeline: `APPOINTMENT_CONFIRMED` (associated with the linked patient).
* **Activity Logs Generated**:
  * Action: `PATIENT_LINKED_TO_REQUEST`, Level: `INFO`, Description: `Linked patient PAT-000001 to request REQ-20260628-A1B2.`
* **Audit Logs Generated**:
  * Table: `consultations_appointment_request`, Action: `LINK_PATIENT`, Payload: `{patient_id: 9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d}`
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_confirmed` (sends details to parent).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Prevent concurrency conflicts during slot booking by acquiring a row lock on doctor schedule.
* **Performance Considerations**:
  * Database transaction wrapping is critical.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Patient Matching`
  * Operation ID: `link_existing_patient`

---

### 6.3 Create New Patient from Request
* **API Name**: Create New Patient from Request
* **Module**: Patient Matching
* **Purpose**: Creates a brand new patient record using the details from the request and approves the booking.
* **Business Context**: Used when the receptionist confirms that the patient is indeed new to the hospital.
* **Endpoint**: `/api/v1/patient-matching/create-patient/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**:
  * The `request_id` must exist and be in `PENDING` status.
* **Business Rules**:
  * Blocks creation if an exact duplicate (first name, last name, DOB, parent mobile) already exists in the patient database.
* **State Transition Rules**:
  * Appointment Request: `PENDING` $\rightarrow$ `PATIENT_CREATED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `request_id` | UUID | Yes | Must exist, PENDING | Request to convert. |
* **Example Request**:
  ```http
  POST /api/v1/patient-matching/create-patient/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f"
  }
  ```
* **Processing Workflow**:
  1. Validate access token.
  2. Start database transaction.
  3. Retrieve the appointment request. Lock the row.
  4. Check if an exact duplicate patient exists in `consultations_patient`. If yes, throw a `409 Conflict` error.
  5. Create a new patient record in `consultations_patient`, generating a unique `patient_number` (format: `PAT-XXXXXX`).
  6. Create a `CONFIRMED` appointment record.
  7. Update the request status to `PATIENT_CREATED`.
  8. Create timeline entries.
  9. Commit transaction.
  10. Return patient ID and number.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "New patient record created and linked.",
      "data": {
        "patient_id": "8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f",
        "patient_number": "PAT-000042",
        "appointment_id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f"
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.patient_id` | UUID | The newly created patient's ID. |
  | `data.patient_number` | String | Generated unique registration number. |
  | `data.appointment_id` | UUID | The confirmed appointment's ID. |
* **Side Effects**: Enrolls the new patient in the hospital. Triggers confirmation notification.
* **Database Changes**:
  * `consultations_patient`: INSERT
  * `consultations_appointments`: INSERT
  * `consultations_appointment_request`: UPDATE (status = 'PATIENT_CREATED')
* **Timeline Entries Generated**:
  * Patient Timeline: `PATIENT_REGISTERED` and `APPOINTMENT_CONFIRMED`.
* **Activity Logs Generated**:
  * Action: `PATIENT_CREATED_FROM_REQUEST`, Level: `INFO`, Description: `Created patient PAT-000042 from request.`
* **Audit Logs Generated**:
  * Table: `consultations_patient`, Action: `CREATE`, Payload: `{patient_number: PAT-000042, name: Tommy Helper}`
* **Notification Events Triggered (Current/Future)**:
  * Event: `patient_registered` (Welcome SMS/Email to parent).
  * Event: `appointment_confirmed` (Appointment details).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Wrapped in transactional locks to prevent duplicate submissions from generating multiple patients.
* **Performance Considerations**:
  * Transaction safety is prioritized.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Patient Matching`
  * Operation ID: `create_patient_from_request`

---

## 7. Patient Management Module

### 7.1 Manual Patient Search
* **API Name**: Manual Patient Search
* **Module**: Patient Management
* **Purpose**: Enables search across all active patient records.
* **Business Context**: Used by staff to find patient profiles when booking walk-ins, checking medical histories, or answering calls.
* **Endpoint**: `/api/v1/patients/search/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**: None
* **Business Rules**:
  * Search term must be at least 2 characters.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**:
  * `search` (String, Required) - Search term (matches patient number, name, parent phone, or parent email).
  * `limit` (Integer, Optional) - Page size.
  * `offset` (Integer, Optional) - Offset.
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/patients/search/?search=Tommy&limit=5 HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate authentication.
  2. Parse the search parameter. If length < 2, return `400 Bad Request`.
  3. Query `consultations_patient` using case-insensitive partial match (`icontains`) on names, phone, and email.
  4. Return paginated results.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Patients retrieved successfully.",
      "data": {
        "count": 1,
        "results": [
          {
            "id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
            "patient_number": "PAT-000001",
            "child_first_name": "Tommy",
            "child_last_name": "Helper",
            "date_of_birth": "2020-05-15",
            "parent_first_name": "Peter",
            "parent_last_name": "Helper",
            "parent_mobile": "+919876543210"
          }
        ]
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.results[].patient_number` | String | Hospital registration ID. |
  | `data.results[].child_first_name` | String | First name. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: Paginated via limit/offset.
* **Security Notes**: Input is sanitized to prevent SQL injection.
* **Performance Considerations**:
  * Uses database indexes on `child_first_name`, `child_last_name`, and `parent_mobile`.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Patient Management`
  * Operation ID: `search_patients`

---

### 7.2 Get Patient Details
* **API Name**: Get Patient Details
* **Module**: Patient Management
* **Purpose**: Retrieves the full profile details of a registered patient.
* **Business Context**: Displays the patient summary card, demographics, and medical history.
* **Endpoint**: `/api/v1/patients/{patient_id}/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**:
  * The patient record must exist.
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `patient_id` (UUID, Required) - Patient ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/patients/9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Verify token.
  2. Query `consultations_patient` by ID. If not found, return `404 Not Found`.
  3. Return details.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Patient details retrieved.",
      "data": {
        "id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
        "patient_number": "PAT-000001",
        "child_first_name": "Tommy",
        "child_last_name": "Helper",
        "date_of_birth": "2020-05-15",
        "gender": "MALE",
        "parent_first_name": "Peter",
        "parent_last_name": "Helper",
        "parent_mobile": "+919876543210",
        "parent_email": "peter.helper@example.com",
        "status": "ACTIVE",
        "created_at": "2026-06-28T10:20:00Z"
      }
    }
    ```
* **Response Field Documentation**: Same as search, includes full contact and status details.
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restrict to authorized clinical staff.
* **Performance Considerations**: Fast key lookup.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Patient Management`
  * Operation ID: `get_patient_details`

---

## 8. Appointment Management Module

### 8.1 List Appointments
* **API Name**: List Appointments
* **Module**: Appointment Management
* **Purpose**: Retrieves a list of scheduled appointments.
* **Business Context**: Powers the clinic's daily agenda and doctor dashboards.
* **Endpoint**: `/api/v1/appointments/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**: None
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**:
  * `status` (String, Optional) - Filter by status (`CONFIRMED`, `CHECKED_IN`, etc.).
  * `doctor_id` (UUID, Optional) - Filter by doctor.
  * `date` (Date, Optional) - Filter by specific date (YYYY-MM-DD).
  * `search` (String, Optional) - Search by patient name or number.
  * `limit`, `offset` (Integer, Optional) - Pagination.
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/appointments/?date=2026-06-28&status=CONFIRMED HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Authenticate user.
  2. Parse filter query parameters.
  3. Query `consultations_appointments` table applying joins on patient and doctor.
  4. Return paginated appointments list.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Appointments retrieved successfully.",
      "data": {
        "count": 1,
        "results": [
          {
            "id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
            "appointment_number": "APT-000001",
            "patient": {
              "id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
              "name": "Tommy Helper"
            },
            "doctor": {
              "id": "d3b07384-d113-4956-a5d8-472d7d56637e",
              "name": "Dr. John Smith"
            },
            "appointment_date": "2026-06-28",
            "start_time": "10:30:00",
            "end_time": "11:00:00",
            "status": "CONFIRMED",
            "priority": "MEDIUM"
          }
        ]
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.results[].appointment_number` | String | Unique appointment identifier. |
  | `data.results[].status` | String | Current status of the booking. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**:
  * Supports filtering by date range, status, and doctor. Sorting defaults to date/time.
* **Security Notes**: Access restricted to authenticated staff.
* **Performance Considerations**:
  * Uses `select_related('patient', 'doctor')` to prevent N+1 query problems.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Management`
  * Operation ID: `list_appointments`

---

### 8.2 Edit Appointment
* **API Name**: Edit Appointment
* **Module**: Appointment Management
* **Purpose**: Modifies details of an existing appointment.
* **Business Context**: Reschedules appointments or updates clinical/internal notes.
* **Endpoint**: `/api/v1/appointments/{id}/`
* **HTTP Method**: `PATCH`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**:
  * Appointment must exist and must not be in a terminal state (`COMPLETED`, `CANCELLED`).
* **Business Rules**:
  * If the date, doctor, or time changes, the system re-runs slot availability checks.
  * Rescheduling must comply with the doctor's working hours, leaves, and blocked slots.
* **State Transition Rules**:
  * If date/time changes, status may transition back to `CONFIRMED` from `CHECKED_IN` if applicable.
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `id` (UUID, Required) - Appointment ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "appointment_date": "2026-07-20",
    "start_time": "11:00:00",
    "internal_notes": "Rescheduled due to doctor schedule change."
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `appointment_date` | Date | No | YYYY-MM-DD, future | New date. |
  | `start_time` | String | No | HH:MM:SS | New start time. |
  | `internal_notes` | String | No | Max 500 chars | Staff notes. |
* **Example Request**:
  ```http
  PATCH /api/v1/appointments/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "appointment_date": "2026-07-20",
    "start_time": "11:00:00"
  }
  ```
* **Processing Workflow**:
  1. Retrieve appointment. Lock row.
  2. Verify it is editable (not completed/cancelled).
  3. If date/time/doctor is updated, check slot availability using the scheduling engine.
  4. Perform the database update.
  5. Generate timeline entry.
  6. Return updated object.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Appointment updated successfully.",
      "data": {
        "id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "appointment_date": "2026-07-20",
        "start_time": "11:00:00",
        "status": "CONFIRMED"
      }
    }
    ```
* **Response Field Documentation**: Same as list.
* **Side Effects**: Dispatches rescheduling notification.
* **Database Changes**:
  * `consultations_appointments`: UPDATE
* **Timeline Entries Generated**:
  * Patient/Appointment Timeline: `APPOINTMENT_RESCHEDULED`.
* **Activity Logs Generated**:
  * Action: `APPOINTMENT_UPDATED`, Level: `INFO`, Description: `Appointment APT-000001 rescheduled to 2026-07-20.`
* **Audit Logs Generated**:
  * Table: `consultations_appointments`, Action: `UPDATE`, Changes: `{appointment_date: 2026-07-20}`
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_rescheduled` (SMS/Email to parent).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restrict to staff.
* **Performance Considerations**:
  * Row-level locking on the slot checking step prevents race conditions.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Management`
  * Operation ID: `update_appointment`

---

### 8.3 Check-in Patient
* **API Name**: Check-in Patient
* **Module**: Appointment Management
* **Purpose**: Marks the patient as arrived at the clinic.
* **Business Context**: Moves the patient to the waiting room queue, notifying the doctor.
* **Endpoint**: `/api/v1/appointments/{id}/check-in/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**:
  * Appointment must exist in `CONFIRMED` status.
  * Must be called on the day of the appointment.
* **Business Rules**:
  * Cannot check-in for future or past dates.
* **State Transition Rules**:
  * `CONFIRMED` $\rightarrow$ `CHECKED_IN`
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `id` (UUID, Required) - Appointment ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  POST /api/v1/appointments/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/check-in/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Retrieve appointment.
  2. Verify status is `CONFIRMED` and date is today.
  3. Update status to `CHECKED_IN`.
  4. Record status change in history.
  5. Generate timeline entry.
  6. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Patient checked in successfully."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: Adds the patient to the doctor's active queue.
* **Database Changes**:
  * `consultations_appointments`: UPDATE (status = 'CHECKED_IN')
  * `consultations_appointment_status_history`: INSERT
* **Timeline Entries Generated**:
  * Patient Timeline: `PATIENT_CHECKED_IN`
* **Activity Logs Generated**:
  * Action: `PATIENT_CHECKED_IN`, Level: `INFO`, Description: `Patient checked in for appointment APT-000001.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**:
  * Event: `patient_checked_in` (notifies doctor via dashboard socket).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Staff restricted.
* **Performance Considerations**: Fast single-row update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Management`
  * Operation ID: `check_in_patient`

---

### 8.4 Start Doctor Consultation
* **API Name**: Start Doctor Consultation
* **Module**: Appointment Management
* **Purpose**: Initiates the clinical consultation session.
* **Business Context**: Transition triggered by the doctor when the patient enters the consultation room.
* **Endpoint**: `/api/v1/appointments/{id}/start-consultation/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (must be the assigned doctor)
* **Preconditions**:
  * Appointment must be in `CHECKED_IN` status.
* **Business Rules**:
  * Only the doctor assigned to the appointment can start it.
* **State Transition Rules**:
  * `CHECKED_IN` $\rightarrow$ `IN_CONSULTATION`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `id` (UUID, Required) - Appointment ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  POST /api/v1/appointments/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/start-consultation/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Retrieve appointment.
  2. Verify requesting user is the assigned doctor.
  3. Verify status is `CHECKED_IN`.
  4. Update status to `IN_CONSULTATION`.
  5. Check if an active `TreatmentCase` exists for this patient and doctor. If not, automatically create one.
  6. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Consultation started.",
      "data": {
        "treatment_case_id": "8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f"
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.treatment_case_id` | UUID | The ID of the active treatment case. |
* **Side Effects**: Launches the doctor's clinical workspace.
* **Database Changes**:
  * `consultations_appointments`: UPDATE (status = 'IN_CONSULTATION')
  * `consultations_treatment_cases` (if new): INSERT
* **Timeline Entries Generated**:
  * Patient Timeline: `CONSULTATION_STARTED`
* **Activity Logs Generated**:
  * Action: `CONSULTATION_STARTED`, Level: `INFO`, Description: `Consultation started for APT-000001.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Strict ownership check (doctor ID matches).
* **Performance Considerations**: Fast update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Management`
  * Operation ID: `start_consultation`

---

### 8.5 Cancel Appointment
* **API Name**: Cancel Appointment
* **Module**: Appointment Management
* **Purpose**: Cancels a scheduled appointment.
* **Business Context**: Used when a parent cancels or the clinic cannot accommodate the booking.
* **Endpoint**: `/api/v1/appointments/{id}/cancel/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**:
  * Appointment must not be in `COMPLETED` or already `CANCELLED` status.
* **Business Rules**:
  * Requires a cancellation reason.
* **State Transition Rules**:
  * `CONFIRMED` or `CHECKED_IN` $\rightarrow$ `CANCELLED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `id` (UUID, Required) - Appointment ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "reason": "Patient is unwell."
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `reason` | String | Yes | Max 250 chars | Reason for cancellation. |
* **Example Request**:
  ```http
  POST /api/v1/appointments/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/cancel/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "reason": "Patient is unwell."
  }
  ```
* **Processing Workflow**:
  1. Retrieve appointment.
  2. Verify status is not completed or cancelled.
  3. Update status to `CANCELLED` and save reason.
  4. Write to status history.
  5. Generate timeline entry.
  6. Dispatch notification event.
  7. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Appointment cancelled successfully."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: Releases the booked slot.
* **Database Changes**:
  * `consultations_appointments`: UPDATE (status = 'CANCELLED')
  * `consultations_appointment_status_history`: INSERT
* **Timeline Entries Generated**:
  * Patient Timeline: `APPOINTMENT_CANCELLED`
* **Activity Logs Generated**:
  * Action: `APPOINTMENT_CANCELLED`, Level: `WARNING`, Description: `Appointment APT-000001 cancelled.`
* **Audit Logs Generated**:
  * Table: `consultations_appointments`, Action: `CANCEL`, Payload: `{reason: Patient is unwell}`
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_cancelled` (SMS/Email to parent and doctor).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restrict to authorized staff.
* **Performance Considerations**: Fast update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Appointment Management`
  * Operation ID: `cancel_appointment`

---

## 9. Clinical Consultation Module

### 9.1 Open Consultation Session
* **API Name**: Open Consultation Session
* **Module**: Clinical Consultation
* **Purpose**: Retrieves all clinical workspace data for a specific appointment.
* **Business Context**: Loaded by the doctor at the start of a consultation to review patient history, past visits, and current vitals/demographics.
* **Endpoint**: `/api/v1/consultations/appointments/{appointment_id}/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (assigned), `SUPER_ADMIN`, `ADMIN` (read-only)
* **Preconditions**:
  * Appointment must exist.
* **Business Rules**:
  * Access is restricted to the assigned doctor (or administrators for auditing).
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `appointment_id` (UUID, Required) - ID of the appointment.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/consultations/appointments/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Retrieve appointment. Verify doctor assignment.
  2. Query patient profile details.
  3. Query past completed consultations for the patient.
  4. Compile data and return.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Consultation workspace loaded.",
      "data": {
        "appointment": {
          "id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
          "appointment_number": "APT-000001",
          "appointment_date": "2026-06-28"
        },
        "patient_summary": {
          "id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
          "name": "Tommy Helper",
          "age": "6 years",
          "total_visits": 1
        },
        "previous_consultations": []
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.appointment` | Object | Current appointment details. |
  | `data.patient_summary` | Object | Summary demographics. |
  | `data.previous_consultations` | Array | Historical visits list. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**:
  * Action: `ACCESS_CLINICAL_RECORD`, Target: `9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Highly sensitive patient data. Strict role and ownership validation is enforced.
* **Performance Considerations**:
  * Fetches historical records using optimized queries with limit 5.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinical Consultation`
  * Operation ID: `open_consultation_session`

---

### 9.2 Create Consultation
* **API Name**: Create Consultation
* **Module**: Clinical Consultation
* **Purpose**: Saves draft clinical notes and findings for an appointment.
* **Business Context**: Used by doctors during the session to input observations, diagnosis, and plans.
* **Endpoint**: `/api/v1/consultations/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (must be the assigned doctor)
* **Preconditions**:
  * Appointment must be in `IN_CONSULTATION` status.
* **Business Rules**:
  * Only one consultation can be created per appointment.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "appointment_id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
    "chief_complaint": "Speech delay, struggles with multi-syllable words.",
    "clinical_findings": "Attention span is normal. Expressive language is delayed.",
    "diagnosis": "Expressive Language Disorder",
    "treatment_notes": "Recommend speech therapy twice a week."
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `appointment_id` | UUID | Yes | Must exist, IN_CONSULTATION | Target appointment. |
  | `chief_complaint` | String | Yes | Max 500 chars | Primary complaint. |
  | `clinical_findings` | String | No | - | Doctor findings. |
  | `diagnosis` | String | Yes | Max 250 chars | Diagnosed condition. |
  | `treatment_notes` | String | Yes | - | Recommended plan. |
* **Example Request**:
  ```http
  POST /api/v1/consultations/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "appointment_id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
    "chief_complaint": "Speech delay",
    "diagnosis": "Expressive Language Disorder",
    "treatment_notes": "Speech therapy"
  }
  ```
* **Processing Workflow**:
  1. Verify doctor ownership.
  2. Validate fields. Check if a consultation already exists for this appointment.
  3. Insert consultation record into `consultations_consultation` as a draft.
  4. Return the created object.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Consultation draft saved successfully.",
      "data": {
        "id": "e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
        "appointment_id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "chief_complaint": "Speech delay",
        "status": "DRAFT"
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.id` | UUID | Unique ID of the consultation. |
  | `data.status` | String | State of consultation (`DRAFT`). |
* **Side Effects**: None
* **Database Changes**:
  * `consultations_consultation`: INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `CONSULTATION_DRAFT_SAVED`, Level: `INFO`, Description: `Draft saved for appointment.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: HTML-sanitize all text areas to prevent XSS injection.
* **Performance Considerations**: Fast insert.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinical Consultation`
  * Operation ID: `create_consultation`

---

### 9.3 Complete Consultation
* **API Name**: Complete Consultation
* **Module**: Clinical Consultation
* **Purpose**: Locks the consultation record, making it read-only.
* **Business Context**: Concludes the clinical session, updating the treatment case and finalizing the billing/reporting state.
* **Endpoint**: `/api/v1/consultations/{consultation_id}/complete/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (must be the assigned doctor)
* **Preconditions**:
  * Consultation must exist in `DRAFT` status.
  * Diagnosis and treatment notes must be filled.
* **Business Rules**:
  * Once completed, the consultation cannot be edited or deleted.
* **State Transition Rules**:
  * Consultation: `DRAFT` $\rightarrow$ `COMPLETED`
  * Parent Appointment: `IN_CONSULTATION` $\rightarrow$ `COMPLETED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `consultation_id` (UUID, Required) - ID of the consultation.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  POST /api/v1/consultations/e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e/complete/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Retrieve consultation and verify doctor ownership.
  2. Verify all mandatory clinical fields are populated.
  3. Start database transaction.
  4. Update consultation status to `COMPLETED`.
  5. Update parent appointment status to `COMPLETED`.
  6. Update associated `TreatmentCase` primary diagnosis.
  7. Generate Patient Timeline and Appointment Timeline entries.
  8. Commit transaction.
  9. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Consultation finalized and locked."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: Triggers follow-up scheduling window.
* **Database Changes**:
  * `consultations_consultation`: UPDATE (status = 'COMPLETED')
  * `consultations_appointments`: UPDATE (status = 'COMPLETED')
  * `consultations_treatment_cases`: UPDATE (primary_diagnosis updated)
* **Timeline Entries Generated**:
  * Patient Timeline: `CONSULTATION_COMPLETED`
* **Activity Logs Generated**:
  * Action: `CONSULTATION_FINALIZED`, Level: `INFO`, Description: `Consultation completed.`
* **Audit Logs Generated**:
  * Table: `consultations_consultation`, Action: `LOCK_RECORD`, ID: `e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restricts subsequent updates. Enforces data locking.
* **Performance Considerations**: Transaction wrapping ensures atomic completion.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Clinical Consultation`
  * Operation ID: `complete_consultation`

---

## 10. Follow-up & Case Management Module

### 10.1 Record Follow-up Decision
* **API Name**: Record Follow-up Decision
* **Module**: Follow-up & Case Management
* **Purpose**: Records whether the patient requires follow-up care.
* **Business Context**: Helps manage the patient's care pathway post-consultation.
* **Endpoint**: `/api/v1/consultations/{consultation_id}/follow-up-decision/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (assigned)
* **Preconditions**:
  * Consultation must be in `COMPLETED` status.
* **Business Rules**:
  * If `requires_followup` is true, the `TreatmentCase` transitions to `FOLLOW_UP_REQUIRED`.
  * If false, the `TreatmentCase` transitions to `FOLLOW_UP_COMPLETED` (or remains active if other cases are open).
* **State Transition Rules**:
  * `TreatmentCase`: `ACTIVE` $\rightarrow$ `FOLLOW_UP_REQUIRED` or `FOLLOW_UP_COMPLETED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `consultation_id` (UUID, Required) - Consultation ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "requires_followup": true
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `requires_followup` | Boolean | Yes | - | Indicates if follow-up is needed. |
* **Example Request**:
  ```http
  POST /api/v1/consultations/e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e/follow-up-decision/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "requires_followup": true
  }
  ```
* **Processing Workflow**:
  1. Retrieve completed consultation.
  2. Get associated `TreatmentCase`.
  3. If `requires_followup` is true, set status to `FOLLOW_UP_REQUIRED`. Else, set to `FOLLOW_UP_COMPLETED`.
  4. Save `TreatmentCase`.
  5. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Follow-up decision recorded."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: Affects treatment journey tracking.
* **Database Changes**:
  * `consultations_treatment_cases`: UPDATE (status)
* **Timeline Entries Generated**:
  * Patient Timeline: `FOLLOWUP_DECISION_RECORDED`
* **Activity Logs Generated**:
  * Action: `FOLLOWUP_DECISION_RECORDED`, Level: `INFO`, Description: `Recorded follow-up decision.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Enforce doctor ownership.
* **Performance Considerations**: Fast update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `record_followup_decision`

---

### 10.2 Create Follow-up
* **API Name**: Create Follow-up
* **Module**: Follow-up & Case Management
* **Purpose**: Schedules a confirmed follow-up appointment directly, bypassing receptionist approval.
* **Business Context**: Used by doctors during consultation to book the next session immediately.
* **Endpoint**: `/api/v1/followups/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (assigned)
* **Preconditions**:
  * The previous consultation must be in `COMPLETED` status.
  * Target slot must be available.
* **Business Rules**:
  * Directly creates a `CONFIRMED` appointment.
  * Must comply with slot availability engine (doctor working hours, leaves, holidays).
* **State Transition Rules**:
  * `TreatmentCase`: `FOLLOW_UP_REQUIRED` $\rightarrow$ `FOLLOW_UP_SCHEDULED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "consultation_id": "e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
    "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
    "followup_date": "2026-07-28",
    "start_time": "11:30",
    "reason": "Routine speech review"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `consultation_id` | UUID | Yes | Must exist, COMPLETED | Previous consultation. |
  | `doctor_id` | UUID | Yes | Active doctor | Target doctor. |
  | `followup_date` | Date | Yes | YYYY-MM-DD, future | Date. |
  | `start_time` | String | Yes | HH:MM | Start time. |
  | `reason` | String | No | Max 250 chars | Reason. |
* **Example Request**:
  ```http
  POST /api/v1/followups/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "consultation_id": "e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
    "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
    "followup_date": "2026-07-28",
    "start_time": "11:30"
  }
  ```
* **Processing Workflow**:
  1. Validate doctor authorization.
  2. Verify previous consultation is completed.
  3. Validate slot availability for `followup_date` and `start_time`.
  4. Start database transaction.
  5. Insert new appointment record with status `CONFIRMED` and type `FOLLOW_UP`.
  6. Update associated `TreatmentCase` status to `FOLLOW_UP_SCHEDULED`.
  7. Generate timeline entries.
  8. Commit transaction.
  9. Dispatch booking notifications.
  10. Return `201 Created`.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Follow-up appointment created successfully.",
      "data": {
        "id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
        "appointment_number": "APT-FOLLOWUP-9F2B8D",
        "status": "CONFIRMED",
        "appointment_type": "FOLLOW_UP"
      }
    }
    ```
* **Response Field Documentation**: Same as standard appointment.
* **Side Effects**: Directly books a slot, bypassing review queue.
* **Database Changes**:
  * `consultations_appointments`: INSERT
  * `consultations_treatment_cases`: UPDATE (status = 'FOLLOW_UP_SCHEDULED')
* **Timeline Entries Generated**:
  * Patient Timeline: `FOLLOWUP_SCHEDULED`
* **Activity Logs Generated**:
  * Action: `FOLLOWUP_CREATED`, Level: `INFO`, Description: `Follow-up appointment booked.`
* **Audit Logs Generated**:
  * Table: `consultations_appointments`, Action: `CREATE_FOLLOWUP`, Payload: `{consultation_id: e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e}`
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_confirmed` (SMS/Email to parent).
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Strict authorization checks.
* **Performance Considerations**: Uses transaction locks on the target slot.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `create_followup`

---

### 10.3 Update Follow-up
* **API Name**: Update Follow-up
* **Module**: Follow-up & Case Management
* **Purpose**: Modifies or reschedules an existing follow-up appointment.
* **Business Context**: Used by doctors or staff to adjust follow-up dates/times.
* **Endpoint**: `/api/v1/followups/{appointment_id}/`
* **HTTP Method**: `PATCH`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `DOCTOR`
* **Preconditions**:
  * Appointment must exist and be of type `FOLLOW_UP`.
* **Business Rules**:
  * Re-runs slot validation on date/time change.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `appointment_id` (UUID, Required) - Appointment ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "appointment_date": "2026-08-10",
    "start_time": "11:30:00"
  }
  ```
* **Field-by-Field Validation Rules**: Same as standard edit.
* **Example Request**:
  ```http
  PATCH /api/v1/followups/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "appointment_date": "2026-08-10"
  }
  ```
* **Processing Workflow**: Same as `PATCH /api/v1/appointments/{id}/`.
* **Success Response**: Same as standard edit.
* **Response Field Documentation**: Same as standard edit.
* **Side Effects**: Dispatches rescheduling notification.
* **Database Changes**:
  * `consultations_appointments`: UPDATE
* **Timeline Entries Generated**:
  * Patient Timeline: `FOLLOWUP_RESCHEDULED`
* **Activity Logs Generated**:
  * Action: `FOLLOWUP_UPDATED`, Level: `INFO`, Description: `Follow-up rescheduled.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_rescheduled`.
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Access restricted to doctor or admin.
* **Performance Considerations**: Fast update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `update_followup`

---

### 10.4 Cancel Follow-up
* **API Name**: Cancel Follow-up
* **Module**: Follow-up & Case Management
* **Purpose**: Cancels a scheduled follow-up appointment.
* **Business Context**: Handles patient cancellations for follow-up appointments.
* **Endpoint**: `/api/v1/followups/{appointment_id}/cancel/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**:
  * Appointment must be in `CONFIRMED` status.
* **Business Rules**:
  * Reverts the associated `TreatmentCase` status to `FOLLOW_UP_REQUIRED` if no other future appointments exist.
* **State Transition Rules**:
  * Appointment: `CONFIRMED` $\rightarrow$ `CANCELLED`
  * `TreatmentCase`: `FOLLOW_UP_SCHEDULED` $\rightarrow$ `FOLLOW_UP_REQUIRED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `appointment_id` (UUID, Required) - Appointment ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "reason": "Family moving out of city."
  }
  ```
* **Field-by-Field Validation Rules**: Same as standard cancel.
* **Example Request**:
  ```http
  POST /api/v1/followups/fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f/cancel/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "reason": "Family moving out of city."
  }
  ```
* **Processing Workflow**:
  1. Retrieve follow-up appointment.
  2. Start database transaction.
  3. Update status to `CANCELLED`.
  4. Check if there are other future scheduled appointments for the patient.
  5. If none, update `TreatmentCase` status to `FOLLOW_UP_REQUIRED`.
  6. Generate timeline entries.
  7. Commit transaction.
  8. Return success.
* **Success Response**: Same as standard cancel.
* **Response Field Documentation**: Same as standard cancel.
* **Side Effects**: Releases slot, reverts case status.
* **Database Changes**:
  * `consultations_appointments`: UPDATE (status = 'CANCELLED')
  * `consultations_treatment_cases`: UPDATE (status)
* **Timeline Entries Generated**:
  * Patient Timeline: `FOLLOWUP_CANCELLED`
* **Activity Logs Generated**:
  * Action: `FOLLOWUP_CANCELLED`, Level: `WARNING`, Description: `Follow-up cancelled.`
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**:
  * Event: `appointment_cancelled`.
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Role authorization.
* **Performance Considerations**: Transaction wrapping.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `cancel_followup`

---

### 10.5 Get Patient Treatment Journey
* **API Name**: Get Patient Treatment Journey
* **Module**: Follow-up & Case Management
* **Purpose**: Retrieves the chronological journey of all cases, consultations, and appointments.
* **Business Context**: Provides clinical summary of the patient's entire treatment course.
* **Endpoint**: `/api/v1/treatment-cases/{patient_id}/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**:
  * Patient must exist.
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `patient_id` (UUID, Required) - Patient ID.
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/treatment-cases/9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Verify authentication.
  2. Query `consultations_treatment_cases` for the patient.
  3. Join consultations and appointments associated with each case.
  4. Return structured journey object.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Treatment journey retrieved.",
      "data": {
        "patient_id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
        "cases": [
          {
            "id": "8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f",
            "status": "ACTIVE",
            "primary_diagnosis": "Expressive Language Disorder",
            "start_date": "2026-06-28",
            "end_date": null,
            "consultations": [
              {
                "id": "e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
                "diagnosis": "Expressive Language Disorder",
                "completed_at": "2026-06-28T11:00:00Z"
              }
            ]
          }
        ]
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.cases` | Array | List of treatment cases with nested consultations. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**:
  * Action: `ACCESS_TREATMENT_JOURNEY`, Target: `9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Access logs recorded due to HIPAA/clinical audit requirements.
* **Performance Considerations**:
  * Uses `prefetch_related` on consultations and appointments.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `get_treatment_journey`

---

### 10.6 Close Treatment Case
* **API Name**: Close Treatment Case
* **Module**: Follow-up & Case Management
* **Purpose**: Marks a patient's active treatment case as closed.
* **Business Context**: Concludes the treatment lifecycle once objectives are achieved or patient is discharged.
* **Endpoint**: `/api/v1/treatment-cases/{patient_id}/close/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (must be the assigned doctor)
* **Preconditions**:
  * Case must be active.
  * Patient must exist.
* **Business Rules**:
  * Cannot close if there are pending consultations or future scheduled appointments.
* **State Transition Rules**:
  * `TreatmentCase`: `ACTIVE` or `FOLLOW_UP_SCHEDULED` $\rightarrow$ `CASE_CLOSED`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `patient_id` (UUID, Required) - Patient ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "closing_summary": "Patient has achieved age-appropriate speech clarity. Objectives met.",
    "outcome": "Treatment Completed"
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `closing_summary` | String | Yes | Max 1000 chars | Summary of outcome. |
  | `outcome` | String | Yes | Max 100 chars | Outcome classification. |
* **Example Request**:
  ```http
  POST /api/v1/treatment-cases/9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d/close/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "closing_summary": "Patient has achieved age-appropriate speech clarity.",
    "outcome": "Treatment Completed"
  }
  ```
* **Processing Workflow**:
  1. Retrieve active `TreatmentCase` for the patient.
  2. Verify no future scheduled appointments exist. If found, throw `422 Unprocessable Entity`.
  3. Start database transaction.
  4. Update case status to `CASE_CLOSED`, set `end_date` to today, and save summary/outcome.
  5. Generate timeline entry.
  6. Commit transaction.
  7. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Treatment case closed successfully."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: None
* **Database Changes**:
  * `consultations_treatment_cases`: UPDATE
* **Timeline Entries Generated**:
  * Patient Timeline: `TREATMENT_CASE_CLOSED`
* **Activity Logs Generated**:
  * Action: `TREATMENT_CASE_CLOSED`, Level: `WARNING`, Description: `Closed treatment case.`
* **Audit Logs Generated**:
  * Table: `consultations_treatment_cases`, Action: `CLOSE_CASE`, Payload: `{outcome: Treatment Completed}`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Restricted to assigned doctor.
* **Performance Considerations**: Fast single-row update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `close_treatment_case`

---

### 10.7 Reopen Treatment Case
* **API Name**: Reopen Treatment Case
* **Module**: Follow-up & Case Management
* **Purpose**: Reopens a closed treatment case.
* **Business Context**: Used if symptoms recur or a patient returns for further therapy after discharge.
* **Endpoint**: `/api/v1/treatment-cases/{patient_id}/reopen/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (assigned)
* **Preconditions**:
  * The treatment case must be in `CASE_CLOSED` status.
* **Business Rules**:
  * Requires a reason for reopening.
* **State Transition Rules**:
  * `TreatmentCase`: `CASE_CLOSED` $\rightarrow$ `ACTIVE`
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* **Path Parameters**:
  * `patient_id` (UUID, Required) - Patient ID.
* **Query Parameters**: None
* **Request Body**:
  ```json
  {
    "reason": "Patient showing mild regression in speech clarity."
  }
  ```
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `reason` | String | Yes | Max 500 chars | Reason for reopening. |
* **Example Request**:
  ```http
  POST /api/v1/treatment-cases/9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d/reopen/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: application/json

  {
    "reason": "Patient showing mild regression in speech clarity."
  }
  ```
* **Processing Workflow**:
  1. Retrieve the closed `TreatmentCase`.
  2. Start database transaction.
  3. Update status to `ACTIVE`, clear `end_date`, and save `reopen_reason`.
  4. Generate timeline entry.
  5. Commit transaction.
  6. Return success.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Treatment case reopened successfully."
    }
    ```
* **Response Field Documentation**: Same as above.
* **Side Effects**: None
* **Database Changes**:
  * `consultations_treatment_cases`: UPDATE
* **Timeline Entries Generated**:
  * Patient Timeline: `TREATMENT_CASE_REOPENED`
* **Activity Logs Generated**:
  * Action: `TREATMENT_CASE_REOPENED`, Level: `WARNING`, Description: `Reopened case.`
* **Audit Logs Generated**:
  * Table: `consultations_treatment_cases`, Action: `REOPEN_CASE`, Payload: `{reason: regression}`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Doctor restricted.
* **Performance Considerations**: Fast update.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Follow-up & Case Management`
  * Operation ID: `reopen_treatment_case`

---

## 11. File Uploads Module

### 11.1 Upload Consultation Document
* **API Name**: Upload Consultation Document
* **Module**: File Uploads
* **Purpose**: Uploads supporting medical documents during a consultation.
* **Business Context**: Allows doctors to attach lab reports, school assessments, or prescriptions to the patient's record.
* **Endpoint**: `/api/v1/consultations/{consultation_id}/attachments/`
* **HTTP Method**: `POST`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `DOCTOR` (assigned)
* **Preconditions**:
  * Consultation must exist.
* **Business Rules**:
  * Maximum file size: **10MB**.
  * Allowed MIME Types: `application/pdf`, `image/jpeg`, `image/png`.
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
  * `Content-Type: multipart/form-data`
* **Path Parameters**:
  * `consultation_id` (UUID, Required) - ID of the consultation.
* **Query Parameters**: None
* **Request Body**: Multipart Form-Data
  * `file`: Binary File
  * `description`: String (Optional)
* **Field-by-Field Validation Rules**:
  | Field | Type | Required | Validation | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `file` | File | Yes | Max 10MB, PDF/JPEG/PNG | File payload. |
  | `description` | String | No | Max 200 chars | Brief description. |
* **Example Request**:
  ```http
  POST /api/v1/consultations/e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e/attachments/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="file"; filename="report.pdf"
  Content-Type: application/pdf

  (binary data)
  ------WebKitFormBoundary7MA4YWxkTrZu0gW
  Content-Disposition: form-data; name="description"

  School Speech Assessment
  ------WebKitFormBoundary7MA4YWxkTrZu0gW--
  ```
* **Processing Workflow**:
  1. Validate doctor permissions.
  2. Parse multipart form. Extract file.
  3. Validate file size (< 10MB) and MIME type.
  4. Stream file to secure Amazon S3 bucket.
  5. Generate S3 object key and public/private URL.
  6. Save record in `consultations_consultation_attachment`.
  7. Return details.
* **Success Response**:
  * **HTTP Status**: `201 Created`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "File uploaded successfully.",
      "data": {
        "id": "e2f3a4b5-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
        "file_name": "report.pdf",
        "file_url": "https://s3.amazonaws.com/neuro-blooms-docs/report.pdf",
        "uploaded_at": "2026-06-28T08:15:00Z"
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.id` | UUID | Unique ID of attachment. |
  | `data.file_url` | String | Presigned URL to download the file. |
* **Side Effects**: Streams file to S3.
* **Database Changes**:
  * `consultations_consultation_attachment`: INSERT
* **Timeline Entries Generated**: None
* **Activity Logs Generated**:
  * Action: `FILE_UPLOADED`, Level: `INFO`, Description: `Uploaded report.pdf.`
* **Audit Logs Generated**:
  * Table: `consultations_consultation_attachment`, Action: `UPLOAD`, Payload: `{file_name: report.pdf}`
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**:
  * Protect bucket with strict IAM policies. Presigned URLs must expire in 15 minutes.
* **Performance Considerations**:
  * Stream uploads directly to S3 without keeping the entire file in web server memory.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `File Uploads`
  * Operation ID: `upload_consultation_document`

---

## 12. Timeline Module

### 12.1 Get Patient Timeline
* **API Name**: Get Patient Timeline
* **Module**: Timeline
* **Purpose**: Retrieves a chronological list of all events related to a patient.
* **Business Context**: Displays the patient's administrative and clinical history.
* **Endpoint**: `/api/v1/patients/{patient_id}/timeline/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`, `DOCTOR`
* **Preconditions**:
  * Patient must exist.
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**:
  * `patient_id` (UUID, Required) - Patient ID.
* **Query Parameters**:
  * `limit`, `offset` (Integer, Optional) - Pagination.
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/patients/9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d/timeline/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Authenticate user.
  2. Query `consultations_patient_timeline` table for `patient_id`.
  3. Return chronological list of events.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Timeline retrieved.",
      "data": {
        "count": 2,
        "results": [
          {
            "id": "t1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
            "event_type": "APPOINTMENT_CONFIRMED",
            "description": "Appointment APT-000001 confirmed.",
            "created_at": "2026-06-28T10:15:00Z"
          },
          {
            "id": "t2b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
            "event_type": "PATIENT_REGISTERED",
            "description": "Patient registered.",
            "created_at": "2026-06-28T10:10:00Z"
          }
        ]
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.results[].event_type` | String | Event classification. |
  | `data.results[].description` | String | Details of the event. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: Paginated by limit/offset. Sorted by `created_at` descending.
* **Security Notes**: Clinical event visibility restricted based on roles.
* **Performance Considerations**: Index on `patient_id` and `created_at` is utilized.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Timeline`
  * Operation ID: `get_patient_timeline`

---

## 13. Reports & Analytics Module

### 13.1 Get Clinic Daily Metrics
* **API Name**: Get Clinic Daily Metrics
* **Module**: Reports & Analytics
* **Purpose**: Retrieves aggregate counts of daily activities.
* **Business Context**: Displays operational summary on the receptionist dashboard.
* **Endpoint**: `/api/v1/reports/daily-metrics/`
* **HTTP Method**: `GET`
* **Authentication Requirements**: Bearer JWT Access Token
* **Authorization (Allowed Roles)**: `SUPER_ADMIN`, `ADMIN`, `RECEPTIONIST`
* **Preconditions**: None
* **Business Rules**: N/A
* **State Transition Rules**: N/A
* **Request Headers**:
  * `Authorization: Bearer <token>`
* **Path Parameters**: None
* **Query Parameters**: None
* **Request Body**: None
* **Field-by-Field Validation Rules**: N/A
* **Example Request**:
  ```http
  GET /api/v1/reports/daily-metrics/ HTTP/1.1
  Host: api.neuroblooms.com
  Authorization: Bearer eyJ...
  ```
* **Processing Workflow**:
  1. Validate permissions.
  2. Query counts for today's appointment requests and appointments in various states.
  3. Compile and return.
* **Success Response**:
  * **HTTP Status**: `200 OK`
  * **Body**:
    ```json
    {
      "success": true,
      "message": "Daily metrics retrieved.",
      "data": {
        "pending_requests": 8,
        "confirmed_appointments": 14,
        "checked_in_patients": 3,
        "completed_consultations": 5
      }
    }
    ```
* **Response Field Documentation**:
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `data.pending_requests` | Integer | Total requests pending. |
  | `data.confirmed_appointments` | Integer | Confirmed bookings today. |
* **Side Effects**: None
* **Database Changes**: None
* **Timeline Entries Generated**: None
* **Activity Logs Generated**: None
* **Audit Logs Generated**: None
* **Notification Events Triggered (Current/Future)**: None
* **Pagination, Filtering & Sorting**: N/A
* **Security Notes**: Staff restricted.
* **Performance Considerations**:
  * Queries are optimized to run on indexed date fields.
* **Swagger/OpenAPI Documentation Notes**:
  * Tag: `Reports & Analytics`
  * Operation ID: `get_daily_metrics`

---

## 14. Comprehensive Error Responses Section

This section documents all system failure scenarios. The Neuro Blooms API utilizes a standardized error envelope format for all failures:

```json
{
  "success": false,
  "message": "Human-readable error summary.",
  "errors": {
    "error_code": "ERR_XXX",
    "title": "Error Title",
    "detail": "Detailed root cause analysis.",
    "fields": {
      "field_name": ["Specific validation error message."]
    }
  }
}
```

---

### 14.1 Request Validation Errors
* **HTTP Status Code**: `400 Bad Request`
* **Internal Error Code**: `ERR_VAL_001`
* **Error Title**: `Validation Failed`
* **Human-readable Error Message**: `One or more fields in the request body failed validation.`
* **Root Cause**: The client sent data that violates field constraints (e.g., malformed email, missing required fields).
* **Trigger Condition**: Input payload does not match serializer schema validation rules.
* **Suggested Client Action**: Inspect the `fields` object in the response, correct the inputs, and resubmit.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Input validation failed.",
    "errors": {
      "error_code": "ERR_VAL_001",
      "title": "Validation Failed",
      "detail": "Provided request parameters did not pass schema validation constraints.",
      "fields": {
        "parent_email": ["Enter a valid email address."]
      }
    }
  }
  ```

### 14.2 Authentication Failures
* **HTTP Status Code**: `401 Unauthorized`
* **Internal Error Code**: `ERR_AUTH_001`
* **Error Title**: `Authentication Failed`
* **Human-readable Error Message**: `Authentication credentials were not provided or are invalid.`
* **Root Cause**: Missing, expired, or malformed JWT token in the `Authorization` header.
* **Trigger Condition**: The `Authorization` header is absent or the signature verification fails.
* **Suggested Client Action**: Refresh the access token or redirect the user to the login page.
* **Retry Behaviour**: Do Not Retry (without re-authenticating)
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "errors": {
      "error_code": "ERR_AUTH_001",
      "title": "Authentication Failed",
      "detail": "The access token provided is invalid or has expired."
    }
  }
  ```

### 14.3 Authorization Failures / Invalid Permissions
* **HTTP Status Code**: `403 Forbidden`
* **Internal Error Code**: `ERR_AUTH_002`
* **Error Title**: `Permission Denied`
* **Human-readable Error Message**: `You do not have permission to perform this action.`
* **Root Cause**: The authenticated user lacks the required role or permission policy.
* **Trigger Condition**: A `RECEPTIONIST` tries to access a clinical endpoint, or a `DOCTOR` tries to access admin settings.
* **Suggested Client Action**: Request an administrator to elevate your role privileges.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Access denied.",
    "errors": {
      "error_code": "ERR_AUTH_002",
      "title": "Permission Denied",
      "detail": "Your current roles [RECEPTIONIST] do not grant permission to execute this operation."
    }
  }
  ```

### 14.4 Missing Resources
* **HTTP Status Code**: `404 Not Found`
* **Internal Error Code**: `ERR_RES_001`
* **Error Title**: `Resource Not Found`
* **Human-readable Error Message**: `The requested resource could not be found.`
* **Root Cause**: The UUID provided in the path does not correspond to any active database record.
* **Trigger Condition**: Querying a patient or appointment that does not exist.
* **Suggested Client Action**: Check the ID parameter and verify the resource exists.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Resource not found.",
    "errors": {
      "error_code": "ERR_RES_001",
      "title": "Resource Not Found",
      "detail": "No patient record exists with the ID 9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d."
    }
  }
  ```

### 14.5 Duplicate Resources
* **HTTP Status Code**: `409 Conflict`
* **Internal Error Code**: `ERR_RES_002`
* **Error Title**: `Duplicate Record`
* **Human-readable Error Message**: `A record with these details already exists.`
* **Root Cause**: Violates unique database constraints (e.g. unique email or duplicate patient registration).
* **Trigger Condition**: Trying to create a user with an email that is already registered.
* **Suggested Client Action**: Use the existing record or change the unique identifier.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Conflict detected.",
    "errors": {
      "error_code": "ERR_RES_002",
      "title": "Duplicate Record",
      "detail": "A user with email doctor@neuroblooms.com is already registered in the system."
    }
  }
  ```

### 14.6 Scheduling Conflicts (General)
* **HTTP Status Code**: `409 Conflict`
* **Internal Error Code**: `ERR_SCH_001`
* **Error Title**: `Scheduling Conflict`
* **Human-readable Error Message**: `The requested time slot is not available.`
* **Root Cause**: The selected doctor is already booked, on leave, or the clinic is closed.
* **Trigger Condition**: Double-booking prevention check fails in the scheduling engine.
* **Suggested Client Action**: Fetch the doctor's available slots and select a different time.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "The selected slot is unavailable.",
    "errors": {
      "error_code": "ERR_SCH_001",
      "title": "Scheduling Conflict",
      "detail": "Dr. John Smith already has a confirmed appointment scheduled for 2026-06-28 from 10:30 to 11:00."
    }
  }
  ```

### 14.7 Business Rule Violations
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_BUS_001`
* **Error Title**: `Business Rule Violation`
* **Human-readable Error Message**: `The operation violates clinic policy or clinical workflows.`
* **Root Cause**: Request fails domain logic rules (e.g. attempting to book a slot outside clinic hours).
* **Trigger Condition**: Enforces business validation rules at the service layer.
* **Suggested Client Action**: Modify the request parameters to comply with clinic policy.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Operational policy violation.",
    "errors": {
      "error_code": "ERR_BUS_001",
      "title": "Business Rule Violation",
      "detail": "Clinic opening hours are from 09:00:00 to 17:00:00. The requested slot of 08:00:00 is invalid."
    }
  }
  ```

### 14.8 Invalid Workflow / State Transitions
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_BUS_002`
* **Error Title**: `Invalid State Transition`
* **Human-readable Error Message**: `Cannot transition the resource to the requested status.`
* **Root Cause**: Triggering an invalid status transition (e.g., checking in a completed appointment).
* **Trigger Condition**: Attempting to move from `COMPLETED` directly to `CHECKED_IN`.
* **Suggested Client Action**: Refresh the resource state and verify the permitted actions.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Workflow transition failed.",
    "errors": {
      "error_code": "ERR_BUS_002",
      "title": "Invalid State Transition",
      "detail": "Cannot transition appointment from state [COMPLETED] to [CHECKED_IN]."
    }
  }
  ```

### 14.9 Ownership Violations
* **HTTP Status Code**: `403 Forbidden`
* **Internal Error Code**: `ERR_AUTH_003`
* **Error Title**: `Ownership Violation`
* **Human-readable Error Message**: `You do not own this resource.`
* **Root Cause**: A doctor attempting to update or access another doctor's consultation or availability settings.
* **Trigger Condition**: Requester ID does not match the owner ID in the resource record.
* **Suggested Client Action**: Verify your resource ownership.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Access denied.",
    "errors": {
      "error_code": "ERR_AUTH_003",
      "title": "Ownership Violation",
      "detail": "You do not have permission to modify the availability settings for doctor ID d3b07384-d113-4956-a5d8-472d7d56637e."
    }
  }
  ```

### 14.10 Soft-Deleted Resources
* **HTTP Status Code**: `404 Not Found`
* **Internal Error Code**: `ERR_RES_003`
* **Error Title**: `Resource Deleted`
* **Human-readable Error Message**: `The requested resource has been deleted.`
* **Root Cause**: The resource has `is_deleted = True` and is filtered out of standard queries.
* **Trigger Condition**: Fetching an attachment or record that was soft-deleted.
* **Suggested Client Action**: Verify the resource status.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Resource unavailable.",
    "errors": {
      "error_code": "ERR_RES_003",
      "title": "Resource Deleted",
      "detail": "The requested attachment has been removed by the administrator."
    }
  }
  ```

### 14.11 Concurrency Conflicts / Optimistic Locking Failures
* **HTTP Status Code**: `409 Conflict`
* **Internal Error Code**: `ERR_CON_001`
* **Error Title**: `Concurrency Conflict`
* **Human-readable Error Message**: `The resource was modified by another user. Please reload and try again.`
* **Root Cause**: The record's version or updated timestamp changed between fetch and save.
* **Trigger Condition**: Version mismatch check during update.
* **Suggested Client Action**: Reload the resource, apply changes to the fresh record, and save.
* **Retry Behaviour**: Retry (after fetching latest state)
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Update conflict.",
    "errors": {
      "error_code": "ERR_CON_001",
      "title": "Concurrency Conflict",
      "detail": "The appointment record was updated by another process. Please refresh the page and re-apply changes."
    }
  }
  ```

### 14.12 Database Constraint Violations
* **HTTP Status Code**: `500 Internal Server Error`
* **Internal Error Code**: `ERR_DB_001`
* **Error Title**: `Integrity Error`
* **Human-readable Error Message**: `A database error occurred while processing the request.`
* **Root Cause**: Violates database schema integrity constraints (e.g. foreign key constraint failed).
* **Trigger Condition**: Attempting to delete a patient who has active appointments (protected by `models.PROTECT`).
* **Suggested Client Action**: Contact system support.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Database integrity violation.",
    "errors": {
      "error_code": "ERR_DB_001",
      "title": "Integrity Error",
      "detail": "Cannot delete the patient record because active appointments are linked to it."
    }
  }
  ```

### 14.13 File Upload Validation Failures (Unsupported Types)
* **HTTP Status Code**: `400 Bad Request`
* **Internal Error Code**: `ERR_FIL_001`
* **Error Title**: `Unsupported File Type`
* **Human-readable Error Message**: `The uploaded file type is not supported.`
* **Root Cause**: The file extension or MIME type is not in the allowed list (PDF, JPEG, PNG).
* **Trigger Condition**: Uploading an executable (.exe) or text file.
* **Suggested Client Action**: Convert the file to PDF, JPEG, or PNG and try again.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Invalid file format.",
    "errors": {
      "error_code": "ERR_FIL_001",
      "title": "Unsupported File Type",
      "detail": "Uploaded file MIME type [application/x-msdownload] is not supported. Only PDF, JPEG, and PNG are allowed."
    }
  }
  ```

### 14.14 Maximum File Size Exceeded
* **HTTP Status Code**: `413 Payload Too Large`
* **Internal Error Code**: `ERR_FIL_002`
* **Error Title**: `File Too Large`
* **Human-readable Error Message**: `The uploaded file exceeds the maximum size limit of 10MB.`
* **Root Cause**: File payload size exceeds the server's configured limit.
* **Trigger Condition**: File size check fails during multipart parsing.
* **Suggested Client Action**: Compress the document/image and re-upload.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Upload size limit exceeded.",
    "errors": {
      "error_code": "ERR_FIL_002",
      "title": "File Too Large",
      "detail": "The uploaded file size is 15.4 MB, which exceeds the limit of 10.0 MB."
    }
  }
  ```

### 14.15 Duplicate Booking Attempts
* **HTTP Status Code**: `409 Conflict`
* **Internal Error Code**: `ERR_SCH_002`
* **Error Title**: `Duplicate Booking`
* **Human-readable Error Message**: `An appointment is already scheduled for this patient at the same time.`
* **Root Cause**: Attempting to schedule two concurrent appointments for the same patient.
* **Trigger Condition**: Scheduling engine detects patient time overlap.
* **Suggested Client Action**: Choose a different time slot or cancel the existing booking.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Patient double-booking prevented.",
    "errors": {
      "error_code": "ERR_SCH_002",
      "title": "Duplicate Booking",
      "detail": "Tommy Helper already has an appointment confirmed on 2026-06-28 from 10:30 to 11:00."
    }
  }
  ```

### 14.16 Doctor Availability Conflicts
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_003`
* **Error Title**: `Doctor Unavailable`
* **Human-readable Error Message**: `The doctor is not accepting appointments on the selected day.`
* **Root Cause**: The doctor has disabled their availability (`accepts_appointments = False`).
* **Trigger Condition**: Booking validation checks the doctor's preference flags.
* **Suggested Client Action**: Select another doctor or wait until their status is active.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Doctor scheduling is disabled.",
    "errors": {
      "error_code": "ERR_SCH_003",
      "title": "Doctor Unavailable",
      "detail": "Dr. John Smith is currently not accepting new appointments."
    }
  }
  ```

### 14.17 Holiday Conflicts
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_004`
* **Error Title**: `Clinic Holiday`
* **Human-readable Error Message**: `The clinic is closed on the selected date due to a holiday.`
* **Root Cause**: The date matches a registered clinic holiday in `consultations_clinic_holiday`.
* **Trigger Condition**: Scheduling engine detects holiday date match.
* **Suggested Client Action**: Choose another business day.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Clinic closed.",
    "errors": {
      "error_code": "ERR_SCH_004",
      "title": "Clinic Holiday",
      "detail": "2027-01-01 is a registered holiday: New Year Day."
    }
  }
  ```

### 14.18 Leave Conflicts
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_005`
* **Error Title**: `Doctor On Leave`
* **Human-readable Error Message**: `The selected doctor is on leave during this period.`
* **Root Cause**: The date falls within the doctor's approved leave range.
* **Trigger Condition**: Scheduling engine detects leave date match.
* **Suggested Client Action**: Select a different date or book with another doctor.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Doctor is unavailable.",
    "errors": {
      "error_code": "ERR_SCH_005",
      "title": "Doctor On Leave",
      "detail": "Dr. John Smith is on leave from 2026-07-10 to 2026-07-12."
    }
  }
  ```

### 14.19 Blocked Slot Conflicts
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_006`
* **Error Title**: `Time Slot Blocked`
* **Human-readable Error Message**: `The requested time slot has been blocked by the doctor.`
* **Root Cause**: The slot overlaps with a registered doctor blocked slot.
* **Trigger Condition**: Scheduling engine detects blocked slot overlap.
* **Suggested Client Action**: Select a different time slot.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Time slot blocked.",
    "errors": {
      "error_code": "ERR_SCH_006",
      "title": "Time Slot Blocked",
      "detail": "The time slot 12:00 to 13:00 on 2026-06-30 is blocked: Staff meeting."
    }
  }
  ```

### 14.20 Booking Window Violations
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_007`
* **Error Title**: `Booking Window Violation`
* **Human-readable Error Message**: `Appointments can only be booked within the allowed window.`
* **Root Cause**: The requested date is further in the future than allowed by clinic settings.
* **Trigger Condition**: Booking date exceeds the current date plus `booking_window_days`.
* **Suggested Client Action**: Select a date closer to the present.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Invalid booking date.",
    "errors": {
      "error_code": "ERR_SCH_007",
      "title": "Booking Window Violation",
      "detail": "Appointments can only be booked up to 30 days in advance. The selected date 2026-09-15 is out of bounds."
    }
  }
  ```

### 14.21 Same-Day Booking Restrictions
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_008`
* **Error Title**: `Same-Day Booking Restricted`
* **Human-readable Error Message**: `Same-day appointments are not allowed.`
* **Root Cause**: Clinic settings have `allow_same_day_booking = False`, and the request is for the current date.
* **Trigger Condition**: Booking date matches the current local date.
* **Suggested Client Action**: Schedule the appointment for tomorrow or a later date.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Booking restricted.",
    "errors": {
      "error_code": "ERR_SCH_008",
      "title": "Same-Day Booking Restricted",
      "detail": "The clinic does not allow booking appointments for the same day. Please select a future date."
    }
  }
  ```

### 14.22 Maximum Appointment Limits
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_SCH_009`
* **Error Title**: `Daily Capacity Reached`
* **Human-readable Error Message**: `The clinic or doctor has reached the maximum daily appointment limit.`
* **Root Cause**: Daily booking count matches the limit set in clinic settings or doctor availability.
* **Trigger Condition**: Total active appointments for the day equal the capacity cap.
* **Suggested Client Action**: Choose another date.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Capacity exceeded.",
    "errors": {
      "error_code": "ERR_SCH_009",
      "title": "Daily Capacity Reached",
      "detail": "Dr. John Smith has reached the daily capacity limit of 10 patients for 2026-06-28."
    }
  }
  ```

### 14.23 Treatment Case Restrictions
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_CAS_001`
* **Error Title**: `Case Closure Restricted`
* **Human-readable Error Message**: `Cannot close the treatment case while there are pending actions.`
* **Root Cause**: The case has active future appointments or incomplete consultations.
* **Trigger Condition**: Attempting to close a case that has scheduling dependencies.
* **Suggested Client Action**: Complete or cancel all pending appointments before closing.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Cannot close treatment case.",
    "errors": {
      "error_code": "ERR_CAS_001",
      "title": "Case Closure Restricted",
      "detail": "The treatment case cannot be closed because there is a future scheduled follow-up appointment on 2026-07-28."
    }
  }
  ```

### 14.24 Follow-up Restrictions
* **HTTP Status Code**: `422 Unprocessable Entity`
* **Internal Error Code**: `ERR_CAS_002`
* **Error Title**: `Follow-up Restricted`
* **Human-readable Error Message**: `Cannot schedule a follow-up without a completed consultation.`
* **Root Cause**: The preceding consultation has not been locked or completed.
* **Trigger Condition**: The consultation ID provided is in `DRAFT` status.
* **Suggested Client Action**: Finalize and complete the consultation draft before booking the follow-up.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Follow-up booking blocked.",
    "errors": {
      "error_code": "ERR_CAS_002",
      "title": "Follow-up Restricted",
      "detail": "The previous consultation (ID e2b3c4d5-f6a7-8b9c-0d1e-2f3a4b5c6d7e) must be completed before booking a follow-up."
    }
  }
  ```

### 14.25 Timeline Generation Failures
* **HTTP Status Code**: `500 Internal Server Error`
* **Internal Error Code**: `ERR_SYS_001`
* **Error Title**: `Timeline Write Failed`
* **Human-readable Error Message**: `An error occurred while updating the patient history timeline.`
* **Root Cause**: System failed to write event details to the timeline table.
* **Trigger Condition**: Database write error during timeline save.
* **Suggested Client Action**: Contact system support.
* **Retry Behaviour**: Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "System error occurred.",
    "errors": {
      "error_code": "ERR_SYS_001",
      "title": "Timeline Write Failed",
      "detail": "Failed to write event [APPOINTMENT_CONFIRMED] to patient timeline due to a database write timeout."
    }
  }
  ```

### 14.26 Activity Log Failures
* **HTTP Status Code**: `500 Internal Server Error`
* **Internal Error Code**: `ERR_SYS_002`
* **Error Title**: `Activity Logging Failed`
* **Human-readable Error Message**: `An error occurred while logging the user activity.`
* **Root Cause**: Database or service failure in writing to the activity logs.
* **Trigger Condition**: Write error on the activity log service.
* **Suggested Client Action**: Contact system support.
* **Retry Behaviour**: Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Logging system error.",
    "errors": {
      "error_code": "ERR_SYS_002",
      "title": "Activity Logging Failed",
      "detail": "Failed to persist activity log for action USER_LOGIN."
    }
  }
  ```

### 14.27 External Storage Failures
* **HTTP Status Code**: `503 Service Unavailable`
* **Internal Error Code**: `ERR_EXT_001`
* **Error Title**: `Storage Service Unavailable`
* **Human-readable Error Message**: `The file storage service is currently unreachable. Please try again later.`
* **Root Cause**: Amazon S3 returned a connection timeout or credential error.
* **Trigger Condition**: File upload fails to establish connection with S3.
* **Suggested Client Action**: Wait a few moments and attempt the upload again.
* **Retry Behaviour**: Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "External service failure.",
    "errors": {
      "error_code": "ERR_EXT_001",
      "title": "Storage Service Unavailable",
      "detail": "The backend was unable to upload the attachment to S3 due to a service timeout."
    }
  }
  ```

### 14.28 Internal Server Errors
* **HTTP Status Code**: `500 Internal Server Error`
* **Internal Error Code**: `ERR_SYS_000`
* **Error Title**: `Internal Server Error`
* **Human-readable Error Message**: `An unexpected error occurred on the server.`
* **Root Cause**: Unhandled exception in the application code.
* **Trigger Condition**: Null pointer exceptions, unhandled runtime errors.
* **Suggested Client Action**: Report the error to the technical support team.
* **Retry Behaviour**: Do Not Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Internal server error.",
    "errors": {
      "error_code": "ERR_SYS_000",
      "title": "Internal Server Error",
      "detail": "An unhandled exception occurred: KeyError: 'user_id' in session validation."
    }
  }
  ```

### 14.29 Temporary Service Unavailability
* **HTTP Status Code**: `503 Service Unavailable`
* **Internal Error Code**: `ERR_SYS_503`
* **Error Title**: `Service Unavailable`
* **Human-readable Error Message**: `The server is temporarily unable to handle the request.`
* **Root Cause**: Server is overloaded or down for maintenance.
* **Trigger Condition**: High CPU/Memory usage, or database connection pool exhaustion.
* **Suggested Client Action**: Retry the request after a few minutes.
* **Retry Behaviour**: Retry
* **Example JSON Response**:
  ```json
  {
    "success": false,
    "message": "Service temporarily unavailable.",
    "errors": {
      "error_code": "ERR_SYS_503",
      "title": "Service Unavailable",
      "detail": "The database connection pool has been exhausted. Please retry in a few minutes."
    }
  }
  ```
