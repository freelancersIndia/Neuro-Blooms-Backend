# Appointment Request API Contract & Reference

This document provides a comprehensive, frontend-ready API reference for the **Appointment Request** system. It covers both the **Public-Facing (Unauthenticated) Intake APIs** used by parents/guardians on the clinic's public website and the **Administrative (Authenticated) APIs** used by admins and receptionists to review, match, approve, reject, or reschedule requests.

---

## Table of Contents
1. [Model Schema & Choices](#1-model-schema--choices)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Public Endpoints (Unauthenticated)](#3-public-endpoints-unauthenticated)
    - [3.1. List Active Doctors (GET)](#31-list-active-doctors-get)
    - [3.2. Get Available Slots (GET)](#32-get-available-slots-get)
    - [3.3. Submit Appointment Request (POST)](#33-submit-appointment-request-post)
4. [Administrative Endpoints (Authenticated)](#4-administrative-endpoints-authenticated)
    - [4.1. List Appointment Requests (GET)](#41-list-appointment-requests-get)
    - [4.2. Retrieve Appointment Request Details (GET)](#42-retrieve-appointment-request-details-get)
    - [4.3. Approve Request (POST)](#43-approve-request-post)
    - [4.4. Reject Request (POST)](#44-reject-request-post)
    - [4.5. Reschedule Request (POST)](#45-reschedule-request-post)
5. [Error Responses & Scenarios](#5-error-responses--scenarios)

---

## 1. Model Schema & Choices

The `AppointmentRequest` model represents an intake request submitted by a parent or guardian.

### Available Choice Enums

* **`RelationshipToChild`**:
  * `FATHER` ("Father")
  * `MOTHER` ("Mother")
  * `GUARDIAN` ("Guardian")
  * `GRANDPARENT` ("Grandparent")
  * `OTHER` ("Other")

* **`Gender`**:
  * `MALE` ("Male")
  * `FEMALE` ("Female")
  * `OTHER` ("Other")
  * `PREFER_NOT_TO_SAY` ("Prefer Not To Say")

* **`AppointmentType`**:
  * `INITIAL` ("Initial")
  * `FOLLOW_UP` ("Follow Up")
  * `REVIEW` ("Review")
  * `INITIAL_CONSULTATION` ("Initial Consultation")
  * `DEVELOPMENT_ASSESSMENT` ("Development Assessment")

* **`BookingSource`**:
  * `WEBSITE` ("Website")
  * `ADMIN_PANEL` ("Admin Panel")
  * `RECEPTIONIST` ("Receptionist")
  * `WHATSAPP` ("WhatsApp")

* **`AppointmentRequestStatus`**:
  * `PENDING` ("Pending")
  * `APPROVED` ("Approved")
  * `REJECTED` ("Rejected")
  * `PATIENT_LINKED` ("Patient Linked")
  * `PATIENT_CREATED` ("Patient Created")
  * `RESCHEDULED` ("Rescheduled")

---

## 2. HTTP Endpoint Overview

### Public Endpoints
* **Base URL**: `/api/v1/public/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `doctors/` | Anonymous (Public) | Lists active doctors for selection. |
| **GET** | `appointments/available-slots/` | Anonymous (Public) | Lists available slots for a doctor on a date. |
| **POST** | `appointment-requests/` | Anonymous (Public) | Submits a new appointment request. |

### Administrative Endpoints
* **Base URL**: `/api/v1/admin/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `appointment-requests/` | Admin, Receptionist, Doctor (Read-Only) | Lists all submitted requests (paginated). |
| **GET** | `appointment-requests/<uuid:id>/` | Admin, Receptionist, Doctor (Read-Only) | Retrieves request details with matching patients. |
| **POST** | `appointment-requests/<uuid:id>/approve/` | Admin, Receptionist | Approves a request and creates a confirmed appointment. |
| **POST** | `appointment-requests/<uuid:id>/reject/` | Admin, Receptionist | Rejects a request with a reason. |
| **POST** | `appointment-requests/<uuid:id>/reschedule/` | Admin, Receptionist | Suggests a different slot/reschedules the request. |

---

## 3. Public Endpoints (Unauthenticated)

### 3.1. List Active Doctors (GET)
* **Path**: `/api/v1/public/doctors/`
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Active doctors retrieved successfully.",
    "data": [
      {
        "id": "a654058f-f980-4044-b02d-0cbc8dadaff3",
        "full_name": "Dr. Sarah Johnson",
        "specialization": "Pediatric Neurologist",
        "qualification": "MD, DM (Neurology)",
        "experience": 12,
        "profile_image": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=150&h=150"
      }
    ]
  }
  ```

### 3.2. Get Available Slots (GET)
* **Path**: `/api/v1/public/appointments/available-slots/`
* **Query Parameters**:
  * `doctor_id` (UUID, Required)
  * `appointment_date` (Date string in `YYYY-MM-DD` format, Required)
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Available slots retrieved successfully.",
    "data": {
      "doctor_id": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "date": "2026-07-20",
      "available_slots": [
        {"start": "09:00", "end": "09:30"},
        {"start": "09:30", "end": "10:00"},
        {"start": "10:00", "end": "10:30"}
      ]
    }
  }
  ```

### 3.3. Submit Appointment Request (POST)
* **Path**: `/api/v1/public/appointment-requests/`
* **Request Payload**:
  ```json
  {
    "parent_first_name": "Ravi",
    "parent_last_name": "Kumar",
    "relationship_to_child": "FATHER",
    "mobile_number": "9876543210",
    "alternate_mobile_number": "9876543211",
    "email": "ravi.kumar@example.com",
    "child_first_name": "Aarav",
    "child_last_name": "Kumar",
    "date_of_birth": "2020-01-01",
    "gender": "MALE",
    "appointment_type": "INITIAL_CONSULTATION",
    "primary_concern": "Speech delay and lack of social engagement.",
    "preferred_date": "2026-07-20",
    "preferred_time_slot": "10:30",
    "additional_notes": "Prefers morning slots if possible.",
    "referral_source": "School Teacher"
  }
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "Appointment request submitted successfully.",
    "data": {
      "id": "d3b07384-d113-4956-a5d8-472d7d56637e",
      "request_number": "REQ-2026-00001",
      "status": "PENDING",
      "child_first_name": "Aarav",
      "child_last_name": "Kumar",
      "preferred_date": "2026-07-20",
      "preferred_time_slot": "10:30"
    }
  }
  ```

---

## 4. Administrative Endpoints (Authenticated)

### 4.1. List Appointment Requests (GET)
* **Path**: `/api/v1/admin/appointment-requests/`
* **Query Parameters (Filters & Search)**:
  * `status` (String, Optional: `PENDING`, `APPROVED`, `REJECTED`, etc.)
  * `search` (String, Optional: search by child name, parent name, request number, mobile)
  * `page` (Integer, Optional)
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Appointment requests retrieved successfully.",
    "data": {
      "count": 12,
      "next": "/api/v1/admin/appointment-requests/?page=2",
      "previous": null,
      "results": [
        {
          "id": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "request_number": "REQ-2026-00001",
          "parent_first_name": "Ravi",
          "parent_last_name": "Kumar",
          "child_first_name": "Aarav",
          "child_last_name": "Kumar",
          "mobile_number": "9876543210",
          "preferred_date": "2026-07-20",
          "preferred_time_slot": "10:30",
          "status": "PENDING",
          "status_display": "Pending",
          "created_at": "2026-06-29T02:00:00Z"
        }
      ]
    }
  }
  ```

### 4.2. Retrieve Appointment Request Details (GET)
* **Path**: `/api/v1/admin/appointment-requests/<uuid:id>/`
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Appointment request retrieved.",
    "data": {
      "id": "d3b07384-d113-4956-a5d8-472d7d56637e",
      "request_number": "REQ-2026-00001",
      "parent_first_name": "Ravi",
      "parent_last_name": "Kumar",
      "relationship_to_child": "FATHER",
      "mobile_number": "9876543210",
      "alternate_mobile_number": "9876543211",
      "email": "ravi.kumar@example.com",
      "child_first_name": "Aarav",
      "child_last_name": "Kumar",
      "date_of_birth": "2020-01-01",
      "gender": "MALE",
      "appointment_type": "INITIAL_CONSULTATION",
      "appointment_type_display": "Initial Consultation",
      "primary_concern": "Speech delay and lack of social engagement.",
      "preferred_date": "2026-07-20",
      "preferred_time_slot": "10:30",
      "additional_notes": "Prefers morning slots.",
      "status": "PENDING",
      "status_display": "Pending",
      "match_result": {
        "request_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
        "total_matches": 1,
        "matches": [
          {
            "patient_id": "8a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
            "patient_code": "PAT-000014",
            "child_name": "Aarav Kumar",
            "parent_name": "Ravi Kumar",
            "mobile_number": "9876543210",
            "match_score": 96,
            "match_level": "EXACT_MATCH",
            "matched_fields": ["mobile_number", "child_name", "date_of_birth"]
          }
        ]
      },
      "timeline": []
    }
  }
  ```

### 4.3. Approve Request (POST)
* **Path**: `/api/v1/admin/appointment-requests/<uuid:id>/approve/`
* **Request Payload**:
  ```json
  {
    "doctor_id": "a654058f-f980-4044-b02d-0cbc8dadaff3",
    "appointment_date": "2026-07-20",
    "start_time": "10:30",
    "remarks": "Assigned to Dr. Sarah as preferred."
  }
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "Appointment request approved successfully.",
    "data": {
      "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "appointment_number": "APT-20260720-A3B9C2",
      "patient_name": "Aarav Kumar",
      "doctor_name": "Dr. Sarah Johnson",
      "appointment_type": "INITIAL_CONSULTATION",
      "status": "CONFIRMED",
      "appointment_date": "2026-07-20",
      "start_time": "10:30:00",
      "end_time": "11:00:00"
    }
  }
  ```

### 4.4. Reject Request (POST)
* **Path**: `/api/v1/admin/appointment-requests/<uuid:id>/reject/`
* **Request Payload**:
  ```json
  {
    "reason": "Clinic is fully booked for developmental assessments this month. Referral sent to partner clinic."
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Appointment request rejected successfully.",
    "data": null
  }
  ```

### 4.5. Reschedule Request (POST)
* **Path**: `/api/v1/admin/appointment-requests/<uuid:id>/reschedule/`
* **Request Payload**:
  ```json
  {
    "doctor_id": "a654058f-f980-4044-b02d-0cbc8dadaff3",
    "appointment_date": "2026-07-21",
    "start_time": "11:30",
    "reason": "Preferred slot on July 20th is already booked."
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Appointment request rescheduled successfully.",
    "data": null
  }
  ```

---

## 5. Error Responses & Scenarios

### 5.1. Validation Error (400 Bad Request)
* **Scenario**: Missing required fields or invalid data types in request submission.
* **Response**:
  ```json
  {
    "email": [
      "Enter a valid email address."
    ],
    "date_of_birth": [
      "Date of birth cannot be in the future."
    ]
  }
  ```

### 5.2. Double Booking / Slot Conflict on Approval (400 Bad Request)
* **Scenario**: Attempting to approve a request into a slot that has been booked by another patient in the meantime.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "non_field_errors": [
        "Selected slot is no longer available. Reason: Slot already booked."
      ]
    }
  }
  ```

### 5.3. Request Not Found (404 Not Found)
* **Scenario**: The specified request UUID does not exist.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Appointment request not found.",
    "data": null
  }
  ```
