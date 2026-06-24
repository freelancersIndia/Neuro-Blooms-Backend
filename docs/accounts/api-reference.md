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
    - [Create User (`POST /api/v1/users/`)](#16-create-user)
    - [Get User Detail (`GET /api/v1/users/{id}/`)](#17-get-user-detail)
    - [Update User (`PUT /api/v1/users/{id}/`)](#18-update-user)
    - [Partial Update User (`PATCH /api/v1/users/{id}/`)](#19-partial-update-user)
    - [Delete User (`DELETE /api/v1/users/{id}/`)](#20-delete-user)
    - [Unlock User Account (`POST /api/v1/users/{id}/unlock/`)](#21-unlock-user-account)
9. [Security Auditing API Endpoint Specifications (Admin Only)](#9-security-auditing-api-endpoint-specifications-admin-only)
    - [List Security Logs (`GET /api/v1/security-logs/`)](#22-list-security-logs)
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
* **page_size**: Number of records per page (default: `20`, max: `100`).
* **search**: Search query matching `first_name`, `last_name`, `email`, or `phone_number`.
* **role**: Filter by role name (case-insensitive, e.g. `doctor`).
* **is_active**: Filter by active status (`true` or `false`).

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "Users retrieved successfully.",
  "data": {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "e402fdbe-389d-4001-a189-e2b202c4819d",
        "email": "doctor@neuroblooms.com",
        "phone_number": "1234567890",
        "first_name": "John",
        "last_name": "Doe",
        "profile_image": null,
        "is_active": true,
        "is_verified": true,
        "role_names": [
          "DOCTOR"
        ],
        "created_at": "2026-06-20T10:00:00Z",
        "updated_at": "2026-06-23T14:30:00Z"
      }
    ]
  }
}
```

---

### 16. Create User
#### Endpoint
`POST /users/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Creates a new user account, assigns their roles, and sends a welcome email containing their credentials.

#### Request Payload
```json
{
  "email": "receptionist@neuroblooms.com",
  "first_name": "Alice",
  "last_name": "Smith",
  "password": "TempPassword123",
  "roles": [
    "RECEPTIONIST"
  ],
  "phone_number": "5551234567"
}
```

#### Success Response
* **Status**: `201 Created`
* **Payload**:
```json
{
  "success": true,
  "message": "User created successfully.",
  "data": {
    "id": "4bc9861e-128a-4cce-9a88-29be11ea2b7d",
    "email": "receptionist@neuroblooms.com",
    "phone_number": "5551234567",
    "first_name": "Alice",
    "last_name": "Smith",
    "profile_image": null,
    "is_active": true,
    "is_verified": false,
    "role_names": [
      "RECEPTIONIST"
    ],
    "created_at": "2026-06-24T01:15:00Z",
    "updated_at": "2026-06-24T01:15:00Z"
  }
}
```

---

### 17. Get User Detail
#### Endpoint
`GET /users/{id}/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User retrieved successfully.",
  "data": {
    "id": "4bc9861e-128a-4cce-9a88-29be11ea2b7d",
    "email": "receptionist@neuroblooms.com",
    "phone_number": "5551234567",
    "first_name": "Alice",
    "last_name": "Smith",
    "profile_image": null,
    "is_active": true,
    "is_verified": false,
    "role_names": [
      "RECEPTIONIST"
    ],
    "created_at": "2026-06-24T01:15:00Z",
    "updated_at": "2026-06-24T01:15:00Z"
  }
}
```

---

### 18. Update User
#### Endpoint
`PUT /users/{id}/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Replaces an existing user's details. All non-read-only fields must be provided in the payload.

#### Request Payload
```json
{
  "email": "receptionist@neuroblooms.com",
  "first_name": "Alice",
  "last_name": "Jones",
  "is_active": true,
  "is_verified": true,
  "roles": [
    "RECEPTIONIST",
    "DOCTOR"
  ],
  "phone_number": "5551234567"
}
```

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User updated successfully.",
  "data": {
    "id": "4bc9861e-128a-4cce-9a88-29be11ea2b7d",
    "email": "receptionist@neuroblooms.com",
    "phone_number": "5551234567",
    "first_name": "Alice",
    "last_name": "Jones",
    "profile_image": null,
    "is_active": true,
    "is_verified": true,
    "role_names": [
      "RECEPTIONIST",
      "DOCTOR"
    ],
    "created_at": "2026-06-24T01:15:00Z",
    "updated_at": "2026-06-24T01:20:00Z"
  }
}
```

---

### 19. Partial Update User
#### Endpoint
`PATCH /users/{id}/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Partially updates a user account. You only need to include the fields you want to change.

---

### 20. Delete User
#### Endpoint
`DELETE /users/{id}/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Permanently deletes the user account from the system. This triggers a cascade delete across session, lock, and role tables, and logs the deletion under a `USER_DISABLED` activity action.

#### Success Response
* **Status**: `200 OK`
* **Payload**:
```json
{
  "success": true,
  "message": "User account deleted successfully.",
  "data": null
}
```

---

### 21. Unlock User Account
#### Endpoint
`POST /users/{id}/unlock/`

#### Authentication Requirement
`IsAuthenticated` + `IsAdmin`

#### Description
Manually unlocks an account that was locked due to brute-force protection. It deactivates the user's active `AccountLock` record, clears their failed login attempts, and logs the action.

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

#### Error Response
* **Status**: `400 Bad Request` (If the user account is not currently locked)
```json
{
  "success": false,
  "message": "User is not locked.",
  "errors": null
}
```

---

## 9. Security Auditing API Endpoint Specifications (Admin Only)

---

### 22. List Security Logs
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

## 10. Role Persistence and System Roles Catalog

The system does **not** expose a dedicated `/roles/` CRUD endpoint. Roles are static and seeded during system deployment. They are managed through the User Management APIs.

### Available System Roles
1. **`ADMIN`**: Full administrative privileges. Can manage users, view security logs, unlock accounts, and modify system settings.
2. **`DOCTOR`**: Clinical access. Can view patient files, manage appointments, and write clinical notes.
3. **`RECEPTIONIST`**: Scheduling access. Can manage patient registrations and schedule appointments.

---

## 11. Best Practices & Security Hardening Guidelines

1. **Enforce HTTPS**: All API communication must be encrypted using TLS 1.3. Any HTTP requests must be redirected to HTTPS.
2. **Access Token Expiration**: Keep access tokens short-lived (e.g., 15-30 minutes) and use refresh token rotation to maintain sessions securely.
3. **Log Sensibly**: Never log passwords, OTP codes, or complete JWT payloads in application server logs.
4. **Rate Limiting**: Implement rate limiting at the API gateway level (e.g., Nginx or Cloudflare) for sensitive endpoints like `/auth/login/`, `/auth/verify-otp/`, and `/auth/forgot-password/` to prevent denial-of-service or brute-force attacks.
