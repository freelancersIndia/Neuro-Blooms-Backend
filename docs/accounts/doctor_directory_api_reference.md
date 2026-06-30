# Doctor Directory API Contract & Reference

This document provides a comprehensive, frontend-ready API reference for the **Doctor Directory** endpoints. It is designed to be fully self-contained so that frontend developers can easily integrate these endpoints.

---

## Table of Contents
1. [HTTP Endpoint Overview](#1-http-endpoint-overview)
2. [Endpoint 1: List Doctors (GET)](#2-endpoint-1-list-doctors-get)
3. [Endpoint 2: Get Doctor Details (GET)](#3-endpoint-2-get-doctor-details-get)
4. [Error Responses & Scenarios](#4-error-responses--scenarios)

---

## 1. HTTP Endpoint Overview

* **Base URL**: `/api/v1/`
* **Path**: `doctors/`
* **Full URL**: `/api/v1/doctors/`

| HTTP Method | Path | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `doctors/` | Any Authenticated User | Retrieves a list of all active doctors. |
| **GET** | `doctors/<uuid:id>/` | Any Authenticated User | Retrieves the detailed profile of a specific doctor, including their availability settings. |

---

## 2. Endpoint 1: List Doctors (GET)

### Purpose
Retrieves a list of all active users who have the `DOCTOR` role, ordered alphabetically by first name and last name.

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/doctors/`
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
    "message": "Doctors retrieved successfully.",
    "data": [
      {
        "id": "a654058f-f980-4044-b02d-0cbc8dadaff3",
        "first_name": "Doctor",
        "last_name": "Who",
        "full_name": "Doctor Who",
        "email": "doctor_test@test.com",
        "phone_number": "9876543210",
        "profile_image": "http://127.0.0.1:8000/media/profiles/dr_who.jpg",
        "specialization": "Cardiology",
        "qualification": "MD",
        "experience": 10,
        "is_active": true
      },
      {
        "id": "c876070f-d102-4266-d24f-2ede0fcf00a5",
        "first_name": "Jane",
        "last_name": "Smith",
        "full_name": "Jane Smith",
        "email": "jane.smith@clinic.com",
        "phone_number": "9876543211",
        "profile_image": null,
        "specialization": "Neurology",
        "qualification": "DM Neurology",
        "experience": 8,
        "is_active": true
      }
    ]
  }
  ```

---

## 3. Endpoint 2: Get Doctor Details (GET)

### Purpose
Retrieves the detailed profile of a specific doctor. It dynamically embeds the doctor's availability preferences (e.g., slot duration, patient limits, and appointment acceptance status).

### Request
* **HTTP Method**: `GET`
* **Path**: `/api/v1/doctors/<uuid:id>/`
* **Authentication**: Bearer JWT Token required.
* **Request Headers**:
  ```http
  Authorization: Bearer <access_token>
  Accept: application/json
  ```

#### Path Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Yes | The unique identifier of the doctor. |

### Success Response (200 OK)
* **Body Format**: JSON
* **Structure**:
  ```json
  {
    "success": true,
    "message": "Doctor details retrieved successfully.",
    "data": {
      "id": "a654058f-f980-4044-b02d-0cbc8dadaff3",
      "first_name": "Doctor",
      "last_name": "Who",
      "full_name": "Doctor Who",
      "email": "doctor_test@test.com",
      "phone_number": "9876543210",
      "profile_image": "http://127.0.0.1:8000/media/profiles/dr_who.jpg",
      "specialization": "Cardiology",
      "qualification": "MD",
      "experience": 10,
      "is_active": true,
      "availability": {
        "accepting_appointments": true,
        "consultation_duration": 30,
        "max_daily_patients": 15
      },
      "created_at": "2026-06-28T15:35:12.123456Z",
      "updated_at": "2026-06-28T15:35:12.123456Z"
    }
  }
  ```

---

## 4. Error Responses & Scenarios

### 4.1. Authentication Errors (401 Unauthorized)
* **Scenario**: The request does not contain a valid JWT Bearer token in the `Authorization` header.
* **Response**:
  ```json
  {
    "success": false,
    "message": "Authentication credentials were not provided.",
    "errors": null
  }
  ```

### 4.2. Not Found Errors (404 Not Found)
* **Scenario**: The `id` provided in the path does not exist, or the user associated with that `id` does not have the `DOCTOR` role.
* **Response**:
  ```json
  {
    "success": false,
    "message": "No User matches the given query.",
    "errors": null
  }
  ```
