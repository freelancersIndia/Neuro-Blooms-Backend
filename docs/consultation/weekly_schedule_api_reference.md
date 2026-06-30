# Clinic Weekly Schedule API Contract & Reference

This document provides a comprehensive, enterprise-grade API reference for the **Clinic Weekly Schedule** endpoints. It is designed to be fully self-contained so that frontend, backend, or third-party integration teams can consume or implement these APIs without needing to inspect the underlying source code.

---

## Table of Contents
1. [Model Reference & Schema](#1-model-reference--schema)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: Retrieve Weekly Schedule (GET)](#3-endpoint-1-retrieve-weekly-schedule-get)
4. [Endpoint 2: Bulk Update Weekly Schedule (PATCH)](#4-endpoint-2-bulk-update-weekly-schedule-patch)
5. [Error Responses & Scenarios](#5-error-responses--scenarios)
6. [Security & Performance Considerations](#6-security--performance-considerations)

---

## 1. Model Reference & Schema

The weekly schedule is represented by the `ClinicWeeklySchedule` model in the database. It stores the operational state (open/closed) and the daily timing bounds for each day of the week.

### Database Table
* **Table Name**: `consultations_clinic_weekly_schedules`

### Field-by-Field Specifications

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key, Auto-generated | Unique identifier for the schedule record. |
| `weekday` | VARCHAR(20) | Unique, Choices: `MONDAY`, `TUESDAY`, `WEDNESDAY`, `THURSDAY`, `FRIDAY`, `SATURDAY`, `SUNDAY` | The day of the week represented by this record. |
| `is_open` | BOOLEAN | Default: `True` | Indicates if the clinic is open for operations on this weekday. |
| `opening_time` | TIME | Nullable (forced to `null` if `is_open` is `false`) | The time the clinic opens on this day. Format: `HH:MM:SS`. |
| `closing_time` | TIME | Nullable (forced to `null` if `is_open` is `false`) | The time the clinic closes on this day. Format: `HH:MM:SS`. |
| `created_at` | DATETIME | Auto-created on insert | The timestamp when the record was created. |
| `updated_at` | DATETIME | Auto-updated on modification | The timestamp when the record was last updated. |
| `is_active` | BOOLEAN | Default: `True` | Soft-delete status indicator. |

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/`
* **Path**: `clinic/weekly-schedule/`
* **Full URL**: `/api/v1/admin/clinic/weekly-schedule/`

| HTTP Method | Allowed Roles | Description |
| :--- | :--- | :--- |
| **GET** | `ADMIN`, `RECEPTIONIST` | Retrieves the clinic's operating schedule for all 7 days of the week. |
| **PATCH** | `ADMIN` | Performs a bulk update of the schedule for all 7 days in a single atomic transaction. |

---

## 3. Endpoint 1: Retrieve Weekly Schedule (GET)

### Purpose
Retrieves the full weekly schedule of the clinic. If the database does not contain records for all 7 days, the service will auto-populate missing days with default values (Monday to Saturday open from 09:00 to 18:00, Sunday closed).

### Request
* **HTTP Method**: `GET`
* **Authentication**: Bearer JWT Token required.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```
* **Query Parameters**: None.
* **Request Body**: None.

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "status": "success",
    "message": "Weekly schedule retrieved successfully.",
    "data": [
      {
        "weekday": "MONDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "TUESDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "WEDNESDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "THURSDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "FRIDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "SATURDAY",
        "is_open": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
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

---

## 4. Endpoint 2: Bulk Update Weekly Schedule (PATCH)

### Purpose
Performs an atomic, bulk update of the operating hours and open/closed status for all 7 days of the week.

### Request
* **HTTP Method**: `PATCH`
* **Authentication**: Bearer JWT Token required.
* **Authorization**: `ADMIN` role only.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

### Request Body
The request body must contain a `schedules` array containing exactly 7 objects, representing each day of the week exactly once.

#### Field-by-Field Validation Rules (JSON Payload)

| Field Name | Location | Required | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `schedules` | Root | Yes | Must be an array of exactly 7 objects. | Contains the daily schedules. |
| `schedules[].weekday` | Array Item | Yes | Must be one of: `MONDAY`, `TUESDAY`, `WEDNESDAY`, `THURSDAY`, `FRIDAY`, `SATURDAY`, `SUNDAY`. Each must be unique. | The weekday being updated. |
| `schedules[].is_open` | Array Item | Yes | Boolean (`true` or `false`). | Whether the clinic is open. |
| `schedules[].opening_time` | Array Item | Conditional | Required if `is_open` is `true`. Format: `HH:MM` or `HH:MM:SS`. Ignored/forced to `null` if `is_open` is `false`. | Opening time of the clinic. |
| `schedules[].closing_time` | Array Item | Conditional | Required if `is_open` is `true`. Must be strictly greater than `opening_time`. Format: `HH:MM` or `HH:MM:SS`. | Closing time of the clinic. |

#### Example Request Body
```json
{
  "schedules": [
    {
      "weekday": "MONDAY",
      "is_open": true,
      "opening_time": "08:30",
      "closing_time": "17:30"
    },
    {
      "weekday": "TUESDAY",
      "is_open": true,
      "opening_time": "08:30",
      "closing_time": "17:30"
    },
    {
      "weekday": "WEDNESDAY",
      "is_open": true,
      "opening_time": "08:30",
      "closing_time": "17:30"
    },
    {
      "weekday": "THURSDAY",
      "is_open": true,
      "opening_time": "08:30",
      "closing_time": "17:30"
    },
    {
      "weekday": "FRIDAY",
      "is_open": true,
      "opening_time": "08:30",
      "closing_time": "17:30"
    },
    {
      "weekday": "SATURDAY",
      "is_open": false,
      "opening_time": null,
      "closing_time": null
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

### Processing Workflow
1. **Authentication & Role Check**: The system validates the JWT token and verifies the user has the `ADMIN` role.
2. **Payload Parsing**: The request JSON is parsed.
3. **Serializer Validation**:
   - Checks if `schedules` has exactly 7 elements.
   - Checks if all 7 weekdays are uniquely represented.
   - For each element, if `is_open` is `true`, checks if `opening_time` and `closing_time` are present and that `closing_time > opening_time`.
   - For each element, if `is_open` is `false`, sets both times to `null`.
4. **Atomic Database Save**: Wraps the update in a transaction block. If any day fails validation or database constraints, the entire bulk operation is rolled back.
5. **Activity Logging**: Compares the new schedule against the database values. If differences exist, creates an `ActivityLog` record detailing the modified weekdays.
6. **Response Generation**: Returns the updated 7-day schedule.

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**: Returns the full updated list of 7 days, sorted in chronological order starting from Monday.
  ```json
  {
    "status": "success",
    "message": "Weekly schedule updated successfully.",
    "data": [
      {
        "weekday": "MONDAY",
        "is_open": true,
        "opening_time": "08:30:00",
        "closing_time": "17:30:00"
      },
      ...
      {
        "weekday": "SUNDAY",
        "is_open": false,
        "opening_time": null,
        "closing_time": null
      }
    ]
  }
  ```

### Side Effects & Database Changes
* **Database Updates**: 7 rows in `consultations_clinic_weekly_schedules` are modified.
* **Activity Log Entry**: Creates an `ActivityLog` entry with action `WEEKLY_SCHEDULE_UPDATED` and a description detailing the change (e.g., `"Weekly schedule updated by admin@clinic.com. Details: SATURDAY (Open: true -> false), SUNDAY (Open: false -> false)."`).

---

## 5. Error Responses & Scenarios

Below is the exhaustive list of error responses returned by the weekly schedule endpoints.

### 5.1. Authentication & Authorization Errors

#### 1. Token Missing (401 Unauthorized)
* **Scenario**: The request does not include the `Authorization` header.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Authentication credentials were not provided.",
    "code": "not_authenticated"
  }
  ```

#### 2. Token Expired / Invalid (401 Unauthorized)
* **Scenario**: The Bearer token is expired, corrupted, or invalid.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Given token not valid for any token type",
    "code": "token_not_valid",
    "errors": [
      {
        "token_class": "AccessToken",
        "token_type": "access",
        "message": "Token is invalid or expired"
      }
    ]
  }
  ```

#### 3. Insufficient Permissions (403 Forbidden)
* **Scenario**: A user with a non-admin role (e.g. `RECEPTIONIST` or `DOCTOR`) attempts to `PATCH` the weekly schedule.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "You do not have permission to perform this action.",
    "code": "permission_denied"
  }
  ```

---

### 5.2. Validation Errors (400 Bad Request)

All validation errors return a `400 Bad Request` status with `code: "validation_error"`.

#### 1. Array Size Error (schedules count != 7)
* **Scenario**: The `schedules` array contains fewer or more than 7 entries.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "schedules": [
        "Bulk update must include exactly 7 days of the week."
      ]
    }
  }
  ```

#### 2. Duplicate Weekdays
* **Scenario**: The `schedules` array contains duplicate weekdays (e.g., two entries for `MONDAY`).
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "schedules": [
        "Each weekday must be uniquely represented."
      ]
    }
  }
  ```

#### 3. Missing Times for Open Day
* **Scenario**: A weekday has `is_open: true` but `opening_time` or `closing_time` is missing or null.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "schedules": [
        {
          "non_field_errors": [
            "Opening and closing times are required if the clinic is open."
          ]
        },
        {}, {}, {}, {}, {}, {}
      ]
    }
  }
  ```

#### 4. Closing Time Before Opening Time
* **Scenario**: A weekday has `is_open: true` but the `closing_time` is equal to or earlier than `opening_time`.
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "schedules": [
        {
          "closing_time": [
            "Closing time must be after opening time."
          ]
        },
        {}, {}, {}, {}, {}, {}
      ]
    }
  }
  ```

#### 5. Invalid Weekday String
* **Scenario**: A value for `weekday` is not one of the allowed choices (e.g. `"MON"` or `"FUNDAY"`).
* **Response Payload**:
  ```json
  {
    "status": "error",
    "message": "Invalid data provided.",
    "code": "validation_error",
    "errors": {
      "schedules": [
        {
          "weekday": [
            "\"MON\" is not a valid choice."
          ]
        },
        {}, {}, {}, {}, {}, {}
      ]
    }
  }
  ```

---

## 6. Security & Performance Considerations

### Transaction Isolation
* The `bulk_update` service method is decorated with `@transaction.atomic`. This guarantees that if any single day's validation fails, the entire database transaction is aborted, preventing partial updates where the weekly schedule becomes inconsistent or fragmented.

### Validation Layering
* Rules are validated at both the Django REST Framework Serializer level and the database level via a Django `CheckConstraint` named `clinic_weekly_schedule_time_check`. This guarantees data integrity even if records are updated via the Django Admin panel or direct database scripts.

### Caching & Rate Limiting
* This endpoint is relatively static and should only be updated when clinic operational hours change. It is recommended to cache the `GET` response on the client side (e.g. in React state or local storage) to avoid unnecessary database queries during navigation.
