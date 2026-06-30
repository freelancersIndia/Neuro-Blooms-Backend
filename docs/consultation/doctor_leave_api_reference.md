# Doctor Leave API Contract & Reference

This document provides a comprehensive, frontend-ready API reference for the **Doctor Leave** endpoints. It includes model schemas, endpoint descriptions, success responses, and error states.

---

## Table of Contents
1. [Model Schema & Validation Rules](#1-model-schema--validation-rules)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: List Doctor Leaves (GET)](#3-endpoint-1-list-doctor-leaves-get)
4. [Endpoint 2: Create Doctor Leave (POST)](#4-endpoint-2-create-doctor-leave-post)
5. [Endpoint 3: Update Doctor Leave (PATCH)](#5-endpoint-3-update-doctor-leave-patch)
6. [Endpoint 4: Delete/Cancel Doctor Leave (DELETE)](#6-endpoint-4-deletecancel-doctor-leave-delete)
7. [Error Responses & Scenarios](#7-error-responses--scenarios)

---

## 1. Model Schema & Validation Rules

The `DoctorLeave` model manages planned leaves or absences for a specific doctor.

### Validation Rules
1. **Required Fields**: `start_date`, `end_date`, and a non-blank `reason` are required.
2. **Date Order**: `end_date` must be on or after `start_date`.
3. **Past Check**: The leave cannot be entirely in the past (i.e., `end_date` must be greater than or equal to today's date).
4. **Overlap Check**: A doctor's leave cannot overlap with any of their other active leaves.
5. **Soft Deletion**: Leaves are soft-deleted by setting `is_active` to `false`.
6. **Reason Length**: The `reason` field cannot exceed 1000 characters.

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/admin/`
* **Path**: `doctors/<uuid:doctor_id>/leaves/`
* **Full URL**: `/api/v1/admin/doctors/<uuid:doctor_id>/leaves/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `doctors/<uuid:doctor_id>/leaves/` | Admin, Receptionist (Read-Only), Doctor Owner | Lists all active leaves for a doctor. |
| **POST** | `doctors/<uuid:doctor_id>/leaves/` | Admin, Doctor Owner | Creates a new planned leave. |
| **PATCH** | `doctors/<uuid:doctor_id>/leaves/<uuid:pk>/` | Admin, Doctor Owner | Updates an existing active leave. |
| **DELETE** | `doctors/<uuid:doctor_id>/leaves/<uuid:pk>/` | Admin, Doctor Owner | Soft-deletes (cancels) a planned leave. |

---

## 3. Endpoint 1: List Doctor Leaves (GET)

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/leaves/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**: Returns an array of active leaves, sorted chronologically by `start_date`.
  ```json
  {
    "success": true,
    "message": "Doctor leaves retrieved successfully.",
    "data": [
      {
        "id": "e3c1a45b-d890-4bf5-8a21-9d21c0cf00a5",
        "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
        "start_date": "2026-07-10",
        "end_date": "2026-07-15",
        "reason": "Annual medical conference attendance",
        "is_active": true
      },
      {
        "id": "f4d2b56c-e901-5ca6-9b32-0e32d1df11b6",
        "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
        "start_date": "2026-08-01",
        "end_date": "2026-08-03",
        "reason": "Personal time off",
        "is_active": true
      }
    ]
  }
  ```

---

## 4. Endpoint 2: Create Doctor Leave (POST)

### Request
* **HTTP Method**: `POST`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/leaves/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

### Request Payload
```json
{
  "start_date": "2026-07-10",
  "end_date": "2026-07-15",
  "reason": "Annual medical conference attendance"
}
```

### Success Response (201 Created)
* **Body Format**: JSON
  ```json
  {
    "success": true,
    "message": "Doctor leave created successfully.",
    "data": {
      "id": "e3c1a45b-d890-4bf5-8a21-9d21c0cf00a5",
      "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "start_date": "2026-07-10",
      "end_date": "2026-07-15",
      "reason": "Annual medical conference attendance",
      "is_active": true
    }
  }
  ```

---

## 5. Endpoint 3: Update Doctor Leave (PATCH)

### Request
* **HTTP Method**: `PATCH`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/leaves/<uuid:pk>/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

### Request Payload
You can perform partial updates. Any omitted fields will retain their existing database values.
```json
{
  "end_date": "2026-07-16",
  "reason": "Extended annual medical conference attendance"
}
```

### Success Response (200 OK)
* **Body Format**: JSON
  ```json
  {
    "success": true,
    "message": "Doctor leave updated successfully.",
    "data": {
      "id": "e3c1a45b-d890-4bf5-8a21-9d21c0cf00a5",
      "doctor": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "start_date": "2026-07-10",
      "end_date": "2026-07-16",
      "reason": "Extended annual medical conference attendance",
      "is_active": true
    }
  }
  ```

---

## 6. Endpoint 4: Delete/Cancel Doctor Leave (DELETE)

### Request
* **HTTP Method**: `DELETE`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/leaves/<uuid:pk>/`
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
    "message": "Doctor leave deleted successfully.",
    "data": null
  }
  ```

---

## 7. Error Responses & Scenarios

### 7.1. Date Order Validation Error (400 Bad Request)
* **Scenario**: `end_date` is configured before `start_date`.
* **Response**:
  ```json
  {
    "end_date": [
      "End date must be on or after start date."
    ]
  }
  ```

### 7.2. Overlapping Leaves Error (400 Bad Request)
* **Scenario**: The requested start and end dates overlap with another active leave record for the same doctor.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Leave overlaps another active leave."
    ]
  }
  ```

### 7.3. Leave Entirely in the Past (400 Bad Request)
* **Scenario**: A user attempts to create a leave where `end_date` is prior to today's date.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Cannot create leave entirely in the past."
    ]
  }
  ```

### 7.4. Authentication & Permission Errors (401 / 403)
* **401 Unauthorized**:
  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```
* **403 Forbidden**:
  ```json
  {
    "detail": "You do not have permission to perform this action."
  }
  ```
