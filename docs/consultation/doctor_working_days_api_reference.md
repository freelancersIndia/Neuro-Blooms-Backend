# Doctor Working Days API Contract & Reference

This document provides a comprehensive, frontend-ready API reference for the **Doctor Working Days** endpoints. It includes model schemas, endpoint descriptions, success responses, and error states.

---

## Table of Contents
1. [Model Schema & Validation Rules](#1-model-schema--validation-rules)
2. [HTTP Endpoint Overview](#2-http-endpoint-overview)
3. [Endpoint 1: Get Doctor Working Days (GET)](#3-endpoint-1-get-doctor-working-days-get)
4. [Endpoint 2: Bulk Update Doctor Working Days (PATCH)](#4-endpoint-2-bulk-update-doctor-working-days-patch)
5. [Error Responses & Scenarios](#5-error-responses--scenarios)

---

## 1. Model Schema & Validation Rules

The `DoctorWorkingDay` model configures the weekly operating hours for a specific doctor.

### Validation Rules
1. **Uniqueness**: A doctor can have only one record per weekday (exactly 7 records in total).
2. **Weekly Completeness**: A bulk update must contain exactly 7 days, representing each weekday uniquely.
3. **Operating Bounds**:
   * If `is_working` is `false`, `opening_time` and `closing_time` are automatically set to `null`.
   * If `is_working` is `true`, `opening_time` and `closing_time` are required, and `closing_time` must be strictly after `opening_time`.
   * **Clinic Schedule Alignment**: The doctor's working hours must fall within the clinic's operating hours for that weekday. If the clinic is closed on a weekday, the doctor cannot be scheduled to work on that day.
     * *Example*: If the clinic hours are `09:00` to `18:00`, a doctor cannot be scheduled from `08:30` to `17:00`.

---

## 2. HTTP Endpoint Overview

* **Base URL**: `/api/v1/admin/`
* **Path**: `doctors/<uuid:doctor_id>/working-days/`
* **Full URL**: `/api/v1/admin/doctors/<uuid:doctor_id>/working-days/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `doctors/<uuid:doctor_id>/working-days/` | Admin, Receptionist (Read-Only), Doctor Owner | Retrieves the 7-day weekly schedule for a doctor (auto-populates default schedule if missing). |
| **PATCH** | `doctors/<uuid:doctor_id>/working-days/` | Admin, Doctor Owner | Bulk updates the doctor's 7-day weekly schedule. |

---

## 3. Endpoint 1: Get Doctor Working Days (GET)

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/working-days/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**: Returns all 7 days of the week, sorted from Monday to Sunday.
  ```json
  {
    "success": true,
    "message": "Doctor working days retrieved successfully.",
    "data": [
      {
        "weekday": "MONDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "TUESDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "WEDNESDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "THURSDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "FRIDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "18:00:00"
      },
      {
        "weekday": "SATURDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "13:00:00"
      },
      {
        "weekday": "SUNDAY",
        "is_working": false,
        "opening_time": null,
        "closing_time": null
      }
    ]
  }
  ```

---

## 4. Endpoint 2: Bulk Update Doctor Working Days (PATCH)

### Request
* **HTTP Method**: `PATCH`
* **Path**: `/api/v1/admin/doctors/<uuid:doctor_id>/working-days/`
* **Authentication**: Bearer JWT Token required.
* **Headers**:
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  Accept: application/json
  ```

### Request Payload
Must include exactly 7 unique weekday objects in the `working_days` array:
```json
{
  "working_days": [
    {
      "weekday": "MONDAY",
      "is_working": true,
      "opening_time": "09:00:00",
      "closing_time": "17:00:00"
    },
    {
      "weekday": "TUESDAY",
      "is_working": true,
      "opening_time": "09:00:00",
      "closing_time": "17:00:00"
    },
    {
      "weekday": "WEDNESDAY",
      "is_working": true,
      "opening_time": "09:00:00",
      "closing_time": "17:00:00"
    },
    {
      "weekday": "THURSDAY",
      "is_working": true,
      "opening_time": "09:00:00",
      "closing_time": "17:00:00"
    },
    {
      "weekday": "FRIDAY",
      "is_working": true,
      "opening_time": "09:00:00",
      "closing_time": "17:00:00"
    },
    {
      "weekday": "SATURDAY",
      "is_working": false,
      "opening_time": null,
      "closing_time": null
    },
    {
      "weekday": "SUNDAY",
      "is_working": false,
      "opening_time": null,
      "closing_time": null
    }
  ]
}
```

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**: Returns the updated 7-day schedule.
  ```json
  {
    "success": true,
    "message": "Doctor working days updated successfully.",
    "data": [
      {
        "weekday": "MONDAY",
        "is_working": true,
        "opening_time": "09:00:00",
        "closing_time": "17:00:00"
      },
      ...
    ]
  }
  ```

---

## 5. Error Responses & Scenarios

### 5.1. Authentication Errors (401 Unauthorized)
* **Scenario**: The request does not contain a valid JWT Bearer token in the `Authorization` header.
* **Response**:
  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```

### 5.2. Permission Errors (403 Forbidden)
* **Scenario**: A doctor attempts to update another doctor's working hours, or a receptionist tries to perform a `PATCH` request.
* **Response**:
  ```json
  {
    "detail": "You do not have permission to perform this action."
  }
  ```

### 5.3. Invalid Weekday Count or Non-Unique Days (400 Bad Request)
* **Scenario**: The `working_days` array does not contain exactly 7 objects, or contains duplicate weekdays.
* **Response**:
  ```json
  {
    "working_days": [
      "Bulk update must include exactly 7 days of the week."
    ]
  }
  ```

### 5.4. Outside Clinic Hours Validation Error (400 Bad Request)
* **Scenario**: A doctor's configured hours exceed the clinic's operating hours, or a doctor is configured as working on a day the clinic is closed.
* **Response**:
  ```json
  {
    "non_field_errors": [
      "Doctor working hours on SATURDAY must fall within clinic operating hours (09:00 - 13:00)."
    ]
  }
  ```
  *(Or if the clinic is closed)*:
  ```json
  {
    "non_field_errors": [
      "Cannot configure working hours on SUNDAY because the clinic is closed."
    ]
  }
  ```
