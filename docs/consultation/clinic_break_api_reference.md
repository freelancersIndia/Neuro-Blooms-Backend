# Clinic Breaks API Contract & Reference

This document provides a comprehensive, enterprise-grade API reference for the **Clinic Breaks** endpoints. It is designed to be fully self-contained so that frontend, backend, or third-party integration teams can consume or implement these APIs without needing to inspect the underlying source code.

---

## Table of Contents
1. [Model Reference & Schema](#1-model-reference--schema)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: List Clinic Breaks (GET)](#3-endpoint-1-list-clinic-breaks-get)
4. [Endpoint 2: Create Clinic Break (POST)](#4-endpoint-2-create-clinic-break-post)
5. [Endpoint 3: Update Clinic Break (PATCH)](#5-endpoint-3-update-clinic-break-patch)
6. [Endpoint 4: Delete Clinic Break (DELETE)](#6-endpoint-4-delete-clinic-break-delete)
7. [Error Responses & Scenarios](#7-error-responses--scenarios)
8. [Security & Performance Considerations](#8-security--performance-considerations)

---

## 1. Model Reference & Schema

A clinic break represents a recurring scheduled closure during a working day (e.g., lunch break, staff meeting) when the clinic does not accept appointments. 

### Database Table
* **Table Name**: `consultations_clinic_breaks`

### Field-by-Field Specifications

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Auto-generated | Unique identifier for the break record. |
| `weekday` | VARCHAR(20) | Choices: `MONDAY`, `TUESDAY`, `WEDNESDAY`, `THURSDAY`, `FRIDAY`, `SATURDAY`, `SUNDAY` | The day of the week on which the break occurs. |
| `break_name` | VARCHAR(100) | Optional, Default: `""` | A descriptive name for the break (e.g., "Lunch Break", "Shift Handover"). |
| `start_time` | TIME | Required | The starting time of the break. Format: `HH:MM:SS` (or `HH:MM`). |
| `end_time` | TIME | Required | The ending time of the break. Format: `HH:MM:SS` (or `HH:MM`). Must be strictly greater than `start_time`. |
| `created_at` | DATETIME | Auto-created on insert | The timestamp when the record was created. |
| `updated_at` | DATETIME | Auto-updated on modification | The timestamp when the record was last updated. |
| `is_active` | BOOLEAN | Default: `True` | Used for soft-deletion. Inactive breaks are excluded from scheduling constraints. |

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/admin/`
* **Path**: `clinic/breaks/`
* **Full URL**: `/api/v1/admin/clinic/breaks/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `clinic/breaks/` | `ADMIN`, `RECEPTIONIST` | Lists all active clinic breaks sorted by weekday and start time. |
| **POST** | `clinic/breaks/` | `ADMIN` | Creates a new clinic break. |
| **PATCH** | `clinic/breaks/<uuid:id>/` | `ADMIN` | Partially updates an existing clinic break. |
| **DELETE** | `clinic/breaks/<uuid:id>/` | `ADMIN` | Soft-deletes a clinic break (`is_active` set to `false`). |

---

## 3. Endpoint 1: List Clinic Breaks (GET)

### Purpose
Retrieves all active clinic breaks sorted in ascending order by weekday (following standard calendar order starting with Monday) and then by start time.

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/admin/clinic/breaks/`
* **Authentication**: Bearer JWT Token required.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Clinic breaks retrieved successfully.",
    "data": [
      {
        "id": "e0a1a5b8-5d2b-4221-8736-ecf05785ea9a",
        "break_name": "Lunch Break",
        "weekday": "MONDAY",
        "start_time": "13:00:00",
        "end_time": "14:00:00",
        "is_active": true
      },
      {
        "id": "4bc459aa-fb9d-476c-82de-4bcdeab8c001",
        "break_name": "Staff Meeting",
        "weekday": "WEDNESDAY",
        "start_time": "15:00:00",
        "end_time": "16:00:00",
        "is_active": true
      }
    ]
  }
  ```

---

## 4. Endpoint 2: Create Clinic Break (POST)

### Purpose
Creates a new clinic break. This will prevent appointment slots from being generated during this time window on the specified weekday.

### Request
* **HTTP Method**: `POST`
* **Path**: `/api/v1/admin/clinic/breaks/`
* **Authentication**: Bearer JWT Token required.
* **Authorization**: `ADMIN` role only.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

#### Field-by-Field Validation Rules (JSON Payload)

| Field Name | Required | Validation Rules | Description |
| :--- | :--- | :--- | :--- |
| `weekday` | Yes | Must be a valid weekday choice (e.g. `MONDAY`). | Day of the week for the break. |
| `break_name` | No | Optional string. Max length: 100. | Title of the break. |
| `start_time` | Yes | Valid time string (`HH:MM` or `HH:MM:SS`). | Start time. |
| `end_time` | Yes | Valid time string (`HH:MM` or `HH:MM:SS`). Must be after `start_time`. | End time. |

#### Example Request Body
```json
{
  "break_name": "Tea Break",
  "weekday": "MONDAY",
  "start_time": "16:00:00",
  "end_time": "16:30:00"
}
```

### Processing & Validation Workflow
1. **Authentication & Role Check**: Validates the JWT token and verifies the user has the `ADMIN` role.
2. **Serializer & Service Validation**:
   - Checks that `end_time` is strictly after `start_time`.
   - Validates against the weekly schedule bounds:
     - Retrieves the weekly schedule for the given `weekday`.
     - If the schedule exists, it must be marked as open (`is_open=True`). Breaks cannot be created on weekdays when the clinic is closed.
     - The break's `start_time` and `end_time` must lie entirely within the clinic's operating hours (`opening_time` to `closing_time`) for that day.
     - If no weekly schedule exists for the weekday, it falls back to validating against the global `ClinicSettings` operating hours.
   - Checks for overlaps:
     - Confirms that the new break does not overlap with any existing active breaks (`is_active=True`) on the same `weekday`.
3. **Database Save**: Saves the `ClinicBreak` instance.
4. **Activity Logging**: Writes an `ActivityLog` entry with action `CLINIC_BREAK_CREATED`.
5. **Response**: Returns the created break object with a `201 Created` status.

### Success Response (201 Created)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Clinic break created successfully.",
    "data": {
      "id": "787c80ab-8d2a-4ef8-bcbb-92cc9ffbc890",
      "break_name": "Tea Break",
      "weekday": "MONDAY",
      "start_time": "16:00:00",
      "end_time": "16:30:00",
      "is_active": true
    }
  }
  ```

---

## 5. Endpoint 3: Update Clinic Break (PATCH)

### Purpose
Partially updates an existing active clinic break.

### Request
* **HTTP Method**: `PATCH`
* **Path**: `/api/v1/admin/clinic/breaks/<uuid:id>/`
* **Authentication**: Bearer JWT Token required.
* **Authorization**: `ADMIN` role only.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

#### Path Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Yes | The unique identifier of the break to update. |

#### Example Request Body
```json
{
  "start_time": "15:45:00",
  "end_time": "16:15:00"
}
```

### Processing & Validation Workflow
1. **Retrieve Instance**: Retrieves the active break record (`id=pk`, `is_active=True`). If it does not exist, returns `404 Not Found`.
2. **Instance-Aware Validation**:
   - The serializer combines the patch payload with the existing instance's fields to perform a complete validation.
   - Validates that the updated times do not overlap with other active breaks on the same weekday (excluding this break itself).
   - Validates that the times are within the operating hours of the weekly schedule or global clinic settings.
3. **Database Save**: Saves the updated `ClinicBreak` instance.
4. **Activity Logging**: Writes an `ActivityLog` entry with action `CLINIC_BREAK_UPDATED` listing the changed fields.

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Clinic break updated successfully.",
    "data": {
      "id": "787c80ab-8d2a-4ef8-bcbb-92cc9ffbc890",
      "break_name": "Tea Break",
      "weekday": "MONDAY",
      "start_time": "15:45:00",
      "end_time": "16:15:00",
      "is_active": true
    }
  }
  ```

---

## 6. Endpoint 4: Delete Clinic Break (DELETE)

### Purpose
Soft-deletes an existing clinic break by setting `is_active` to `false`.

### Request
* **HTTP Method**: `DELETE`
* **Path**: `/api/v1/admin/clinic/breaks/<uuid:id>/`
* **Authentication**: Bearer JWT Token required.
* **Authorization**: `ADMIN` role only.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  ```

#### Path Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Yes | The unique identifier of the break to delete. |

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Clinic break deleted successfully.",
    "data": null
  }
  ```

---

## 7. Error Responses & Scenarios

### 7.1. Authentication & Authorization Errors

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
* **Scenario**: A user with a non-admin role (e.g., `RECEPTIONIST`) attempts to perform a `POST`, `PATCH`, or `DELETE` request.
* **Response**:
  ```json
  {
    "success": false,
    "message": "You do not have permission to perform this action.",
    "errors": null
  }
  ```

---

### 7.2. Client & Validation Errors (400 Bad Request)

#### 1. End Time Before Start Time
* **Scenario**: `end_time` is less than or equal to `start_time`.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "end_time": [
        "End time must be after start time."
      ]
    }
  }
  ```

#### 2. Break Outside Clinic Operating Hours
* **Scenario**: The break's start or end time lies outside the operating hours configured in the weekly schedule or global settings.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "non_field_errors": [
        "Breaks must be inside clinic operating hours (09:00 - 18:00)."
      ]
    }
  }
  ```

#### 3. Break on Closed Day
* **Scenario**: Attempting to create a break on a weekday when the weekly schedule has `is_open=False`.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "weekday": [
        "Cannot create breaks for a weekday when the clinic is closed."
      ]
    }
  }
  ```

#### 4. Break Overlap
* **Scenario**: The break time overlaps with another already-active break on the same weekday.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "non_field_errors": [
        "Break overlaps existing break."
      ]
    }
  }
  ```

#### 5. Invalid Weekday Value
* **Scenario**: The `weekday` field is not one of the allowed choices (e.g., `"MONDAY"`).
* **Response**:
  ```json
  {
    "success": false,
    "message": "Validation failed.",
    "errors": {
      "weekday": [
        "\"TUESDAYY\" is not a valid choice."
      ]
    }
  }
  ```

---

### 7.3. Not Found Errors (404 Not Found)

#### 1. Break Not Found
* **Scenario**: Attempting to `PATCH` or `DELETE` a break using a non-existent or inactive ID.
* **Response**:
  ```json
  {
    "success": false,
    "message": "No ClinicBreak matches the given query.",
    "errors": null
  }
  ```

---

## 8. Security & Performance Considerations

### Transaction Isolation
* Database writes (`create_break`, `update_break`, `delete_break`) are wrapped in `@transaction.atomic` blocks in the service layer. This ensures that the validation checks (specifically the overlap check) and database commits occur in a safe, consistent transaction state.

### Soft Deletion
* When a break is deleted, it is not purged from the database. Instead, `is_active` is set to `false`. This preserves historical break records for audit logs and system analytics while immediately removing them from current slot scheduling constraints.
