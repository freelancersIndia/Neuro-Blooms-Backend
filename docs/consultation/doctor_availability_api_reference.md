# Doctor Availability API Contract & Reference

This document provides a comprehensive, enterprise-grade API reference for the **Doctor Availability** endpoints. It is designed to be fully self-contained so that frontend, backend, or third-party integration teams can consume or implement these APIs without needing to inspect the underlying source code.

---

## Table of Contents
1. [Model Reference & Schema](#1-model-reference--schema)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: Get Doctor Availability (GET)](#3-endpoint-1-get-doctor-availability-get)
4. [Endpoint 2: Update Doctor Availability (PATCH)](#4-endpoint-2-update-doctor-availability-patch)
5. [Error Responses & Scenarios](#5-error-responses--scenarios)
6. [Security & Performance Considerations](#6-security--performance-considerations)

---

## 1. Model Reference & Schema

Doctor Availability represents the scheduling preferences and constraints for a specific doctor (e.g., consultation slot duration, maximum daily patients, and whether they are currently accepting appointments).

### Database Table
* **Table Name**: `consultations_doctor_availabilities`

### Field-by-Field Specifications

| Database Field Name | API Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `id` | UUID | Primary Key, Auto-generated | Unique identifier for the availability record. |
| `doctor_id` | `doctor` | UUID | Foreign Key (to User) | The unique identifier of the doctor. |
| `accepts_appointments` | `accepting_appointments` | BOOLEAN | Default: `True` | Indicates if the doctor is currently accepting new appointments. |
| `consultation_duration_minutes` | `consultation_duration` | Positive Integer | Default: `30`. Must be one of: `15`, `20`, `30`, `45`, `60`, `90`, `120`. | The duration of a single appointment slot in minutes. |
| `max_daily_patients` | `max_daily_patients` | Positive Integer | Default: `15`. Must be between `1` and `100` (inclusive). | The maximum number of patients this doctor can see per day. |
| `created_at` | — | DATETIME | Auto-created on insert | The timestamp when the record was created. |
| `updated_at` | — | DATETIME | Auto-updated on modification | The timestamp when the record was last updated. |
| `is_active` | — | BOOLEAN | Default: `True` | Used for soft-deletion. A doctor can only have one active availability preference record. |

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/admin/`
* **Path**: `doctors/<uuid:doctor_id>/availability/`
* **Full URL**: `/api/v1/admin/doctors/<uuid:doctor_id>/availability/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `doctors/<uuid:doctor_id>/availability/` | `ADMIN`, `RECEPTIONIST`, `DOCTOR` (Owner) | Retrieves the doctor's availability preferences. Auto-creates a default record if none exists. |
| **PATCH** | `doctors/<uuid:doctor_id>/availability/` | `ADMIN`, `DOCTOR` (Owner) | Partially updates the doctor's availability preferences. |

---

## 3. Endpoint 1: Get Doctor Availability (GET)

### Purpose
Retrieves the availability preferences for the specified doctor. If no availability record exists in the database for an active doctor, the system automatically creates and returns a default preference record.

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/availability/`
* **Authentication**: Bearer JWT Token required.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

#### Path Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `doctor_id` | UUID | Yes | The unique identifier of the doctor. |

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Doctor availability retrieved successfully.",
    "data": {
      "id": "c3a9f07c-9b1d-44a1-8736-ecf05785ea9a",
      "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "accepting_appointments": true,
      "consultation_duration": 30,
      "max_daily_patients": 15
    }
  }
  ```

---

## 4. Endpoint 2: Update Doctor Availability (PATCH)

### Purpose
Partially updates the availability preferences (such as slot duration or patient limits) for a specific doctor.

### Request
* **HTTP Method**: `PATCH`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/availability/`
* **Authentication**: Bearer JWT Token required.
* **Authorization**: `ADMIN` or the owning `DOCTOR` only.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

#### Path Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `doctor_id` | UUID | Yes | The unique identifier of the doctor. |

#### Field-by-Field Validation Rules (JSON Payload)

| Field Name | Required | Validation Rules | Description |
| :--- | :--- | :--- | :--- |
| `accepting_appointments` | No | Must be a boolean. | Whether the doctor is accepting appointments. |
| `consultation_duration` | No | Must be an integer. Allowed values: `[15, 20, 30, 45, 60, 90, 120]`. | Slot duration in minutes. |
| `max_daily_patients` | No | Must be an integer between `1` and `100` (inclusive). | Maximum patients per day. |

#### Example Request Body
```json
{
  "accepting_appointments": false,
  "consultation_duration": 45,
  "max_daily_patients": 10
}
```

### Processing & Validation Workflow
1. **Authentication & Role Check**: Validates the JWT token and verifies the user has permission (`ADMIN` or is the owner of the record).
2. **Retrieve / Auto-Create**: Retrieves the existing availability record using `get_availability`. If the record doesn't exist, it is auto-created.
3. **Serializer Validation**:
   - Checks that `consultation_duration` (if provided) is in the allowed set.
   - Checks that `max_daily_patients` (if provided) is between 1 and 100.
4. **Database Save**: Saves the updated preferences to the database.
5. **Activity Logging**: Writes an `ActivityLog` entry with action `DOCTOR_AVAILABILITY_UPDATED` detailing the changed fields.
6. **Response**: Returns the updated availability object with a `200 OK` status.

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Doctor availability updated successfully.",
    "data": {
      "id": "c3a9f07c-9b1d-44a1-8736-ecf05785ea9a",
      "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "accepting_appointments": false,
      "consultation_duration": 45,
      "max_daily_patients": 10
    }
  }
  ```

---

## 5. Error Responses & Scenarios

### 5.1. Authentication & Authorization Errors

#### 1. Token Missing / Expired (401 Unauthorized)
* **Scenario**: Request lacks a valid JWT bearer token.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Authentication credentials were not provided.",
    "errors": null
  }
  ```

#### 2. Insufficient Permissions (403 Forbidden)
* **Scenario**: A receptionist attempts to perform a `PATCH` request, or a doctor attempts to view or update another doctor's availability.
* **Response**:
  ```json
  {
    "success": false,
    "message": "You do not have permission to perform this action.",
    "errors": null
  }
  ```

---

### 5.2. Client & Validation Errors (400 Bad Request)

#### 1. Invalid User / Not a Doctor
* **Scenario**: The `doctor_id` in the URL path belongs to a user who does not have the `DOCTOR` role, or the user does not exist.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "doctor": [
        "Doctor must exist and have the Doctor role."
      ]
    }
  }
  ```

#### 2. Invalid Consultation Duration
* **Scenario**: `consultation_duration` is not in the allowed list `[15, 20, 30, 45, 60, 90, 120]`.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "consultation_duration": [
        "Consultation duration must be one of [15, 20, 30, 45, 60, 90, 120]."
      ]
    }
  }
  ```

#### 3. Max Daily Patients Out of Bounds
* **Scenario**: `max_daily_patients` is less than 1 or greater than 100.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "max_daily_patients": [
        "Max daily patients must be between 1 and 100."
      ]
    }
  }
  ```

---

## 6. Security & Performance Considerations

### Just-In-Time Auto-creation
* The `get_availability` method automatically inserts a default availability record into the database the first time a doctor is queried. This simplifies onboarding, ensuring that every active doctor has a valid preference record immediately upon first view or slot generation.

### Database Constraints
* **Check Constraints**: The database enforces `consultation_duration_minutes > 0` and `max_daily_patients >= 0` at the database level (`doctor_consultation_duration_check` and `doctor_max_daily_patients_check`).
* **Uniqueness**: A partial unique index (`unique_active_doctor_availability`) ensures that a doctor can only have at most one active (`is_active=True`) availability record at any given time.
