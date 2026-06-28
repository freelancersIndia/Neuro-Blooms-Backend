# Neuro Blooms Hospital Management System - Backend API Reference

This document serves as the official **API Contract** between the Frontend, Backend, and QA teams for the **Neuro Blooms Hospital Management System**. It contains detailed specifications for all endpoints, including authentication, permissions, business rules, parameters, request/response payloads, error handling, state transitions, and side effects.

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [User & Role Management](#2-user--role-management)
3. [Clinic Management](#3-clinic-management)
4. [Doctor Scheduling](#4-doctor-scheduling)
5. [Appointment Requests](#5-appointment-requests)
6. [Patient Matching](#6-patient-matching)
7. [Patient Management](#7-patient-management)
8. [Appointment Management](#8-appointment-management)
9. [Clinical Consultation](#9-clinical-consultation)
10. [Follow-up & Case Management](#10-follow-up--case-management)
11. [File Uploads](#11-file-uploads)
12. [Timeline](#12-timeline)
13. [Reports & Analytics](#13-reports--analytics)
14. [Notifications](#14-notifications)
15. [Common Responses & Error Envelopes](#15-common-responses--error-envelopes)
16. [Security & Performance Notes](#16-security--performance-notes)

---

## 1. Authentication

### 1.1 User Login
- **Purpose**: Authenticates users (Admins, Receptionists, Doctors) and returns JWT tokens.
- **Endpoint**: `POST /api/v1/auth/login/`
- **Authentication**: Public
- **Permissions**: Anyone
- **Business Rules**:
  - Email must be a valid registered email.
  - Account must not be deactivated.
- **Request Headers**:
  - `Content-Type: application/json`
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `email` | String | Yes | Valid email format | The user's registered email address. |
  | `password` | String | Yes | Min 8 characters | The user's password. |
- **Example Request**:
  ```json
  {
    "email": "doctor@neuroblooms.com",
    "password": "Password123"
  }
  ```
- **Successful Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Login successful.",
    "data": {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
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
- **Response Fields**:
  | Field | Type | Description |
  | ----- | ---- | ----------- |
  | `access` | String | JWT access token (short-lived, 15 mins). |
  | `refresh` | String | JWT refresh token (long-lived, 7 days). |
  | `user` | Object | The authenticated user's profile details. |
- **Error Responses**:
  - **400 Bad Request**: Invalid email or password format.
  - **401 Unauthorized**: Invalid credentials, inactive account.
  - **429 Too Many Requests**: Rate limit exceeded (max 5 failed login attempts per IP per minute).
- **Idempotency**: Yes (safe to call multiple times).
- **Side Effects**: Creates an Activity Log entry for login attempt.

### 1.2 Token Refresh
- **Purpose**: Generates a new access token using a valid refresh token.
- **Endpoint**: `POST /api/v1/auth/token/refresh/`
- **Authentication**: Public (requires refresh token in body)
- **Permissions**: Anyone
- **Request Body**:
  | Field | Type | Required | Description |
  | ----- | ---- | -------- | ----------- |
  | `refresh` | String | Yes | The valid refresh token. |
- **Successful Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Token refreshed successfully.",
    "data": {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
  ```
- **Error Responses**:
  - **401 Unauthorized**: Refresh token is invalid, expired, or blacklisted.

### 1.3 User Logout
- **Purpose**: Blacklists the refresh token and logs out the user.
- **Endpoint**: `POST /api/v1/auth/logout/`
- **Authentication**: Required (Bearer Token)
- **Permissions**: IsAuthenticated
- **Request Body**:
  | Field | Type | Required | Description |
  | ----- | ---- | -------- | ----------- |
  | `refresh` | String | Yes | The refresh token to be blacklisted. |
- **Successful Response (204 No Content)**: (No body returned)

---

## 2. User & Role Management

### 2.1 Create User
- **Purpose**: Creates a new system user (Doctor, Receptionist, Admin) and associates their system roles.
- **Endpoint**: `POST /api/v1/admin/users/`
- **Authentication**: Required (Bearer Token)
- **Permissions**: Super Admin, Admin
- **Business Rules**:
  - Email must be unique.
  - Role must be a valid system role (`ADMIN`, `RECEPTIONIST`, `DOCTOR`).
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `email` | String | Yes | Unique email | User's email. |
  | `first_name` | String | Yes | Max 50 chars | User's first name. |
  | `last_name` | String | Yes | Max 50 chars | User's last name. |
  | `roles` | Array of Strings | Yes | Valid roles | List of roles (e.g., `["DOCTOR"]`). |
- **Successful Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "User created successfully.",
    "data": {
      "id": "e5b8a1c2-d3f4-4a5b-6c7d-8e9f0a1b2c3d",
      "email": "staff@neuroblooms.com",
      "first_name": "Sarah",
      "last_name": "Connor",
      "roles": ["RECEPTIONIST"],
      "is_active": true
    }
  }
  ```
- **Error Responses**:
  - **400 Bad Request**: Validation errors, duplicate email.
  - **403 Forbidden**: User lacks admin privileges.
- **Side Effects**: Generates default system preferences for the user (e.g., Doctor Availability if role is DOCTOR).

---

## 3. Clinic Management

### 3.1 Get Clinic Settings
- **Purpose**: Retrieves the global settings of the clinic.
- **Endpoint**: `GET /api/v1/admin/clinic/settings/`
- **Authentication**: Required (Bearer Token)
- **Permissions**: Super Admin, Admin, Receptionist, Doctor (Read-only)
- **Successful Response (200 OK)**:
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

### 3.2 Update Clinic Settings
- **Purpose**: Updates the global settings of the clinic.
- **Endpoint**: `PATCH /api/v1/admin/clinic/settings/`
- **Authentication**: Required (Bearer Token)
- **Permissions**: Super Admin, Admin
- **Business Rules**:
  - `opening_time` must be before `closing_time`.
  - `slot_duration_minutes` must be a positive integer (typically 15, 30, or 60).
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `clinic_name` | String | No | Max 100 chars | Name of the clinic. |
  | `opening_time` | String | No | HH:MM:SS | Daily opening hour. |
  | `closing_time` | String | No | HH:MM:SS | Daily closing hour. |
  | `slot_duration_minutes` | Integer | No | Min 10, Max 120 | Default duration of an appointment slot. |
  | `booking_window_days` | Integer | No | Min 1 | How many days in advance a slot can be booked. |
  | `allow_same_day_booking` | Boolean | No | - | Can patients book appointments on the same day. |
- **Successful Response (200 OK)**: (Returns updated settings object)

### 3.3 Manage Weekly Schedule
- **Purpose**: View or update the opening/closing schedule for each day of the week.
- **Endpoint**: `PATCH /api/v1/admin/clinic/weekly-schedule/`
- **Authentication**: Required (Bearer Token)
- **Permissions**: Super Admin, Admin
- **Request Body**:
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
- **Successful Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Weekly schedule updated successfully."
  }
  ```

### 3.4 Clinic Holidays
- **Endpoints**:
  - `GET /api/v1/admin/clinic/holidays/` (List all holidays)
  - `POST /api/v1/admin/clinic/holidays/` (Create holiday)
  - `DELETE /api/v1/admin/clinic/holidays/{id}/` (Remove holiday)
- **Permissions**: Super Admin, Admin (Full Access), Others (Read-only on GET)
- **Business Rules**:
  - No appointments can be booked on a holiday.
  - If a holiday is created on a date with existing appointments, they must be flagged or rescheduled.
- **Request Body (POST)**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `holiday_name` | String | Yes | Max 100 chars | Name/Reason for holiday. |
  | `holiday_date` | Date | Yes | YYYY-MM-DD | Date of the holiday. |
  | `description` | String | No | - | Additional details. |

---

## 4. Doctor Scheduling

### 4.1 Update Doctor Availability Preferences
- **Purpose**: Configures a doctor's booking parameters.
- **Endpoint**: `PATCH /api/v1/admin/doctors/{doctor_id}/availability/`
- **Authentication**: Required (Bearer Token)
- **Permissions**: Super Admin, Admin, Doctor Owner (only their own)
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `accepts_appointments` | Boolean | Yes | - | If false, doctor will not appear in slot calculations. |
  | `consultation_duration_minutes` | Integer | Yes | Min 15 | Duration of each consultation. |
  | `max_daily_patients` | Integer | Yes | Min 1 | Maximum patients the doctor will see per day. |

### 4.2 Update Doctor Working Days
- **Purpose**: Sets a doctor's specific operating hours for each weekday.
- **Endpoint**: `PATCH /api/v1/admin/doctors/{doctor_id}/working-days/`
- **Permissions**: Super Admin, Admin, Doctor Owner (only their own)
- **Request Body**:
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

### 4.3 Manage Doctor Leaves
- **Endpoints**:
  - `GET /api/v1/admin/doctors/{doctor_id}/leaves/`
  - `POST /api/v1/admin/doctors/{doctor_id}/leaves/`
  - `DELETE /api/v1/admin/doctors/{doctor_id}/leaves/{id}/`
- **Permissions**: Super Admin, Admin, Doctor Owner
- **Business Rules**:
  - Leave dates cannot overlap.
  - End Date must be greater than or equal to Start Date.
- **Request Body (POST)**:
  ```json
  {
    "start_date": "2026-07-10",
    "end_date": "2026-07-12",
    "reason": "Medical conference"
  }
  ```

### 4.4 Manage Doctor Blocked Slots
- **Endpoints**:
  - `GET /api/v1/admin/doctors/{doctor_id}/blocked-slots/`
  - `POST /api/v1/admin/doctors/{doctor_id}/blocked-slots/`
  - `DELETE /api/v1/admin/doctors/{doctor_id}/blocked-slots/{id}/`
- **Permissions**: Super Admin, Admin, Doctor Owner
- **Business Rules**:
  - Prevents booking during specific hours of a working day (e.g., 12:00 to 13:00 for a seminar).

---

## 5. Appointment Requests

### 5.1 Submit Appointment Request
- **Purpose**: Creates an initial booking request (typically from the website or receptionist).
- **Endpoint**: `POST /api/v1/appointment-requests/`
- **Authentication**: Public / Optional
- **Business Rules**:
  - Captures patient demographic details and preferred doctor/date/time.
  - Creates a `PENDING` request.
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `child_first_name` | String | Yes | Max 50 chars | Patient's first name. |
  | `child_last_name` | String | Yes | Max 50 chars | Patient's last name. |
  | `date_of_birth` | Date | Yes | YYYY-MM-DD | Patient's DOB. |
  | `gender` | String | Yes | MALE/FEMALE/OTHER | Patient's gender. |
  | `parent_first_name` | String | Yes | Max 50 chars | Parent's first name. |
  | `parent_last_name` | String | Yes | Max 50 chars | Parent's last name. |
  | `parent_mobile` | String | Yes | Valid mobile | Parent's contact number. |
  | `parent_email` | String | Yes | Valid email | Parent's email address. |
  | `preferred_doctor_id` | UUID | Yes | Active Doctor | Selected doctor. |
  | `preferred_date` | Date | Yes | Future date | Preferred date. |
  | `preferred_time` | String | Yes | HH:MM | Preferred start time. |
- **Successful Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "Appointment request submitted successfully.",
    "data": {
      "id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
      "request_number": "REQ-20260628-A1B2",
      "status": "PENDING",
      "child_first_name": "Tommy",
      "child_last_name": "Helper"
    }
  }
  ```

### 5.2 List Appointment Requests
- **Purpose**: Returns a paginated list of appointment requests for reception review.
- **Endpoint**: `GET /api/v1/appointment-requests/`
- **Query Parameters**:
  - `status` (PENDING, APPROVED, REJECTED, RESCHEDULED)
  - `search` (Search by patient name, email, phone)
  - `ordering` (e.g., `created_at`, `-preferred_date`)

---

## 6. Patient Matching

This module is triggered when a receptionist reviews a `PENDING` Appointment Request.

### 6.1 Get Patient Matches
- **Purpose**: Computes potential matching patient records from the database using fuzzy scoring.
- **Endpoint**: `GET /api/v1/patient-matching/`
- **Permissions**: Super Admin, Admin, Receptionist
- **Query Parameters**:
  - `request_id` (UUID, Required)
- **Successful Response (200 OK)**:
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

### 6.2 Link Existing Patient
- **Purpose**: Links the request to an existing patient record instead of creating a duplicate.
- **Endpoint**: `POST /api/v1/patient-matching/link/`
- **Request Body**:
  ```json
  {
    "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f",
    "patient_id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d"
  }
  ```
- **Successful Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Patient successfully linked to the request."
  }
  ```

### 6.3 Create New Patient from Request
- **Purpose**: Creates a brand new patient record using the details from the request.
- **Endpoint**: `POST /api/v1/patient-matching/create-patient/`
- **Business Rules**:
  - Blocks creation if an exact duplicate (first name, last name, date of birth, parent mobile) already exists.
- **Request Body**:
  ```json
  {
    "request_id": "c7b3a9d2-e5f8-4a1c-8d3e-9f0b2c4d6e8f"
  }
  ```
- **Successful Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "New patient record created and linked.",
    "data": {
      "patient_id": "8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f",
      "patient_number": "PAT-000042"
    }
  }
  ```

---

## 7. Patient Management

### 7.1 Manual Patient Search
- **Purpose**: Allows manual search across active patient records with pagination.
- **Endpoint**: `GET /api/v1/patients/search/`
- **Query Parameters**:
  - `search` (String, Required): Term to search (Min 2 chars). Matches code, names, mobile, or email.

### 7.2 Get Patient Details
- **Purpose**: Retrieves a patient's registration details, history, and timeline.
- **Endpoint**: `GET /api/v1/patients/{patient_id}/`

---

## 8. Appointment Management

### 8.1 List Appointments
- **Purpose**: Retrieves a paginated list of scheduled appointments.
- **Endpoint**: `GET /api/v1/appointments/`
- **Query Parameters**:
  - `status` (CONFIRMED, CHECKED_IN, IN_CONSULTATION, COMPLETED, CANCELLED, NO_SHOW)
  - `doctor_id` (UUID)
  - `date` (YYYY-MM-DD)
  - `search` (Patient search)

### 8.2 Edit Appointment
- **Purpose**: Modifies appointment details. Re-runs slot validation if doctor, date, or time changes.
- **Endpoint**: `PATCH /api/v1/appointments/{id}/`
- **Request Body**:
  ```json
  {
    "appointment_date": "2026-07-20",
    "start_time": "11:00",
    "notes": "Rescheduled by parent request."
  }
  ```

### 8.3 Check-in Patient
- **Purpose**: Marks a patient as checked-in (arrived at the clinic).
- **Endpoint**: `POST /api/v1/appointments/{id}/check-in/`
- **State Transition**: `CONFIRMED` $\rightarrow$ `CHECKED_IN`
- **Side Effects**: Logs a check-in event in the Patient and Appointment Timelines.

### 8.4 Start Doctor Consultation
- **Purpose**: Transitions the appointment status to `IN_CONSULTATION`.
- **Endpoint**: `POST /api/v1/appointments/{id}/start-consultation/`
- **Permissions**: Doctor (must be the assigned doctor)
- **State Transition**: `CHECKED_IN` $\rightarrow$ `IN_CONSULTATION`
- **Side Effects**: Automatically creates or links a `TreatmentCase` for the patient.

### 8.5 Cancel Appointment
- **Purpose**: Cancels a confirmed appointment.
- **Endpoint**: `POST /api/v1/appointments/{id}/cancel/`
- **Request Body**:
  ```json
  {
    "reason": "Patient is unwell."
  }
  ```
- **State Transition**: `CONFIRMED` $\rightarrow$ `CANCELLED`

---

## 9. Clinical Consultation

This workspace is utilized by the Doctor during the clinical session.

### 9.1 Open Consultation Session
- **Purpose**: Retrieves all clinical data required to load the doctor's workspace (patient summary, previous visits, current appointment details).
- **Endpoint**: `GET /api/v1/consultations/appointments/{appointment_id}/`
- **Permissions**: Doctor (assigned), Admin/Receptionist (Read-only)
- **Successful Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Consultation workspace loaded.",
    "data": {
      "appointment": {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
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

### 9.2 Create Consultation
- **Purpose**: Records clinical notes, findings, diagnosis, and treatment recommendations.
- **Endpoint**: `POST /api/v1/consultations/`
- **Permissions**: Doctor (assigned)
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `appointment_id` | UUID | Yes | Unique | Associated appointment. |
  | `chief_complaint` | String | Yes | Max 500 chars | Patient's primary complaint. |
  | `clinical_findings` | String | No | - | Clinical observation notes. |
  | `diagnosis` | String | Yes | Max 250 chars | Diagnosed condition. |
  | `treatment_notes` | String | Yes | - | Recommended treatment plan. |
  | `recommendations` | String | No | - | Home exercises/recs. |
- **Successful Response (201 Created)**: (Returns created consultation object)

### 9.3 Complete Consultation
- **Purpose**: Permanently locks the consultation record.
- **Endpoint**: `POST /api/v1/consultations/{consultation_id}/complete/`
- **Permissions**: Doctor (assigned)
- **Business Rules**:
  - A valid diagnosis must be recorded before completion.
  - Once completed, the record becomes read-only and cannot be updated.
- **State Transition**:
  - Parent Appointment: `IN_CONSULTATION` $\rightarrow$ `COMPLETED`
- **Side Effects**:
  - Triggers the follow-up decision step.
  - Appends history to `TreatmentCase`.

---

## 10. Follow-up & Case Management

This module manages the post-consultation journey, allowing doctors to schedule follow-ups or close treatment cases.

### 10.1 Record Follow-up Decision
- **Purpose**: Records whether the patient requires follow-up care or has completed treatment.
- **Endpoint**: `POST /api/v1/consultations/{consultation_id}/follow-up-decision/`
- **Permissions**: Doctor (assigned)
- **Request Body**:
  | Field | Type | Required | Description |
  | ----- | ---- | -------- | ----------- |
  | `requires_followup` | Boolean | Yes | Set to true if follow-up appointments are required. |
- **State Transition**:
  - `TreatmentCase`: `ACTIVE` $\rightarrow$ `FOLLOW_UP_REQUIRED` (if true) or `FOLLOW_UP_COMPLETED` (if false)

### 10.2 Create Follow-up
- **Purpose**: Directly schedules a confirmed follow-up appointment, bypassing the receptionist approval flow.
- **Endpoint**: `POST /api/v1/followups/`
- **Permissions**: Doctor (assigned)
- **Business Rules**:
  - The previous consultation must be completed.
  - Slot availability validation is enforced.
  - Directly creates a `CONFIRMED` appointment.
- **Request Body**:
  | Field | Type | Required | Validation | Description |
  | ----- | ---- | -------- | ---------- | ----------- |
  | `consultation_id` | UUID | Yes | Completed | The previous consultation ID. |
  | `doctor_id` | UUID | Yes | Active Doctor | Selected doctor. |
  | `followup_date` | Date | Yes | Future date | Appointment date. |
  | `start_time` | String | Yes | HH:MM | Slot start time. |
  | `reason` | String | No | - | Reason for follow-up. |
  | `notes` | String | No | - | Clinical notes for next visit. |
- **Successful Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "Follow-up appointment created successfully.",
    "data": {
      "id": "fa4b5c6d-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
      "appointment_number": "APT-FOLLOWUP-9F2B8D",
      "status": "CONFIRMED",
      "appointment_type": "FOLLOW_UP",
      "booking_source": "ADMIN_PANEL"
    }
  }
  ```

### 10.3 Update Follow-up
- **Purpose**: Allows the doctor to modify or reschedule a follow-up appointment.
- **Endpoint**: `PATCH /api/v1/followups/{appointment_id}/`
- **Permissions**: Doctor (assigned)
- **Request Body**:
  ```json
  {
    "appointment_date": "2026-08-10",
    "start_time": "11:30",
    "reason": "Updated review time"
  }
  ```

### 10.4 Cancel Follow-up
- **Purpose**: Cancels a scheduled follow-up appointment.
- **Endpoint**: `POST /api/v1/followups/{appointment_id}/cancel/`
- **Request Body**:
  ```json
  {
    "reason": "Family moving out of city."
  }
  ```
- **State Transition**:
  - Appointment: `CONFIRMED` $\rightarrow$ `CANCELLED`
  - `TreatmentCase`: Reverts to `FOLLOW_UP_REQUIRED` (if no other future appointments exist).

### 10.5 Get Patient Treatment Journey
- **Purpose**: Retrieves the timeline of all consultations, follow-ups, diagnoses, and case status for a patient.
- **Endpoint**: `GET /api/v1/treatment-cases/{patient_id}/`
- **Permissions**: Doctor, Admin, Receptionist (Read-only)

### 10.6 Close Treatment Case
- **Purpose**: Marks the patient's treatment case as closed.
- **Endpoint**: `POST /api/v1/treatment-cases/{patient_id}/close/`
- **Permissions**: Doctor (assigned)
- **Business Rules**:
  - Cannot close if there are pending consultations or future scheduled appointments.
- **Request Body**:
  | Field | Type | Required | Description |
  | ----- | ---- | -------- | ----------- |
  | `closing_summary` | String | Yes | Summary of the treatment outcome. |
  | `outcome` | String | Yes | E.g., `Treatment Completed`, `Referred`, `Discontinued`. |
- **State Transition**:
  - `TreatmentCase`: `ACTIVE` / `FOLLOW_UP` $\rightarrow$ `CASE_CLOSED`

### 10.7 Reopen Treatment Case
- **Purpose**: Reopens a closed treatment case if symptoms return or new follow-up is needed.
- **Endpoint**: `POST /api/v1/treatment-cases/{patient_id}/reopen/`
- **Permissions**: Doctor (assigned)
- **Request Body**:
  ```json
  {
    "reason": "Patient showing mild regression in speech clarity."
  }
  ```
- **State Transition**:
  - `TreatmentCase`: `CASE_CLOSED` $\rightarrow$ `ACTIVE`

---

## 11. File Uploads

### 11.1 Upload Consultation Document
- **Purpose**: Uploads supporting medical documents (e.g., reports, prescriptions, assessments) during a consultation.
- **Endpoint**: `POST /api/v1/consultations/{consultation_id}/attachments/`
- **Authentication**: Required
- **Permissions**: Doctor (assigned)
- **Business Rules**:
  - Maximum file size: **10MB**.
  - Allowed MIME Types: `application/pdf`, `image/jpeg`, `image/png`.
  - Files are uploaded to secure S3 buckets with short-lived presigned URLs.
- **Request Body**: Multi-part Form Data
  - `file`: Binary File
  - `description`: String (Optional)
- **Successful Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "File uploaded successfully.",
    "data": {
      "id": "e2f3a4b5-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
      "file_name": "assessment_report.pdf",
      "file_url": "https://s3.amazonaws.com/neuro-blooms-docs/...",
      "uploaded_at": "2026-06-28T08:15:00Z"
    }
  }
  ```

---

## 12. Timeline

### 12.1 Get Patient Timeline
- **Purpose**: Retrieves a chronological list of all events related to a patient (registration, appointments, cancellations, clinical notes).
- **Endpoint**: `GET /api/v1/patients/{patient_id}/timeline/`
- **Permissions**: Doctor, Admin, Receptionist

---

## 13. Reports & Analytics

### 13.1 Get Clinic Daily Metrics
- **Purpose**: Retrieves aggregate counts of daily activities for the dashboard.
- **Endpoint**: `GET /api/v1/reports/daily-metrics/`
- **Permissions**: Admin, Receptionist
- **Response (200 OK)**:
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

---

## 14. Notifications

### 14.1 Notification Event Triggers
The system automatically triggers internal notification events (e.g., Email or SMS queues) on key state changes:
1. **Appointment Request Submitted**: Sends confirmation to parent; alerts receptionists.
2. **Appointment Approved**: Sends appointment details, date, time, and doctor name to parent.
3. **Appointment Cancelled**: Sends cancellation notice to parent and doctor.
4. **Follow-up Scheduled**: Sends booking details directly to parent.

---

## 15. Common Responses & Error Envelopes

The Neuro Blooms API utilizes a standardized envelope format for all responses.

### 15.1 Success Envelope
```json
{
  "success": true,
  "message": "Human readable success message.",
  "data": {} // Object or Array
}
```

### 15.2 Error Envelope
```json
{
  "success": false,
  "message": "A summary of the error(s).",
  "errors": {
    "field_name": [
      "Specific validation or business error message."
    ]
  }
}
```

### 15.3 HTTP Status Codes Table
| Code | Name | Description |
| ---- | ---- | ----------- |
| **200** | OK | Request succeeded. Returns data. |
| **201** | Created | Resource successfully created. |
| **204** | No Content | Succeeded, no response body (e.g., logout, delete). |
| **400** | Bad Request | Syntactical or field validation errors. |
| **401** | Unauthorized | Authentication failed (missing, invalid, or expired token). |
| **403** | Forbidden | User lacks necessary role-based permissions. |
| **404** | Not Found | Requested resource does not exist. |
| **409** | Conflict | Concurrent conflict (e.g., slot already booked, duplicate patient). |
| **422** | Unprocessable Entity | Business rule violations (e.g., doctor on leave, case already closed). |
| **429** | Too Many Requests | Rate limit exceeded. |
| **500** | Internal Server Error | Unexpected backend or database error. |

---

## 16. Security & Performance Notes

### 16.1 Security Controls
- **Role-Based Access Control (RBAC)**: Enforced via Django REST Framework permissions at view level.
- **Data Sanitization**: All text inputs are stripped of HTML tags to prevent Cross-Site Scripting (XSS).
- **SQL Injection Protection**: Built-in Django ORM parameterized queries are used exclusively.
- **Soft Deletes**: Deleting sensitive clinical records (like attachments) does not purge them from DB; instead, it sets `is_deleted=True` for auditability.

### 16.2 Performance Optimizations
- **Pagination**: All list endpoints enforce `limit`/`offset` pagination (default limit: 20, max: 100).
- **Database Indexing**: Indexes are placed on highly queried fields: `doctor_id`, `patient_id`, `appointment_date`, and `status`.
- **Select Related / Prefetch Related**: Used extensively in services to prevent $N+1$ query issues when loading appointments and clinical history.
