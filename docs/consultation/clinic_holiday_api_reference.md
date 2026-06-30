# Clinic Holidays API Contract & Reference

This document provides a comprehensive, enterprise-grade API reference for the **Clinic Holidays** endpoints. It is designed to be fully self-contained so that frontend, backend, or third-party integration teams can consume or implement these APIs without needing to inspect the underlying source code.

---

## Table of Contents
1. [Model Reference & Schema](#1-model-reference--schema)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: List Clinic Holidays (GET)](#3-endpoint-1-list-clinic-holidays-get)
4. [Endpoint 2: Create Clinic Holiday (POST)](#4-endpoint-2-create-clinic-holiday-post)
5. [Endpoint 3: Update Clinic Holiday (PATCH)](#5-endpoint-3-update-clinic-holiday-patch)
6. [Endpoint 4: Delete Clinic Holiday (DELETE)](#6-endpoint-4-delete-clinic-holiday-delete)
7. [Error Responses & Scenarios](#7-error-responses--scenarios)
8. [Security & Performance Considerations](#8-security--performance-considerations)

---

## 1. Model Reference & Schema

A clinic holiday represents a day on which the entire clinic is closed (e.g. national holidays, annual maintenance). This is used as a global constraint when scheduling appointments and generating slots.

### Database Table
* **Table Name**: `consultations_clinic_holidays`

### Field-by-Field Specifications

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Auto-generated | Unique identifier for the holiday record. |
| `holiday_name` | VARCHAR(150) | Required (cannot be blank) | A short descriptive name for the holiday (e.g., "Independence Day"). |
| `holiday_date` | DATE | Unique (among active holidays) | The date of the holiday. Format: `YYYY-MM-DD`. |
| `description` | TEXT | Nullable, Optional | Additional notes or details regarding the holiday. |
| `created_at` | DATETIME | Auto-created on insert | The timestamp when the record was created. |
| `updated_at` | DATETIME | Auto-updated on modification | The timestamp when the record was last updated. |
| `is_active` | BOOLEAN | Default: `True` | Used for soft-deletion. Inactive holidays are excluded from scheduling constraints. |

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/admin/`
* **Path**: `clinic/holidays/`
* **Full URL**: `/api/v1/admin/clinic/holidays/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `clinic/holidays/` | `ADMIN`, `RECEPTIONIST` | Lists all active clinic holidays sorted chronologically. |
| **POST** | `clinic/holidays/` | `ADMIN` | Creates a new clinic holiday. |
| **PATCH** | `clinic/holidays/<uuid:id>/` | `ADMIN` | Partially updates an existing clinic holiday. |
| **DELETE** | `clinic/holidays/<uuid:id>/` | `ADMIN` | Soft-deletes a clinic holiday (`is_active` set to `false`). |

---

## 3. Endpoint 1: List Clinic Holidays (GET)

### Purpose
Retrieves all active clinic holidays sorted in ascending chronological order.

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/admin/clinic/holidays/`
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
    "status": "success",
    "message": "Holidays retrieved successfully.",
    "data": [
      {
        "id": "2364c237-7df7-47b2-bd55-9b2eead3e1b0",
        "holiday_name": "New Year's Day",
        "holiday_date": "2026-01-01",
        "description": "New Year celebration. Clinic closed.",
        "is_active": true
      },
      {
        "id": "ef2e987c-3f41-4560-8bb2-cc019bfb8b42",
        "holiday_name": "Independence Day",
        "holiday_date": "2026-08-15",
        "description": "National holiday.",
        "is_active": true
      }
    ]
  }
  ```

---

## 4. Endpoint 2: Create Clinic Holiday (POST)

### Purpose
Creates a new clinic holiday. This will block all appointment slot generation for the specified date.

### Request
* **HTTP Method**: `POST`
* **Path**: `/api/v1/admin/clinic/holidays/`
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
| `holiday_name` | Yes | Must be a string. Max length: 150. Cannot be empty or blank. | Name of the holiday. |
| `holiday_date` | Yes | Must be a valid date in `YYYY-MM-DD` format. Must be unique among all active holidays. | Date of the holiday. |
| `description` | No | Optional string. | Brief notes about the holiday. |

#### Example Request Body
```json
{
  "holiday_name": "Christmas Day",
  "holiday_date": "2026-12-25",
  "description": "Christmas holiday. All staff on leave."
}
```

### Processing Workflow
1. **Authentication & Role Check**: Validates the JWT token and verifies the user has the `ADMIN` role.
2. **Serializer Validation**:
   - Validates that `holiday_name` is not blank or exceeding 150 characters.
   - Validates that `holiday_date` is a valid date.
   - Checks if another active holiday (`is_active=True`) already exists on the same `holiday_date`. If so, raises a validation error.
3. **Database Save**: Saves the new `ClinicHoliday` instance to the database.
4. **Activity Logging**: Creates an `ActivityLog` entry with action `CLINIC_HOLIDAY_CREATED` detailing the created holiday name and date.
5. **Response**: Returns the created holiday object with a `201 Created` status.

### Success Response (201 Created)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "status": "success",
    "message": "Clinic holiday created successfully.",
    "data": {
      "id": "6c4349ab-2b7c-4ef7-b2bb-b12eefab8c90",
      "holiday_name": "Christmas Day",
      "holiday_date": "2026-12-25",
      "description": "Christmas holiday. All staff on leave.",
      "is_active": true
    }
  }
  ```

### Side Effects & Database Changes
* **Database Updates**: 1 row inserted into `consultations_clinic_holidays`.
* **Activity Log Entry**: Creates an `ActivityLog` entry with action `CLINIC_HOLIDAY_CREATED` (e.g., `"Clinic holiday 'Christmas Day' created for 2026-12-25 by admin@clinic.com."`).

---

## 5. Endpoint 3: Update Clinic Holiday (PATCH)

### Purpose
Partially updates an existing active clinic holiday.

### Request
* **HTTP Method**: `PATCH`
* **Path**: `/api/v1/admin/clinic/holidays/<uuid:id>/`
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
| `id` | UUID | Yes | The unique identifier of the holiday to update. |

#### Example Request Body
```json
{
  "holiday_name": "Christmas Day (Observed)",
  "description": "Extended holiday details."
}
```

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "status": "success",
    "message": "Clinic holiday updated successfully.",
    "data": {
      "id": "6c4349ab-2b7c-4ef7-b2bb-b12eefab8c90",
      "holiday_name": "Christmas Day (Observed)",
      "holiday_date": "2026-12-25",
      "description": "Extended holiday details.",
      "is_active": true
    }
  }
  ```

### Side Effects & Database Changes
* **Database Updates**: 1 row updated in `consultations_clinic_holidays`.
* **Activity Log Entry**: Creates an `ActivityLog` entry with action `CLINIC_HOLIDAY_UPDATED` detailing the modified fields (e.g., `"Clinic holiday 'Christmas Day (Observed)' updated by admin@clinic.com. Changed: holiday_name, description."`).

---

## 6. Endpoint 4: Delete Clinic Holiday (DELETE)

### Purpose
Soft-deletes an existing clinic holiday by setting `is_active` to `false`. Once inactive, the date will no longer block slot generation.

### Request
* **HTTP Method**: `DELETE`
* **Path**: `/api/v1/admin/clinic/holidays/<uuid:id>/`
* **Authentication**: Bearer JWT Token required.
* **Authorization**: `ADMIN` role only.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  ```

#### Path Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Yes | The unique identifier of the holiday to delete. |

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "status": "success",
    "message": "Clinic holiday deleted successfully.",
    "data": null
  }
  ```

### Side Effects & Database Changes
* **Database Updates**: The target row's `is_active` field is set to `false`, and `updated_at` is updated.
* **Activity Log Entry**: Creates an `ActivityLog` entry with action `CLINIC_HOLIDAY_DELETED` (e.g., `"Clinic holiday 'Christmas Day (Observed)' on 2026-12-25 soft deleted by admin@clinic.com."`).

---

## 7. Error Responses & Scenarios

### 7.1. Authentication & Authorization Errors

#### 1. Token Missing / Expired (401 Unauthorized)
* **Scenario**: The request lacks a valid JWT bearer token.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Authentication credentials were not provided.",
    "code": "not_authenticated"
  }
  ```

#### 2. Insufficient Permissions (403 Forbidden)
* **Scenario**: A user with a non-admin role (e.g. `RECEPTIONIST`) attempts to `POST`, `PATCH`, or `DELETE` a holiday.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "You do not have permission to perform this action.",
    "code": "permission_denied"
  }
  ```

---

### 7.2. Client & Validation Errors (400 Bad Request)

#### 1. Duplicate Holiday Date
* **Scenario**: Attempting to create or update a holiday to a date that already has an active holiday.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "holiday_date": [
        "Another active holiday is already configured on this date."
      ]
    }
  }
  ```

#### 2. Blank Holiday Name
* **Scenario**: `holiday_name` is missing or is just whitespace.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "holiday_name": [
        "Holiday name cannot be blank."
      ]
    }
  }
  ```

#### 3. Invalid Date Format
* **Scenario**: `holiday_date` is not in the format `YYYY-MM-DD` (e.g. `"25-12-2026"`).
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "holiday_date": [
        "Date has wrong format. Use one of these formats instead: YYYY-MM-DD."
      ]
    }
  }
  ```

---

### 7.3. Not Found Errors (404 Not Found)

#### 1. Holiday Not Found / Inactive
* **Scenario**: Attempting to `PATCH` or `DELETE` a holiday using an ID that does not exist or has already been soft-deleted.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "No ClinicHoliday matches the given query.",
    "code": "not_found"
  }
  ```

---

## 8. Security & Performance Considerations

### Transaction Isolation
* All write operations (`create_holiday`, `update_holiday`, `delete_holiday`) are executed within `@transaction.atomic` blocks to guarantee database consistency and write integrity.

### Unique Constraint
* A database `UniqueConstraint` named `unique_active_holiday_date` enforces date uniqueness only on active records (`is_active=True`). This allows the system to hold historical soft-deleted holiday records on the same date without violating database uniqueness constraints.
