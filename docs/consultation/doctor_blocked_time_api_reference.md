# Doctor Blocked Time API Contract & Reference

This document provides a comprehensive, frontend-ready API reference for the **Doctor Blocked Time (Slots)** endpoints. It includes model schemas, validation rules, endpoint descriptions, success responses, and error states.

---

## Table of Contents
1. [Model Schema & Validation Rules](#1-model-schema--validation-rules)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: List Doctor Blocked Slots (GET)](#3-endpoint-1-list-doctor-blocked-slots-get)
4. [Endpoint 2: Create Doctor Blocked Slot (POST)](#4-endpoint-2-create-doctor-blocked-slot-post)
5. [Endpoint 3: Update Doctor Blocked Slot (PATCH)](#5-endpoint-3-update-doctor-blocked-slot-patch)
6. [Endpoint 4: Delete/Cancel Doctor Blocked Slot (DELETE)](#6-endpoint-4-deletecancel-doctor-blocked-slot-delete)
7. [Error Responses & Scenarios](#7-error-responses--scenarios)

---

## 1. Model Schema & Validation Rules

The `DoctorBlockedSlot` model represents a specific, one-off time window on a given date during which a doctor is unavailable (e.g., for personal meetings, administrative tasks, or urgent interruptions).

### Validation Rules
1. **Required Fields**: `block_date`, `start_time`, `end_time`, and a non-blank `reason` are required.
2. **Time Order**: `end_time` must be strictly after `start_time`.
3. **Past Check**: The `block_date` cannot be in the past (must be today's date or in the future).
4. **Working Hours Alignment**: The blocked time slot must fall entirely within the doctor's configured working hours for that weekday. If the doctor is not scheduled to work on that weekday, the slot cannot be blocked.
5. **No Overlapping Blocked Slots**: The blocked slot must not overlap with any other active blocked slot for the same doctor.
6. **No Overlapping Leaves**: The blocked slot must not fall on a date when the doctor is on active leave.
7. **No Overlapping Appointments**: The blocked slot must not overlap with any existing, confirmed, and active appointments for the same doctor.
8. **Soft Deletion**: Blocked slots are soft-deleted by setting `is_active` to `false`.

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/admin/`
* **Path**: `doctors/<uuid:doctor_id>/blocked-slots/`
* **Full URL**: `/api/v1/admin/doctors/<uuid:doctor_id>/blocked-slots/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `doctors/<uuid:doctor_id>/blocked-slots/` | Admin, Receptionist (Read-Only), Doctor Owner | Lists all active blocked slots for a doctor. |
| **POST** | `doctors/<uuid:doctor_id>/blocked-slots/` | Admin, Doctor Owner | Creates a new blocked slot. |
| **PATCH** | `doctors/<uuid:doctor_id>/blocked-slots/<uuid:pk>/` | Admin, Doctor Owner | Updates an existing active blocked slot. |
| **DELETE** | `doctors/<uuid:doctor_id>/blocked-slots/<uuid:pk>/` | Admin, Doctor Owner | Soft-deletes (cancels) a blocked slot. |

---

## 3. Endpoint 1: List Doctor Blocked Slots (GET)

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/blocked-slots/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**: Returns an array of active blocked slots, sorted by `block_date` and `start_time`.
  ```json
  {
    "success": true,
    "message": "Doctor blocked slots retrieved successfully.",
    "data": [
      {
        "id": "b123a45b-c890-4bf5-8a21-9d21c0cf00a5",
        "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
        "block_date": "2026-07-02",
        "start_time": "14:00:00",
        "end_time": "16:00:00",
        "reason": "Department staff meeting",
        "is_active": true
      },
      {
        "id": "c234b56c-d901-5ca6-9b32-0e32d1df11b6",
        "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
        "block_date": "2026-07-05",
        "start_time": "10:30:00",
        "end_time": "11:30:00",
        "reason": "Equipment calibration check",
        "is_active": true
      }
    ]
  }
  ```

---

## 4. Endpoint 2: Create Doctor Blocked Slot (POST)

### Request
* **HTTP Method**: `POST`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/blocked-slots/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

### Request Payload
* **Format**: Times must be sent as `HH:MM:SS` (or `HH:MM`).
```json
{
  "block_date": "2026-07-02",
  "start_time": "14:00:00",
  "end_time": "16:00:00",
  "reason": "Department staff meeting"
}
```

### Success Response (201 Created)
* **Body Format**: JSON
  ```json
  {
    "success": true,
    "message": "Doctor blocked slot created successfully.",
    "data": {
      "id": "b123a45b-c890-4bf5-8a21-9d21c0cf00a5",
      "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "block_date": "2026-07-02",
      "start_time": "14:00:00",
      "end_time": "16:00:00",
      "reason": "Department staff meeting",
      "is_active": true
    }
  }
  ```

---

## 5. Endpoint 3: Update Doctor Blocked Slot (PATCH)

### Request
* **HTTP Method**: `PATCH`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/blocked-slots/<uuid:pk>/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

### Request Payload
You can perform partial updates. Omitted fields will retain their existing database values.
```json
{
  "start_time": "14:30:00",
  "reason": "Delayed department staff meeting"
}
```

### Success Response (200 OK)
* **Body Format**: JSON
  ```json
  {
    "success": true,
    "message": "Doctor blocked slot updated successfully.",
    "data": {
      "id": "b123a45b-c890-4bf5-8a21-9d21c0cf00a5",
      "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "block_date": "2026-07-02",
      "start_time": "14:30:00",
      "end_time": "16:00:00",
      "reason": "Delayed department staff meeting",
      "is_active": true
    }
  }
  ```

---

## 6. Endpoint 4: Delete/Cancel Doctor Blocked Slot (DELETE)

### Request
* **HTTP Method**: `DELETE`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/blocked-slots/<uuid:pk>/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

### Success Response (200 OK)
* **Body Format**: JSON
  ```json
  {
    "success": true,
    "message": "Doctor blocked slot deleted successfully.",
    "data": null
  }
  ```

---

## 7. Error Responses & Scenarios

### 7.1. Time Order Validation Error (400 Bad Request)
* **Scenario**: `end_time` is configured prior to or equal to `start_time`.
* **Response**:
  ```json
  {
    "end_time": [
      "End time must be after start time."
    ]
  }
  ```

### 7.2. Out of Working Hours Error (400 Bad Request)
* **Scenario**: The blocked slot does not fit inside the doctor's working hours for that weekday.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Blocked time must fall within doctor's working hours (09:00 - 18:00)."
    ]
  }
  ```
  *(Or if the doctor does not work on that day)*:
  ```json
  {
    "non_field_errors": [
      "Doctor is not working on this day."
    ]
  }
  ```

### 7.3. Date in the Past Error (400 Bad Request)
* **Scenario**: `block_date` is configured before today's date.
* **Response**:
  ```json
  {
    "block_date": [
      "Block date cannot be in the past."
    ]
  }
  ```

### 7.4. Overlapping Blocked Time Error (400 Bad Request)
* **Scenario**: The slot overlaps with another active blocked slot.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Blocked time overlaps with another blocked slot."
    ]
  }
  ```

### 7.5. Overlapping Leave Error (400 Bad Request)
* **Scenario**: The slot falls on a date when the doctor is on active leave.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Cannot block time during doctor leave."
    ]
  }
  ```

### 7.6. Overlapping Confirmed Appointment Error (400 Bad Request)
* **Scenario**: The slot overlaps with an existing confirmed and active appointment for the doctor.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Cannot block time with existing confirmed appointments."
    ]
  }
  ```
