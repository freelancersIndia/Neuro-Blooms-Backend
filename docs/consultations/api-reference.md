# Neuro Blooms Healthcare Management System
## Consultations Module API Reference Specification

---

## Table of Contents
1. [Overview](#1-overview)
2. [Standard Response Envelopes](#2-standard-response-envelopes)
    - [Success Response Envelope](#success-response-envelope)
    - [Error Response Envelope](#error-response-envelope)
    - [Validation Error Envelope](#validation-error-envelope)
    - [Conflict Error Envelope](#conflict-error-envelope)
3. [Public Consultation Request API Specification](#3-public-consultation-request-api-specification)
    - [Submit Public Consultation Request (`POST /api/v1/public/consultation-request/`)](#submit-public-consultation-request)
4. [Appointment Request Management API Specification](#4-appointment-request-management-api-specification)
    - [List Appointment Requests (`GET /api/v1/appointments/requests/`)](#list-appointment-requests)
    - [Retrieve Appointment Request Detail (`GET /api/v1/appointments/requests/{id}/`)](#retrieve-appointment-request-detail)
    - [Get Appointment Request Statistics (`GET /api/v1/appointments/requests/statistics/`)](#get-appointment-request-statistics)
    - [Approve Appointment Request (`POST /api/v1/appointments/requests/{id}/approve/`)](#approve-appointment-request)
    - [Reject Appointment Request (`POST /api/v1/appointments/requests/{id}/reject/`)](#reject-appointment-request)
    - [Retrieve Appointment Request Timeline (`GET /api/v1/appointments/requests/{id}/timeline/`)](#retrieve-appointment-request-timeline)
    - [Export Appointment Requests to CSV (`GET /api/v1/appointments/requests/export/`)](#export-appointment-requests-to-csv)
5. [Data Normalization & Sanitization Rules](#5-data-normalization--sanitization-rules)
6. [Duplicate Prevention & Validation Logic](#6-duplicate-prevention--validation-logic)
7. [Best Practices, Throttling & Security Guidelines](#7-best-practices-throttling--security-guidelines)

---

## 1. Overview
The Neuro Blooms Consultations Module API provides endpoints for scheduling, booking, and managing patient assessments and appointments.

This module exposes:
1. A public-facing API for receiving appointment/consultation requests from the public website (recorded in the system as **Appointment Requests** in `PENDING` state).
2. Authenticated management APIs for receptionist and administrator workflows to review, list, aggregate statistics for, approve, reject, view timelines for, and export appointment requests.

Doctor and calendar scheduling/booking management API capabilities are not included in the scope of this module.

### Base URL
All API paths documented herein are relative to the project's gateway base URL:
```
https://api.neuroblooms.com/api/v1
```

---

## 2. Standard Response Envelopes

To maintain consistency with the Accounts module, the Consultations module enforces standardized JSON response structures.

### Success Response Envelope
Returned for successful operations (HTTP status codes `2xx`).
```json
{
  "success": true,
  "message": "Human-readable description of the completed operation.",
  "data": {}
}
```

### Error Response Envelope
Returned for general failures or unexpected server errors (HTTP status codes `500`).
```json
{
  "success": false,
  "message": "Human-readable explanation of the failure.",
  "errors": null
}
```

### Validation Error Envelope
Returned when input validation fails (HTTP `400 Bad Request`). The `errors` field contains a dictionary where keys represent field names, and values are arrays of validation messages.
```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "mobile_number": [
      "Enter a valid mobile number."
    ]
  }
}
```

### Conflict Error Envelope
Returned when duplicate requests exist in the database (HTTP `409 Conflict`).
```json
{
  "success": false,
  "message": "A consultation request already exists for this child on the selected date."
}
```

---

## 3. Public Consultation Request API Specification

### Submit Public Consultation Request

Submit a new appointment request from the website.

* **Endpoint:** `/public/consultation-request/`
* **Method:** `POST`
* **Authentication:** None Required (`AllowAny`)
* **Throttling:** Enforced (`AnonRateThrottle` - `100/day`)

#### Request Header
```http
Content-Type: application/json
```

#### Request Payload Specification
| Parameter | Type | Required | Description | Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| `parent_first_name` | String | Yes | First name of the parent/guardian. | Max 100 characters. Trimmed. |
| `parent_last_name` | String | Yes | Last name of the parent/guardian. | Max 150 characters. Trimmed. |
| `relationship_to_child`| String | Yes | Relationship designation. | Case-insensitive matching. Allowed values: `Mother`, `Father`, `Guardian`, `Grandparent`, `Other`. |
| `mobile_number` | String | Yes | Primary contact phone number. | Valid Indian mobile number format (e.g. 10 digits optionally starting with `+91`, `91`, or `0`). |
| `alternate_mobile_number`| String| No | Alternate contact phone number. | Must be a valid Indian mobile number format if provided. |
| `email` | String | No | Contact email address. | Standard RFC-compliant email validation. |
| `child_first_name` | String | Yes | Child's first name. | Max 150 characters. Trimmed. |
| `child_last_name` | String | Yes | Child's last name. | Max 150 characters. Trimmed. |
| `date_of_birth` | Date | Yes | Child's birth date (YYYY-MM-DD). | Cannot be a future date. |
| `gender` | String | Yes | Child's gender designation. | Case-insensitive matching. Allowed values: `Male`, `Female`, `Other`, `Prefer Not To Say`. |
| `appointment_type` | String | Yes | Requested consultation category. | Case-insensitive matching. Allowed values: `INITIAL_CONSULTATION`, `DEVELOPMENT_ASSESSMENT`. |
| `primary_concern` | String | Yes | Reason for the assessment. | Case-insensitive matching. Allowed values: `Speech Delay`, `Autism Assessment`, `Behavioural Concerns`, `Developmental Delay`, `Learning Difficulty`, `ADHD Assessment`, `Occupational Therapy`, `Physiotherapy`, `Feeding Issues`, `Other`. |
| `preferred_date` | Date | Yes | Proposed date (YYYY-MM-DD). | Cannot be in the past. |
| `preferred_time_slot` | String | Yes | Preferred timeframe label. | Required. Trimmed. e.g. `"10:00 AM"`. |
| `additional_notes` | String | No | Additional context / comments. | Max 1000 characters. Required if `primary_concern` is `"Other"`. |
| `referral_source` | String | No | Marketing or referral source. | Max 255 characters. Trimmed. |

#### Request Payload Example
```json
{
  "parent_first_name": "Suresh",
  "parent_last_name": "Kumar",
  "relationship_to_child": "Father",
  "mobile_number": "9876543210",
  "alternate_mobile_number": "",
  "email": "suresh.kumar@example.com",
  "child_first_name": "Aarav",
  "child_last_name": "Kumar",
  "date_of_birth": "2020-04-12",
  "gender": "Male",
  "appointment_type": "INITIAL_CONSULTATION",
  "primary_concern": "Speech Delay",
  "preferred_date": "2026-07-15",
  "preferred_time_slot": "10:00 AM",
  "additional_notes": "Needs slow instruction.",
  "referral_source": "Google"
}
```

#### Response Specifications

##### Response 201 Created
Returned on successful registration of the appointment request. Generates a unique tracking sequence number.
```json
{
  "success": true,
  "message": "Consultation request submitted successfully.",
  "data": {
    "request_number": "REQ-2026-000001",
    "status": "PENDING",
    "preferred_date": "2026-07-15",
    "preferred_time_slot": "10:00 AM"
  }
}
```

##### Response 400 Bad Request (Validation Failure)
Returned when input payload constraints are violated.
```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "mobile_number": [
      "Enter a valid mobile number."
    ]
  }
}
```

##### Response 409 Conflict (Duplicate Request)
Returned when an identical pending request already exists.
```json
{
  "success": false,
  "message": "A consultation request already exists for this child on the selected date."
}
```

---

## 4. Appointment Request Management API Specification

All endpoints in this section require token authentication via JWT (`Authorization: Bearer <token>`) and are restricted to users with `ADMIN` or `RECEPTIONIST` system roles. Requests by users with the `DOCTOR` role or any other role will be rejected with `403 Forbidden`.

### List Appointment Requests

Retrieve a paginated, filtered, and sorted list of all appointment requests submitted.

* **Endpoint:** `/appointments/requests/`
* **Method:** `GET`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist

#### Query Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `page` | Integer | No | Page number for pagination. Defaults to `1`. |
| `page_size` | Integer | No | Number of requests per page (min 1, max 100). Defaults to `10`. |
| `search` | String | No | Case-insensitive search on parent name, child name, mobile, email, and request number. |
| `status` | String | No | Filter by request status (`PENDING`, `APPROVED`, `REJECTED`). |
| `appointment_type`| String | No | Filter by appointment type (`INITIAL_CONSULTATION`, `DEVELOPMENT_ASSESSMENT`). |
| `preferred_date` | Date | No | Filter by preferred date (`YYYY-MM-DD`). |
| `primary_concern` | String | No | Filter by primary concern concern key. |
| `ordering` | String | No | Sort field. Allowed values: `created_at`, `-created_at`, `preferred_date`, `-preferred_date`, `parent_first_name`, `-parent_first_name`, `child_first_name`, `-child_first_name`. Defaults to `-created_at`. |

#### Response 200 OK Example
```json
{
  "success": true,
  "message": "Appointment requests fetched successfully.",
  "data": {
    "statistics": {
      "total_requests": 25,
      "pending_review": 10,
      "approved": 12,
      "rejected": 3
    },
    "results": [
      {
        "id": "764b8bbd-d34e-4e4f-b67a-115f0ebcd22f",
        "request_number": "REQ-2026-000001",
        "parent_first_name": "Rohan",
        "parent_last_name": "Sharma",
        "child_first_name": "Aarav",
        "child_last_name": "Sharma",
        "mobile_number": "9876543210",
        "email": "rohan@example.com",
        "preferred_date": "2026-07-06",
        "preferred_time_slot": "10:00 AM",
        "status": "PENDING",
        "created_at": "2026-06-26T14:00:00Z"
      }
    ],
    "pagination": {
      "count": 25,
      "page": 1,
      "page_size": 10,
      "total_pages": 3,
      "next": "https://api.neuroblooms.com/api/v1/appointments/requests/?page=2",
      "previous": null
    }
  }
}
```

---

### Retrieve Appointment Request Detail

Get complete details of a specific appointment request. Accessing this endpoint automatically registers an `APPOINTMENT_REQUEST_VIEWED` log entry.

* **Endpoint:** `/appointments/requests/{id}/`
* **Method:** `GET`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist

#### Response 200 OK Example
```json
{
  "success": true,
  "message": "Appointment request details retrieved successfully.",
  "data": {
    "id": "764b8bbd-d34e-4e4f-b67a-115f0ebcd22f",
    "request_number": "REQ-2026-000001",
    "parent_first_name": "Rohan",
    "parent_last_name": "Sharma",
    "relationship_to_child": "FATHER",
    "mobile_number": "9876543210",
    "alternate_mobile_number": "9876543211",
    "email": "rohan@example.com",
    "child_first_name": "Aarav",
    "child_last_name": "Sharma",
    "date_of_birth": "2020-05-15",
    "gender": "MALE",
    "appointment_type": "INITIAL_CONSULTATION",
    "primary_concern": "SPEECH_DELAY",
    "preferred_date": "2026-07-06",
    "preferred_time_slot": "10:00 AM",
    "additional_notes": "Needs patience.",
    "referral_source": "Google Search",
    "booking_source": "WEBSITE",
    "status": "PENDING",
    "rejection_reason": null,
    "reviewed_at": null,
    "reviewed_by": null,
    "created_at": "2026-06-26T14:00:00Z"
  }
}
```

---

### Get Appointment Request Statistics

Get aggregate counters for appointment requests in the system.

* **Endpoint:** `/appointments/requests/statistics/`
* **Method:** `GET`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist

#### Response 200 OK Example
```json
{
  "success": true,
  "message": "Appointment request statistics retrieved successfully.",
  "data": {
    "total_requests": 25,
    "pending_review": 10,
    "approved": 12,
    "rejected": 3
  }
}
```

---

### Approve Appointment Request

Approve a pending request. Approving a request transitions its status to `APPROVED`, records an `APPOINTMENT_REQUEST_APPROVED` activity log entry, and triggers a notification email to the parent.

* **Endpoint:** `/appointments/requests/{id}/approve/`
* **Method:** `POST`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist

#### Response 200 OK Example
```json
{
  "success": true,
  "message": "Appointment request approved successfully."
}
```

#### Response 409 Conflict (State Conflict)
Returned if the request is already approved, rejected, or in a status other than `PENDING`.
```json
{
  "success": false,
  "message": "Appointment request already approved."
}
```

---

### Reject Appointment Request

Reject a pending request. Transitioning the request status to `REJECTED` requires a rejection reason and records an `APPOINTMENT_REQUEST_REJECTED` activity log entry.

* **Endpoint:** `/appointments/requests/{id}/reject/`
* **Method:** `POST`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist

#### Request Payload Specification
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `reason` | String | Yes | Non-empty text stating the reason for rejection. |

#### Request Payload Example
```json
{
  "reason": "Duplicate submission of REQ-2026-000010."
}
```

#### Response 200 OK Example
```json
{
  "success": true,
  "message": "Appointment request rejected successfully."
}
```

---

### Retrieve Appointment Request Timeline

Get the chronological event lifecycle history of an appointment request based on activity log footprints.

* **Endpoint:** `/appointments/requests/{id}/timeline/`
* **Method:** `GET`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist

#### Response 200 OK Example
```json
{
  "success": true,
  "message": "Request timeline retrieved successfully.",
  "data": [
    {
      "event": "Submitted",
      "performed_by": "Website",
      "performed_at": "2026-06-26T14:00:00Z"
    },
    {
      "event": "Viewed",
      "performed_by": "receptionist@neuroblooms.com",
      "performed_at": "2026-06-26T14:15:00Z"
    },
    {
      "event": "Approved",
      "performed_by": "receptionist@neuroblooms.com",
      "performed_at": "2026-06-26T14:20:00Z"
    }
  ]
}
```

---

### Export Appointment Requests to CSV

Triggers a memory-efficient stream download of all filtered appointment requests in CSV format.

* **Endpoint:** `/appointments/requests/export/`
* **Method:** `GET`
* **Authentication:** Required (JWT Bearer)
* **Permissions:** Admin, Receptionist
* **Query Parameters:** Identical search/filters as the List endpoint.

#### Response Headers
```http
Content-Type: text/csv
Content-Disposition: attachment; filename="appointment_requests.csv"
```

---

## 5. Data Normalization & Sanitization Rules

The backend automatically applies cleanup rules on incoming payloads during deserialization to protect database integrity and ensure API flexibility:

1. **Whitespace Trimming**: Leading and trailing whitespaces are automatically stripped from all string parameter inputs.
2. **HTML/Script Tag Sanitization**: To protect the database and admin dashboard from Cross-Site Scripting (XSS) and injection vulnerabilities, all HTML and script elements are automatically stripped using Django's `strip_tags` sanitizer.
3. **Choice Fields Normalization**:
   To avoid validation errors due to casing discrepancies or display label inputs from frontends, normalization maps labels and lowercase characters to corresponding database constants:
   - **Relationship to Child**: Accepts `"mother"`/`"Mother"` -> maps internally to `"MOTHER"`; `"grandfather"`/`"Grandparent"` -> maps to `"GRANDPARENT"`, etc.
   - **Gender**: Accepts `"male"`/`"Male"` -> maps internally to `"MALE"`; `"Prefer Not To Say"` -> maps to `"PREFER_NOT_TO_SAY"`, etc.
   - **Appointment Type**: Accepts `"development_assessment"`/`"Development Assessment"` -> maps internally to `"DEVELOPMENT_ASSESSMENT"`.
   - **Primary Concern**: Accepts `"Speech Delay"`/`"speech_delay"` -> maps internally to `"SPEECH_DELAY"`.

---

## 6. Duplicate Prevention & Validation Logic

### Duplicate Request Prevention
Before registering the request, the service layer queries existing requests matching:
- `status` = `"PENDING"`
- `mobile_number` = matching input mobile number
- `child_first_name` = case-insensitive matching input child first name
- `child_last_name` = case-insensitive matching input child last name
- `preferred_date` = matching input preferred date

If a match is found, creation is aborted and a `409 Conflict` is returned. A request is not blocked if previous requests are marked as `APPROVED` or `REJECTED`.

### Cross-Field Validation
If `primary_concern` is normalized to `OTHER` (`"Other"`), the `additional_notes` field becomes strictly required and cannot be blank or null.

---

## 7. Best Practices, Throttling & Security Guidelines

1. **IP-Based Throttling**: Anonymous endpoints are restricted to `100 requests per day` per IP address to safeguard against Denial of Service (DoS) and programmatic form spam.
2. **PII Masking in Logs**: The backend is configured to comply with strict data privacy guidelines. System logging does not write raw email addresses or mobile numbers to disk. Sensitive details are masked using:
   - Email: `s*****h@example.com`
   - Mobile: `******3210`
3. **Transactional Integrity**: Sequential ID generation and request persistence are executed inside `transaction.atomic` blocks with `select_for_update` row locks on previous sequential keys to prevent ID collisions.
4. **Resilient Integrations**: The system triggers confirmation emails asynchronously (or safely within try-except blocks). Network or SMTP transmission issues do not fail the request creation API.
