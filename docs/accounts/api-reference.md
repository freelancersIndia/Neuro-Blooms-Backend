# Neuro Blooms Healthcare Management System
## Accounts Module API Reference Specification

---

## Table of Contents
1. [Overview](#1-overview)
2. [Standard Request & Response Envelopes](#2-standard-request--response-envelopes)
    - [Success Response Envelope](#success-response-envelope)
    - [Error Response Envelope](#error-response-envelope)
    - [Validation Error Envelope](#validation-error-envelope)
    - [Session Expired/Revoked Exception Envelope](#session-expiredrevoked-exception-envelope)
3. [Authentication API Endpoint Specifications](#3-authentication-api-endpoint-specifications)
    - [Login (`POST /api/v1/auth/login/`)](#1-login)
    - [Logout (`POST /api/v1/auth/logout/`)](#2-logout)
    - [Token Refresh (`POST /api/v1/auth/refresh/`)](#3-token-refresh)
    - [Resend Verification (`POST /api/v1/auth/resend-verification/`)](#4-resend-verification)
4. [OTP API Endpoint Specifications](#4-otp-api-endpoint-specifications)
    - [Send OTP (`POST /api/v1/auth/send-otp/`)](#5-send-otp)
    - [Verify OTP (`POST /api/v1/auth/verify-otp/`)](#6-verify-otp)
5. [Password Management API Endpoint Specifications](#5-password-management-api-endpoint-specifications)
    - [Forgot Password (`POST /api/v1/auth/forgot-password/`)](#7-forgot-password)
    - [Reset Password (`POST /api/v1/auth/reset-password/`)](#8-reset-password)
    - [Change Password (`POST /api/v1/auth/change-password/`)](#9-change-password)
6. [Profile API Endpoint Specifications](#6-profile-api-endpoint-specifications)
    - [Get Profile (`GET /api/v1/profile/me/`)](#10-get-profile)
    - [Update Profile (`PATCH /api/v1/profile/me/`)](#11-update-profile)
7. [Session Management API Endpoint Specifications](#7-session-management-api-endpoint-specifications)
    - [List Active Sessions (`GET /api/v1/sessions/`)](#12-list-active-sessions)
    - [Revoke Specific Session (`DELETE /api/v1/sessions/{id}/`)](#13-revoke-specific-session)
    - [Logout All Sessions (`POST /api/v1/sessions/logout-all/`)](#14-logout-all-sessions)
8. [User Management API Endpoint Specifications (Admin Only)](#8-user-management-api-endpoint-specifications-admin-only)
    - [List Users (`GET /api/v1/users/`)](#15-list-users)
    - [User Statistics (`GET /api/v1/users/statistics/`)](#16-user-statistics)
    - [Create User (`POST /api/v1/users/`)](#17-create-user)
    - [Get User Detail (`GET /api/v1/users/{id}/`)](#18-get-user-detail)
    - [Update User (`PATCH /api/v1/users/{id}/`)](#19-update-user)
    - [Lock User Account (`POST /api/v1/users/{id}/lock/`)](#20-lock-user-account)
    - [Unlock User Account (`POST /api/v1/users/{id}/unlock/`)](#21-unlock-user-account)
    - [Delete User (`DELETE /api/v1/users/{id}/`)](#22-delete-user)
9. [Security Auditing API Endpoint Specifications (Admin Only)](#9-security-auditing-api-endpoint-specifications-admin-only)
    - [List Security Logs (`GET /api/v1/security-logs/`)](#23-list-security-logs)
10. [Role Persistence and System Roles Catalog](#10-role-persistence-and-system-roles-catalog)
11. [Best Practices & Security Hardening Guidelines](#11-best-practices--security-hardening-guidelines)

---

## 1. Overview
The Neuro Blooms Accounts Module APIs provide secure, standardized endpoints for user authentication, authorization, session control, user profile administration, and security audit logging. 

Built using **Django REST Framework (DRF)** and **SimpleJWT (JSON Web Tokens)**, the backend enforces standard API response envelopes, pagination schemas, granular role-based access controls (RBAC), and automatic security lockout mechanisms.

### Base URL
All API paths documented herein are relative to the project's gateway base URL:
```
https://api.neuroblooms.com/api/v1
```

---

## 2. Standard Request & Response Envelopes

The system wraps all responses in a standard JSON envelope to simplify client parsing.

### Success Response Envelope
Returned for successful operations (HTTP status codes `2xx`).
```json
{
  "success": true,
  "message": "Human-readable description of the completed operation.",
  "data": {}
}
```
*Note: The `data` key contains the requested payload (object, array, or `null`).*

### Error Response Envelope
Returned for general failures, authentication blocks, or client errors (HTTP status codes `400`, `401`, `403`, `404`, `500`).
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
    "email": [
      "Enter a valid email address."
    ],
    "password": [
      "This field is required."
    ]
  }
}
```

### Session Expired/Revoked Exception Envelope
Returned when a refresh token has been revoked, rotated, or blacklisted, or when the corresponding `UserSession` is marked inactive.
```json
{
  "success": false,
  "message": "Session expired or revoked."
}
```
*HTTP Status Code: `401 Unauthorized`*

---

## 3. Authentication API Endpoint Specifications

---

### 1. Login
#### Endpoint
`POST /auth/login/`

#### Authentication Requirement
`AllowAny` (No token required)

#### Description
Verifies user credentials (email and password). If valid, it generates and sends a 6-digit `LOGIN_VERIFICATION` OTP code to the user's registered email address. This endpoint does **not** return JWT tokens; it acts as the first step in the two-step verification flow.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Payload
```json
{
  "email": "doctor@neuroblooms.com",
  "password": "SecurePassword123"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Credentials verified. A login verification OTP has been sent to your email.",
  "data": null
}
```

#### Error Responses
* **Status**: `400 Bad Request` (Invalid Credentials or Account Locked)
```json
{
  "success": false,
  "message": "Invalid email or password.",
  "errors": null
}
```
```json
{
  "success": false,
  "message": "This account is temporarily locked. Please try again in 15 minutes.",
  "errors": null
}
```

#### Validation Rules
1. **email**: Must be a valid email string. Required.
2. **password**: Must be a string. Required.

#### Notes
* If the email does not exist in the system, the endpoint raises a `400 Bad Request` with "Invalid email or password" to prevent user enumeration.
* A failed login attempt is recorded in the database, which can trigger an automatic account lockout after 5 consecutive failures.

---

### 2. Logout
#### Endpoint
`POST /auth/logout/`

#### Authentication Requirement
`AllowAny` (The client passes the refresh token explicitly in the request body to allow logout even if the access token has expired).

#### Description
Terminates the user's active session. It blacklists the provided refresh token and sets the corresponding `UserSession` record's `is_active` status to `FALSE`.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Payload
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Successfully logged out.",
  "data": null
}
```

#### Error Response
* **Status**: `400 Bad Request`
```json
{
  "success": false,
  "message": "Invalid or expired refresh token.",
  "errors": null
}
```

---

### 3. Token Refresh
#### Endpoint
`POST /auth/refresh/`

#### Authentication Requirement
`AllowAny` (Passes refresh token in payload)

#### Description
Exchanges a valid, unexpired, and active refresh token for a new access token and a rotated refresh token. It validates that the token's JTI matches an active `UserSession` in the database, updates the session's active JTI, and updates the `last_activity` timestamp.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Payload
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Token refreshed successfully.",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access_payload...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_refresh_payload..."
  }
}
```

#### Error Response
* **Status**: `401 Unauthorized`
```json
{
  "success": false,
  "message": "Session expired or revoked."
}
```

#### Notes
* SimpleJWT is configured with `ROTATE_REFRESH_TOKENS = True`. This means the client receives a new refresh token on every refresh request, and the old one is rotated.
* If the session was revoked via another device or by an administrator, the refresh request will fail with a `401 Unauthorized` status.

---

### 4. Resend Verification
#### Endpoint
`POST /auth/resend-verification/`

#### Authentication Requirement
`AllowAny`

#### Description
Generates and resends an `EMAIL_VERIFICATION` OTP code to a registered user whose account is not yet verified (`is_verified = FALSE`).

#### Request Payload
```json
{
  "email": "doctor@neuroblooms.com"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "If the email exists and is unverified, a verification OTP has been sent.",
  "data": null
}
```

---

## 4. OTP API Endpoint Specifications

---

### 5. Send OTP
#### Endpoint
`POST /auth/send-otp/`

#### Authentication Requirement
`AllowAny`

#### Description
Generates and emails a 6-digit One-Time Password (OTP) for a specified purpose.

#### Request Payload
```json
{
  "email": "doctor@neuroblooms.com",
  "purpose": "EMAIL_VERIFICATION"
}
```
*Note: Valid choices for `purpose` are `LOGIN_VERIFICATION`, `PASSWORD_RESET`, and `EMAIL_VERIFICATION`.*

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "If the email exists, an OTP has been sent.",
  "data": null
}
```

#### Validation Rules
1. **email**: Must be a valid email format.
2. **purpose**: Must match one of the allowed choices.

---

### 6. Verify OTP
#### Endpoint
`POST /auth/verify-otp/`

#### Authentication Requirement
`AllowAny`

#### Description
Verifies the 6-digit OTP code submitted by the user. The behavior varies depending on the `purpose` parameter:
1. **LOGIN_VERIFICATION**: Completes the login flow. Creates an active `UserSession` and returns JWT tokens (access + refresh) along with user profile details.
2. **EMAIL_VERIFICATION**: Marks the user's account as verified (`is_verified = TRUE`) and returns success.
3. **PASSWORD_RESET**: Returns a cryptographically signed, short-lived verification token. The client must pass this token to the reset-password endpoint to authorize the password change.

#### Request Payload
```json
{
  "email": "doctor@neuroblooms.com",
  "otp_code": "481920",
  "purpose": "LOGIN_VERIFICATION"
}
```

#### Success Response (For LOGIN_VERIFICATION)
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "OTP verified successfully.",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "email": "doctor@neuroblooms.com",
      "first_name": "John",
      "last_name": "Doe",
      "profile_image": "http://localhost:8000/media/profiles/avatar.png",
      "roles": ["DOCTOR"]
    }
  }
}
```

#### Success Response (For EMAIL_VERIFICATION)
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Email verified successfully.",
  "data": null
}
```

#### Success Response (For PASSWORD_RESET)
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "OTP verified successfully.",
  "data": {
    "token": "doctor@neuroblooms.com:PASSWORD_RESET:1aeX92..."
  }
}
```

#### Error Response
* **Status**: `400 Bad Request`
```json
{
  "success": false,
  "message": "Invalid or expired OTP code.",
  "errors": null
}
```

---

## 5. Password Management API Endpoint Specifications

---

### 7. Forgot Password
#### Endpoint
`POST /auth/forgot-password/`

#### Authentication Requirement
`AllowAny`

#### Description
Initiates the password recovery flow. If the email exists, it generates a `PASSWORD_RESET` OTP and emails it to the user.

#### Request Payload
```json
{
  "email": "doctor@neuroblooms.com"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "If the email exists, a password reset OTP has been sent.",
  "data": null
}
```

#### Notes
* To prevent account harvesting, this endpoint returns a success message even if the email does not exist in the database.

---

### 8. Reset Password
#### Endpoint
`POST /auth/reset-password/`

#### Authentication Requirement
`AllowAny`

#### Description
Resets a user's password. Requires the cryptographically signed token returned by the `Verify OTP` endpoint (purpose: `PASSWORD_RESET`). On success, it updates the password and terminates all active sessions for that user to ensure account security.

#### Request Payload
```json
{
  "token": "doctor@neuroblooms.com:PASSWORD_RESET:1aeX92...",
  "new_password": "NewSecurePassword456",
  "confirm_password": "NewSecurePassword456"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Password has been reset successfully.",
  "data": null
}
```

#### Error Response
* **Status**: `400 Bad Request`
```json
{
  "success": false,
  "message": "Invalid or expired verification token.",
  "errors": null
}
```

---

### 9. Change Password
#### Endpoint
`POST /auth/change-password/`

#### Authentication Requirement
`IsAuthenticated` (Requires valid Bearer access token)

#### Description
Allows authenticated users to change their password by providing their current password.

#### Request Headers
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

#### Request Payload
```json
{
  "current_password": "SecurePassword123",
  "new_password": "NewSuperSecurePassword789",
  "confirm_password": "NewSuperSecurePassword789"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Password has been changed successfully.",
  "data": null
}
```

#### Error Response
* **Status**: `400 Bad Request` (Invalid current password or validation failure)
```json
{
  "success": false,
  "message": "Invalid current password.",
  "errors": null
}
```

---

## 6. Profile API Endpoint Specifications

---

### 10. Get Profile
#### Endpoint
`GET /profile/me/`

#### Authentication Requirement
`IsAuthenticated`

#### Description
Retrieves the profile details of the currently authenticated user.

#### Request Headers
```http
Authorization: Bearer <access_token>
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Profile retrieved successfully.",
  "data": {
    "id": "e402fdbe-389d-4001-a189-e2b202c4819d",
    "email": "doctor@neuroblooms.com",
    "phone_number": "1234567890",
    "first_name": "John",
    "last_name": "Doe",
    "profile_image": "/media/profiles/avatar.png",
    "is_verified": true,
    "roles": [
      "DOCTOR"
    ],
    "created_at": "2026-06-20T10:00:00Z",
    "updated_at": "2026-06-23T14:30:00Z"
  }
}
```

---

### 11. Update Profile
#### Endpoint
`PATCH /profile/me/`

#### Authentication Requirement
`IsAuthenticated`

#### Description
Partially updates the authenticated user's profile details. Users can update their `first_name`, `last_name`, `phone_number`, and `profile_image`. The `id`, `email`, `is_verified`, and `roles` fields are read-only and cannot be modified through this endpoint.

#### Request Payload
```json
{
  "first_name": "Johnny",
  "phone_number": "9876543210"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Profile updated successfully.",
  "data": {
    "id": "e402fdbe-389d-4001-a189-e2b202c4819d",
    "email": "doctor@neuroblooms.com",
    "phone_number": "9876543210",
    "first_name": "Johnny",
    "last_name": "Doe",
    "profile_image": "/media/profiles/avatar.png",
    "is_verified": true,
    "roles": [
      "DOCTOR"
    ],
    "created_at": "2026-06-20T10:00:00Z",
    "updated_at": "2026-06-24T01:00:00Z"
  }
}
```

---

## 7. Session Management API Endpoint Specifications

---

### 12. List Active Sessions
#### Endpoint
`GET /sessions/`

#### Authentication Requirement
`IsAuthenticated`

#### Description
Retrieves a list of all active sessions for the authenticated user, including IP addresses, browser information, and device types.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Active sessions retrieved successfully.",
  "data": [
    {
      "id": "8fa02b9e-648c-4f9e-a89e-49b82cce79d2",
      "ip_address": "192.168.1.50",
      "browser": "Chrome 125.0.0",
      "device": "Desktop",
      "login_at": "2026-06-24T00:30:00Z",
      "last_activity": "2026-06-24T01:10:00Z",
      "is_active": true
    }
  ]
}
```

---

### 13. Revoke Specific Session
#### Endpoint
`DELETE /sessions/{id}/`

#### Authentication Requirement
`IsAuthenticated`

#### Description
Revokes a specific active session by its UUID. This deactivates the session record and blacklists the associated JWT refresh token.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Session revoked successfully.",
  "data": null
}
```

#### Error Response
* **Status**: `404 Not Found` (If the session ID does not exist or does not belong to the user)
```json
{
  "success": false,
  "message": "Not found.",
  "errors": null
}
```

---

### 14. Logout All Sessions
#### Endpoint
`POST /sessions/logout-all/`

#### Authentication Requirement
`IsAuthenticated`

#### Description
Revokes all active sessions for the authenticated user, including the session used to make the request. All associated refresh tokens are blacklisted.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Successfully logged out of all active sessions.",
  "data": null
}
```

---

## 8. User Management API Endpoint Specifications (Admin Only)

*Note: Access to these endpoints requires a valid access token belonging to a user with the `ADMIN` role. Non-admin access returns a `403 Forbidden` response.*

---

### 15. List Users
#### Endpoint
`GET /users/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Lists all registered user accounts with pagination, search, and filters.

#### Query Parameters
* **page**: Page number (default: `1`).
* **page_size**: Number of records per page (default: `12`, max: `100`).
* **search**: Case-insensitive search query matching `first_name`, `last_name`, `email`, `phone_number`, or computed full name (`first_name + last_name`).
* **role**: Filter by role name (case-insensitive, e.g. `DOCTOR`, `RECEPTIONIST`). Supports only valid system seeded roles; invalid roles return empty results.
* **is_active**: Filter by active status (`true` or `false`). Invalid values return validation errors.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Users retrieved successfully.",
  "data": {
    "count": 124,
    "page": 1,
    "page_size": 12,
    "total_pages": 11,
    "next": "https://api.neuroblooms.com/api/v1/users/?page=2",
    "previous": null,
    "results": [
      {
        "id": "e402fdbe-389d-4001-a189-e2b202c4819d",
        "full_name": "John Doe",
        "email": "doctor@neuroblooms.com",
        "phone_number": "9876543210",
        "profile_image": null,
        "roles": [
          "DOCTOR"
        ],
        "is_verified": true,
        "is_active": true,
        "created_at": "2026-06-20T10:00:00Z"
      }
    ]
  }
}
```

---

### 16. User Statistics
#### Endpoint
`GET /users/statistics/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Returns a summary of system user counts by verification and active statuses for the administrator dashboard. Computes results efficiently using database aggregation queries.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User statistics retrieved successfully.",
  "data": {
    "total_users": 120,
    "verified_users": 97,
    "active_users": 102,
    "inactive_users": 18
  }
}
```

---

### 17. Create User
#### Endpoint
`POST /api/v1/users/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin` (Only ADMIN users can access this endpoint. Non-admin users will receive `403 Forbidden`).

#### Description
Creates a new system user, assigns one or more system roles, hashes their password, stores the profile image (if uploaded), and logs the administrative creation action.

#### Request Headers
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`
- `Content-Type: multipart/form-data` or `application/json` (multipart/form-data is required if uploading a `profile_image`)

#### Request Fields
| Field | Required | Type | Max Length / Constraints | Description / Notes |
| :--- | :---: | :--- | :--- | :--- |
| `first_name` | ✅ | String | 150 characters | First name of the user. |
| `last_name` | ✅ | String | 150 characters | Last name of the user. |
| `email` | ✅ | String (Email) | Must be unique | Unique, valid email address. |
| `phone_number` | ❌ | String | Must be unique if provided | Optional. Unique mobile or landline phone number. Blank values are stored as `null` in the DB. |
| `profile_image` | ❌ | File (Image) | Image format | Optional. User profile photo file. |
| `password` | ✅ | String | Minimum 8 characters | Validated against Django password validators. Automatically hashed using `set_password()`. |
| `roles` | ✅ | List of Strings | Cannot be empty, must be valid | Array of role names (e.g. `["ADMIN", "DOCTOR"]`). Duplicate roles are rejected. |
| `is_active` | ❌ | Boolean | Default: `true` | Indicates if the user account is active. |
| `is_verified` | ❌ | Boolean | Default: `false` | Indicates if the user's email is verified. |

*Note: The `is_staff` and `is_superuser` fields must never be accepted from the frontend. The backend always sets `is_staff = True` for all created users, and `is_superuser = False`.*

#### Password Hashing & Security
The password is never stored in plain text. It is checked against configured Django password validators and hashed using Django's standard `set_password()` helper.

#### Role Assignment
Roles passed in the request (e.g. `["ADMIN", "DOCTOR"]`) are validated for existence, deduplicated, and mapped to the user using the `UserRole` intermediate model.

#### Activity Logging
Every successful user creation logs an administrative action in the system audit logs:
- **Action**: `USER_CREATED`
- **Description**: `Admin <admin_email> created user <created_user_email>.`
- **Stored Data**: Admin User ID, Client IP Address, Action type, Description.

#### Request Example (JSON)
```json
{
    "first_name": "Krishna",
    "last_name": "Kolluri",
    "email": "krishna@gmail.com",
    "phone_number": "9876543210",
    "password": "SecurePassword@123",
    "roles": [
        "ADMIN",
        "DOCTOR"
    ],
    "is_active": true,
    "is_verified": false
}
```

#### Success Response
* **Status**: `201 Created`
* **Response Body**:
```json
{
    "success": true,
    "message": "User created successfully.",
    "data": {
        "id": "4bc9861e-128a-4cce-9a88-29be11ea2b7d",
        "first_name": "Krishna",
        "last_name": "Kolluri",
        "full_name": "Krishna Kolluri",
        "email": "krishna@gmail.com",
        "phone_number": "9876543210",
        "profile_image": "https://api.neuroblooms.com/media/profiles/krishna_profile.jpg",
        "roles": [
            "ADMIN",
            "DOCTOR"
        ],
        "is_active": true,
        "is_verified": false,
        "created_at": "2026-06-25T10:30:00Z"
    }
}
```

#### Error Responses
* **401 Unauthorized**:
  ```json
  {
      "success": false,
      "message": "Given token not valid for any token type",
      "errors": null
  }
  ```
* **403 Forbidden**:
  ```json
  {
      "success": false,
      "message": "You do not have permission to perform this action.",
      "errors": null
  }
  ```
* **400 Bad Request (Duplicate Email)**:
  ```json
  {
      "success": false,
      "message": "Validation failed.",
      "errors": {
          "email": [
              "User with this email already exists."
          ]
      }
  }
  ```
* **400 Bad Request (Invalid Role)**:
  ```json
  {
      "success": false,
      "message": "Validation failed.",
      "errors": {
          "roles": [
              "Invalid role: MANAGER"
          ]
      }
  }
  ```

---

### 18. Get User Detail
#### Endpoint
`GET /api/v1/users/{id}/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin`

#### Description
Retrieves full details for a specific user, including their name, contact information, role mapping, account statuses (such as whether they are active, verified, or locked), and failed login attempt counts.

#### Request Headers
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
    "success": true,
    "message": "User details retrieved successfully.",
    "data": {
        "id": "b04e5a0d-c197-46a3-ab13-0413a7d9359b",
        "first_name": "Doctor",
        "last_name": "User",
        "full_name": "Doctor User",
        "email": "doctor_mgmt@test.com",
        "phone_number": "1234567890",
        "profile_image": null,
        "roles": [
            "DOCTOR"
        ],
        "is_active": true,
        "is_verified": false,
        "is_locked": false,
        "failed_login_attempts": 0,
        "created_at": "2026-06-25T10:00:00Z"
    }
}
```

#### Error Responses
* **401 Unauthorized**:
  ```json
  {
      "success": false,
      "message": "Given token not valid for any token type",
      "errors": null
  }
  ```
* **403 Forbidden**:
  ```json
  {
      "success": false,
      "message": "You do not have permission to perform this action.",
      "errors": null
  }
  ```
* **404 Not Found**:
  ```json
  {
      "success": false,
      "message": "User not found.",
      "errors": null
  }
  ```

---

### 19. Update User
#### Endpoint
`PATCH /api/v1/users/{id}/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin`

#### Description
Partially updates a specific user account's profile details and role mappings. Unspecified fields remain unchanged. Logs a `USER_UPDATED` administrative event.

#### Request Headers
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`
- `Content-Type: application/json`

#### Request Fields
| Field | Required | Type | Constraints / Description |
| :--- | :---: | :--- | :--- |
| `first_name` | ❌ | String | First name. Strip whitespace. |
| `last_name` | ❌ | String | Last name. Strip whitespace. |
| `email` | ❌ | String (Email) | Must be unique. Stored in lowercase. |
| `phone_number` | ❌ | String | Must be unique. Blank is stored as `null`. |
| `profile_image` | ❌ | File (Image) | Optional profile picture update. |
| `roles` | ❌ | List of Strings | Replacing role mapping. Duplicate or invalid roles are rejected. |
| `is_active` | ❌ | Boolean | Account status. |
| `is_verified` | ❌ | Boolean | Verification status. |

#### Request Example (JSON)
```json
{
    "first_name": "UpdatedName",
    "roles": [
        "DOCTOR",
        "RECEPTIONIST"
    ],
    "phone_number": "1122334455"
}
```

#### Success Response
* **Status**: `200 OK`
* **Response Body**:
```json
{
    "success": true,
    "message": "User updated successfully.",
    "data": {
        "id": "b04e5a0d-c197-46a3-ab13-0413a7d9359b",
        "first_name": "UpdatedName",
        "last_name": "User",
        "full_name": "UpdatedName User",
        "email": "doctor_mgmt@test.com",
        "phone_number": "1122334455",
        "profile_image": null,
        "roles": [
            "DOCTOR",
            "RECEPTIONIST"
        ],
        "is_active": true,
        "is_verified": false,
        "is_locked": false,
        "failed_login_attempts": 0,
        "created_at": "2026-06-25T10:00:00Z"
    }
}
```

#### Error Responses
* **400 Bad Request (Duplicate Email or Phone)**:
  ```json
  {
      "success": false,
      "message": "Validation failed.",
      "errors": {
          "phone_number": [
              "User with this phone number already exists."
          ]
      }
  }
  ```

---

### 20. Lock User Account
#### Endpoint
`POST /api/v1/users/{id}/lock/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin`

#### Description
Manually locks a specific user account. This creates a permanent/long-term active lock preventing the user from logging in. Logs a `USER_LOCKED` administrative event.

#### Request Headers
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`

#### Success Response
* **Status**: `200 OK`
* **Response Body**:
```json
{
    "success": true,
    "message": "User account locked successfully.",
    "data": null
}
```

#### Error Responses
* **400 Bad Request (Already Locked)**:
  ```json
  {
      "success": false,
      "message": "User account is already locked.",
      "errors": null
  }
  ```

---

### 21. Unlock User Account
#### Endpoint
`POST /api/v1/users/{id}/unlock/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin`

#### Description
Manually unlocks a specific locked user account. This marks all active locks as inactive and resets the failed login attempt counter. Logs both `USER_UNLOCKED` (administrative ledger) and `ACCOUNT_UNLOCKED` (security log) events.

#### Request Headers
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`

#### Success Response
* **Status**: `200 OK`
* **Response Body**:
```json
{
    "success": true,
    "message": "User account unlocked successfully.",
    "data": null
}
```

#### Error Responses
* **400 Bad Request (Not Locked)**:
  ```json
  {
      "success": false,
      "message": "User account is not locked.",
      "errors": null
  }
  ```

---

### 22. Delete User
#### Endpoint
`DELETE /api/v1/users/{id}/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin`

#### Description
Permanently deletes the user account from the system. This triggers a cascade delete across intermediate tables, locks, and sessions. Enforces checks preventing self-deletion and superuser deletion. Logs a `USER_DELETED` administrative event.

#### Request Headers
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`

#### Success Response
* **Status**: `200 OK`
* **Response Body**:
```json
{
    "success": true,
    "message": "User deleted successfully.",
    "data": null
}
```

#### Error Responses
* **400 Bad Request (Self-Deletion or Superuser Block)**:
  ```json
  {
      "success": false,
      "message": "Administrators cannot delete their own account.",
      "errors": null
  }
  ```

---

## 9. Security Auditing API Endpoint Specifications (Admin Only)

---

### 23. List Security Logs
#### Endpoint
`GET /security-logs/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Retrieves the security audit ledger. Enforces pagination and supports filters.

#### Query Parameters
* **page**: Page number.
* **action**: Filter by specific activity type (e.g., `LOGIN`, `ACCOUNT_LOCKED`).
* **user_id**: Filter by the UUID of the user who performed the action.
* **date_from**: Filter logs created on or after this ISO timestamp (e.g., `2026-06-20T00:00:00Z`).
* **date_to**: Filter logs created on or before this ISO timestamp.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Security logs retrieved successfully.",
  "data": {
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "fa982cc2-d890-449e-b98a-a829be11ea2b",
        "user_email": "admin@neuroblooms.com",
        "action": "ACCOUNT_UNLOCKED",
        "description": "Account unlocked by administrator admin@neuroblooms.com.",
        "ip_address": "192.168.1.100",
        "created_at": "2026-06-24T01:21:00Z"
      },
      {
        "id": "7ac198a2-f900-4bce-928d-29be11ea2b4c",
        "user_email": "Anonymous",
        "action": "FAILED_LOGIN",
        "description": "Failed login attempt for user doctor@neuroblooms.com.",
        "ip_address": "203.0.113.5",
        "created_at": "2026-06-24T01:05:00Z"
      }
    ]
  }
}
```

---

## 10. Role and Permission Management API Endpoint Specifications (Admin Only)

*Note: Access to these endpoints requires a valid access token belonging to a user with the `ADMIN` role. Non-admin access returns a `403 Forbidden` response.*

---

### 24. List Roles
#### Endpoint
`GET /api/v1/roles/`

#### Authentication & Authorization
- **Authentication**: JWT Required (`Bearer <Token>`)
- **Permissions**: `IsAuthenticated` and `IsAdmin`

#### Description
Lists all registered roles with pagination, search, and filters. Returns annotated user and permission counts.

#### Query Parameters
* **page**: Page number (default: `1`).
* **page_size**: Number of records per page (default: `10`, max: `100`). Supporting values like `10`, `20`, `50`, `100`.
* **search**: Case-insensitive search query matching `name` or `description`.
* **status**: Filter by status (`active` or `inactive`).
* **type**: Filter by role type (`system` or `custom`).
* **has_users**: Filter by whether the role has assigned users (`true` or `false`).
* **created_after**: Filter roles created on or after this ISO date.
* **created_before**: Filter roles created on or before this ISO date.
* **date_range**: Shortcut filter (`today`, `7_days`, `30_days`).
* **ordering**: Order by `name`, `-name`, `created_at`, `-created_at`, `users_count`, `-users_count`, `permissions_count`, `-permissions_count`.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Roles retrieved successfully.",
  "data": {
    "count": 4,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "e402fdbe-389d-4001-a189-e2b202c4819d",
        "name": "DOCTOR",
        "description": "Clinical role for doctors.",
        "users_count": 15,
        "permissions_count": 5,
        "is_system": true,
        "is_active": true,
        "created_at": "2026-06-20T10:00:00Z",
        "updated_at": "2026-06-23T14:30:00Z",
        "can_delete": false,
        "can_edit": true
      }
    ]
  }
}
```

---

### 25. Role Statistics
#### Endpoint
`GET /api/v1/roles/statistics/`

#### Description
Returns a summary of role metrics for the dashboard.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Role statistics retrieved successfully.",
  "data": {
    "total_roles": 4,
    "active_roles": 4,
    "inactive_roles": 0,
    "system_roles": 3,
    "custom_roles": 1,
    "total_assigned_users": 16
  }
}
```

---

### 26. Create Role
#### Endpoint
`POST /api/v1/roles/`

#### Request Payload
```json
{
  "name": "Ward Manager",
  "description": "Manages ward operations and nurse scheduling.",
  "is_active": true,
  "permissions": [
    "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
  ]
}
```

#### Validation Rules
1. **name**: Required. Between 3 and 50 characters. Case-insensitive uniqueness.
2. **description**: Optional. Maximum 500 characters.
3. **permissions**: Required. Must be a non-empty list of valid Permission UUIDs.
4. **is_active**: Optional. Defaults to `true`.

#### Success Response
* **Status**: `201 Created`
* **Payload**:
```json
{
  "success": true,
  "message": "Role created successfully.",
  "data": {
    "id": "c782fdbe-389d-4001-a189-e2b202c4819d",
    "name": "Ward Manager",
    "description": "Manages ward operations and nurse scheduling.",
    "is_system": false,
    "is_active": true,
    "created_at": "2026-06-29T23:30:00Z",
    "updated_at": "2026-06-29T23:30:00Z",
    "permissions_count": 1,
    "users_count": 0
  }
}
```

---

### 27. Get Role Detail
#### Endpoint
`GET /api/v1/roles/{id}/`

#### Query Parameters
* **user_page**: Page number for assigned users pagination (default: `1`).
* **user_page_size**: Number of assigned users per page (default: `10`).

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Role details retrieved successfully.",
  "data": {
    "id": "e402fdbe-389d-4001-a189-e2b202c4819d",
    "name": "DOCTOR",
    "description": "Clinical role for doctors.",
    "is_system": true,
    "is_active": true,
    "created_at": "2026-06-20T10:00:00Z",
    "updated_at": "2026-06-23T14:30:00Z",
    "created_by": "System",
    "updated_by": "admin@test.com",
    "users_count": 15,
    "permissions_count": 5,
    "permissions": [
      {
        "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "name": "View Patients",
        "code": "view_patients",
        "group": "Patient Management",
        "description": "Can view patient records",
        "assigned": true
      }
    ],
    "assigned_users": {
      "count": 15,
      "page": 1,
      "page_size": 10,
      "total_pages": 2,
      "next": "https://api.neuroblooms.com/api/v1/roles/e402fdbe-389d-4001-a189-e2b202c4819d/?user_page=2&user_page_size=10",
      "previous": null,
      "results": [
        {
          "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
          "profile_image": null,
          "full_name": "Doctor User",
          "email": "doctor@test.com",
          "phone": "1234567890",
          "status": "Active",
          "last_login": "2026-06-29T18:00:00Z",
          "can_remove": true
        }
      ]
    }
  }
}
```

---

### 28. Update Role
#### Endpoint
`PATCH /api/v1/roles/{id}/`

#### Request Payload
```json
{
  "description": "Updated clinical role description.",
  "permissions": [
    "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"
  ]
}
```

#### Validation Rules
1. **System Roles**: If `is_system` is `true`, updating `name` is prohibited.
2. **Deactivation**: If `is_active` is set to `false` on the `ADMIN` role, it will be rejected to prevent lockout.

---

### 29. Delete Role (Soft Delete)
#### Endpoint
`DELETE /api/v1/roles/{id}/`

#### Description
Marks a role as deleted (`is_deleted = true`).

#### Validation Rules
1. **System Roles**: Cannot delete system roles (`is_system = true`).
2. **Assigned Users**: Cannot delete a role that has active user assignments.

---

### 30. Assign Permissions to Role
#### Endpoint
`POST /api/v1/roles/{id}/permissions/assign/`

#### Request Payload
```json
{
  "permission_ids": [
    "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"
  ]
}
```

---

### 31. Remove Permissions from Role
#### Endpoint
`POST /api/v1/roles/{id}/permissions/remove/`

#### Request Payload
```json
{
  "permission_ids": [
    "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"
  ]
}
```

#### Validation Rules
1. Cannot remove permissions from the `ADMIN` system role.

---

### 32. Assign Users to Role
#### Endpoint
`POST /api/v1/roles/{id}/users/assign/`

#### Request Payload
```json
{
  "user_ids": [
    "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  ]
}
```

---

### 33. Remove Users from Role
#### Endpoint
`POST /api/v1/roles/{id}/users/remove/`

#### Request Payload
```json
{
  "user_ids": [
    "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  ]
}
```

#### Validation Rules
1. Cannot remove the last user from the `ADMIN` system role.

---

### 34. User Statistics
#### Endpoint
`GET /api/v1/users/statistics/`

#### Description
Returns dashboard summary statistics including counts of active, inactive, locked, and role-specific users.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User statistics retrieved successfully.",
  "data": {
    "total_users": 48,
    "active_users": 44,
    "inactive_users": 4,
    "verified_users": 42,
    "unverified_users": 6,
    "locked_users": 2,
    "admins": 2,
    "doctors": 18,
    "receptionists": 6,
    "super_admins": 1,
    "new_users": 3
  }
}
```

---

### 35. Block User
#### Endpoint
`POST /api/v1/users/{id}/block/`

#### Description
Manually blocks a user account administratively.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User account blocked successfully.",
  "data": null
}
```

#### Validation Rules
1. Cannot block yourself.
2. Cannot block the final Super Admin or final Administrator.
3. Cannot block already blocked users.

---

### 36. Unlock User
#### Endpoint
`POST /api/v1/users/{id}/unlock/`

#### Description
Unlocks a user account (removes manual blocks and deactivates any active lockout from failed login attempts).

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User account unlocked successfully.",
  "data": null
}
```

#### Validation Rules
1. Cannot unlock already unlocked users.

---

### 37. Activate User
#### Endpoint
`POST /api/v1/users/{id}/activate/`

#### Description
Activates a deactivated user.

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "User account activated successfully.",
  "data": null
}
```

---

### 38. Deactivate User
#### Endpoint
`POST /api/v1/users/{id}/deactivate/`

#### Description
Deactivates a user account.

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "User account deactivated successfully.",
  "data": null
}
```

#### Validation Rules
1. Cannot deactivate yourself.
2. Cannot deactivate the final Super Admin or final Administrator.

---

### 39. Reset Password (Admin)
#### Endpoint
`POST /api/v1/users/{id}/reset-password/`

#### Description
Resets a user's password by an administrator.

#### Request Payload
```json
{
  "password": "NewSecurePassword123!"
}
```

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Password reset successfully.",
  "data": null
}
```

---

### 40. Assign Roles to User
#### Endpoint
`POST /api/v1/users/{id}/roles/assign/`

#### Request Payload
```json
{
  "roles": ["DOCTOR"]
}
```

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Roles assigned successfully.",
  "data": null
}
```

#### Validation Rules
1. Cannot assign duplicate roles.
2. Cannot assign invalid roles.

---

### 41. Remove Roles from User
#### Endpoint
`POST /api/v1/users/{id}/roles/remove/`

#### Request Payload
```json
{
  "roles": ["DOCTOR"]
}
```

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Roles removed successfully.",
  "data": null
}
```

#### Validation Rules
1. Cannot remove the last `ADMIN` role from the final administrator.

---

### 42. List User Sessions
#### Endpoint
`GET /api/v1/users/{id}/sessions/`

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Sessions retrieved successfully.",
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "results": [
      {
        "id": "c8d9e0f1-a2b3-c4d5-e6f7-0a1b2c3d4e5f",
        "device": "Desktop",
        "browser": "Chrome 120.0.0",
        "platform": "Windows",
        "ip_address": "127.0.0.1",
        "location": "Localhost",
        "login_time": "2026-06-30T00:00:00Z",
        "last_activity": "2026-06-30T00:05:00Z",
        "current_session": false,
        "can_revoke": true
      }
    ]
  }
}
```

---

### 43. Revoke User Session
#### Endpoint
`POST /api/v1/users/{id}/sessions/{session_id}/revoke/`

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Session revoked successfully.",
  "data": null
}
```

---

### 44. Logout User from All Devices
#### Endpoint
`POST /api/v1/users/{id}/logout-all/`

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "All sessions revoked successfully.",
  "data": null
}
```

---

### 45. List User Activity Logs
#### Endpoint
`GET /api/v1/users/{id}/activity/`

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Activity logs retrieved successfully.",
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "results": [
      {
        "timestamp": "2026-06-30T00:00:00Z",
        "performed_by": "admin@neuroblooms.com",
        "ip": "127.0.0.1",
        "action": "USER_UPDATED",
        "description": "Admin admin@neuroblooms.com updated user doctor@neuroblooms.com."
      }
    ]
  }
}
```

---

### 46. List User Security Logs
#### Endpoint
`GET /api/v1/users/{id}/security/`

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Security logs retrieved successfully.",
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "results": [
      {
        "timestamp": "2026-06-30T00:00:00Z",
        "performed_by": "doctor@neuroblooms.com",
        "ip": "127.0.0.1",
        "action": "LOGIN",
        "description": "User logged in successfully via two-step OTP verification."
      }
    ]
  }
}
```

---

### 47. Active Roles Dropdown
#### Endpoint
`GET /api/v1/roles/dropdown/`

#### Success Response
* **Status**: `200 OK`
```json
{
  "success": true,
  "message": "Active roles retrieved successfully.",
  "data": [
    {
      "id": "e4f5a6b7-c8d9-0e1f-2a3b-4c5d6e7f8a9b",
      "name": "ADMIN"
    },
    {
      "id": "f5a6b7c8-d90e-1f2a-3b4c-5d6e7f8a9b0c",
      "name": "DOCTOR"
    }
  ]
}
```

---

## 11. Best Practices & Security Hardening Guidelines

1. **Enforce HTTPS**: All API communication must be encrypted using TLS 1.3. Any HTTP requests must be redirected to HTTPS.
2. **Access Token Expiration**: Keep access tokens short-lived (e.g., 15-30 minutes) and use refresh token rotation to maintain sessions securely.
3. **Log Sensibly**: Never log passwords, OTP codes, or complete JWT payloads in application server logs.
4. **Rate Limiting**: Implement rate limiting at the API gateway level (e.g., Nginx or Cloudflare) for sensitive endpoints like `/auth/login/`, `/auth/verify-otp/`, and `/auth/forgot-password/` to prevent denial-of-service or brute-force attacks.
