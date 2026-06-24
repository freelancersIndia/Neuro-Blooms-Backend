# Neuro Blooms Healthcare Management System
## Accounts Module QA Testing Guide & Playbook

---

## Table of Contents
1. [Overview](#1-overview)
2. [Testing Environment & Postman Setup](#2-testing-environment--postman-setup)
    - [Postman Environment Configuration](#postman-environment-configuration)
    - [Automating Bearer Token Injection](#automating-bearer-token-injection)
3. [Core Test Cases Catalog](#3-core-test-cases-catalog)
    - [Group A: Authentication & Login Flow Tests](#group-a-authentication--login-flow-tests)
    - [Group B: OTP Lifecycle & Verification Tests](#group-b-otp-lifecycle--verification-tests)
    - [Group C: Password Management Tests](#group-c-password-management-tests)
    - [Group D: Profile Management Tests](#group-d-profile-management-tests)
    - [Group E: Active Session & Revocation Tests](#group-e-active-session--revocation-tests)
    - [Group F: User Administration & RBAC Tests](#group-f-user-administration--rbac-tests)
    - [Group G: Brute-Force & Account Lockout Tests](#group-g-brute-force--account-lockout-tests)
4. [Granular Test Case Specifications](#4-granular-test-case-specifications)
    - [TC-01: Successful Two-Factor Login Flow](#tc-01-successful-two-factor-login-flow)
    - [TC-02: Invalid Credentials & Failed Attempt Tracking](#tc-02-invalid-credentials--failed-attempt-tracking)
    - [TC-03: Brute-Force Lockout (5 Failed Attempts)](#tc-03-brute-force-lockout-5-failed-attempts)
    - [TC-04: Authenticating Against a Locked Account](#tc-04-authenticating-against-a-locked-account)
    - [TC-05: Expired OTP Code Verification](#tc-05-expired-otp-code-verification)
    - [TC-06: Reused/Replayed OTP Verification](#tc-06-reusedreplayed-otp-verification)
    - [TC-07: JWT Refresh Token Rotation & Session Sync](#tc-07-jwt-refresh-token-rotation--session-sync)
    - [TC-08: Revoked Session Invalidation](#tc-08-revoked-session-invalidation)
    - [TC-09: Duplicate Email Registration Constraint](#tc-09-duplicate-email-registration-constraint)
    - [TC-10: RBAC Endpoint Permission Violation](#tc-10-rbac-endpoint-permission-violation)
5. [Database Verification Queries](#5-database-verification-queries)
6. [Test Execution Checklist](#6-test-execution-checklist)
7. [Best Practices & Security Hardening Guidelines](#7-best-practices--security-hardening-guidelines)

---

## 1. Overview
This testing guide provides QA engineers, developers, and security auditors with a comprehensive playbook for verifying the **Neuro Blooms Accounts Module**. 

It outlines the environment setup, Postman automation guidelines, database validation queries, and a detailed catalog of positive, negative, and edge test cases. 

Following these procedures ensures that the authentication, authorization, session control, and account locking mechanisms function exactly as designed and remain secure against common vulnerability vectors.

---

## 2. Testing Environment & Postman Setup

To execute the test cases described in this playbook, set up your testing environment as follows:

### Postman Environment Configuration
Create a new environment in Postman (e.g., `Neuro Blooms - Local`) and define the following variables:

| Variable Name | Description | Example Local Value |
| :--- | :--- | :--- |
| `base_url` | The gateway API path | `http://localhost:8000/api/v1` |
| `admin_email` | Default administrator email | `admin@neuroblooms.com` |
| `admin_password`| Default administrator password | `AdminSecurePass123` |
| `user_email` | Test user email (Doctor/Receptionist)| `doctor@neuroblooms.com` |
| `user_password` | Test user password | `DoctorSecurePass123` |
| `access_token` | Automatically populated JWT Access Token| `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `refresh_token`| Automatically populated JWT Refresh Token| `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `signed_token` | Signed token for password resets | `doctor@neuroblooms.com:PASSWORD_RESET...`|
| `session_id` | UUID of an active device session | `8fa02b9e-648c-4f9e-a89e-49b82cce79d2` |
| `target_user_id`| UUID of a target user account | `e402fdbe-389d-4001-a189-e2b202c4819d` |

---

### Automating Bearer Token Injection
To avoid manually copying and pasting access tokens for authorized requests, configure your Postman collections to extract and inject tokens automatically.

#### Step 1: Configure the Login Collection
In your `Verify OTP` request, add the following script to the **Tests** tab. This script extracts the returned tokens and saves them to the active environment variables:

```javascript
if (pm.response.code === 200) {
    const jsonResponse = pm.response.json();
    if (jsonResponse.success && jsonResponse.data.access) {
        pm.environment.set("access_token", jsonResponse.data.access);
        pm.environment.set("refresh_token", jsonResponse.data.refresh);
        pm.test("Tokens successfully saved to environment.", function () {
            pm.expect(pm.environment.get("access_token")).to.not.be.null;
        });
    }
}
```

#### Step 2: Configure Collection Authorization
1. Right-click your Postman collection and select **Edit**.
2. Navigate to the **Authorization** tab.
3. Set the **Type** to `Bearer Token`.
4. In the **Token** field, input: `{{access_token}}`.
5. Click **Save**. All requests in this collection will now inherit the bearer token automatically.

---

## 3. Core Test Cases Catalog

---

### Group A: Authentication & Login Flow Tests
* **TC_AUTH_01**: Login with valid credentials triggers login OTP email (Positive).
* **TC_AUTH_02**: Login with invalid email address returns standard credential error (Negative).
* **TC_AUTH_03**: Login with incorrect password returns standard credential error (Negative).
* **TC_AUTH_04**: Login with missing required fields returns validation errors (Negative).
* **TC_AUTH_05**: Login attempt on a deactivated user account is blocked (Negative).

### Group B: OTP Lifecycle & Verification Tests
* **TC_OTP_01**: Verifying a valid login OTP returns JWT access and refresh tokens (Positive).
* **TC_OTP_02**: Verifying a valid email verification OTP marks the account as verified (Positive).
* **TC_OTP_03**: Verifying an invalid or mismatched OTP code is blocked (Negative).
* **TC_OTP_04**: Verifying an expired OTP code is blocked (Negative/Edge).
* **TC_OTP_05**: Reusing a previously verified OTP code is blocked (Negative/Edge).
* **TC_OTP_06**: Requesting a new OTP invalidates all previously issued outstanding codes for that purpose (Edge).

### Group C: Password Management Tests
* **TC_PASS_01**: Forgot password request sends a password reset OTP (Positive).
* **TC_PASS_02**: Resetting password using a valid cryptographic signed token succeeds (Positive).
* **TC_PASS_03**: Resetting password with mismatched password and confirmation fields is blocked (Negative).
* **TC_PASS_04**: Changing password while logged in by providing the correct current password succeeds (Positive).
* **TC_PASS_05**: Changing password with an incorrect current password is blocked (Negative).
* **TC_PASS_06**: Resetting password automatically terminates all active sessions for that user (Edge/Security).

### Group D: Profile Management Tests
* **TC_PROF_01**: Authenticated user can retrieve their own profile details (Positive).
* **TC_PROF_02**: Authenticated user can partially update their profile details (Positive).
* **TC_PROF_03**: Unauthenticated request to profile endpoints is blocked (Negative).
* **TC_PROF_04**: User cannot modify read-only profile fields (`id`, `email`, `roles`) via update (Negative/Edge).

### Group E: Active Session & Revocation Tests
* **TC_SESS_01**: User can list all their active device sessions (Positive).
* **TC_SESS_02**: User can revoke a specific active session, blacklisting its refresh token (Positive).
* **TC_SESS_03**: User can log out of all active sessions simultaneously (Positive).
* **TC_SESS_04**: Attempting to use a revoked session's refresh token to get a new access token is blocked (Negative/Security).

### Group F: User Administration & RBAC Tests
* **TC_ADMIN_01**: Admin user can list, search, and filter user accounts (Positive).
* **TC_ADMIN_02**: Admin user can create a new user account with assigned roles (Positive).
* **TC_ADMIN_03**: Admin user can update a user's details and role assignments (Positive).
* **TC_ADMIN_04**: Admin user can permanently delete a user account (Positive).
* **TC_ADMIN_05**: Non-admin user attempting to access user administration endpoints is blocked (Negative/Security).

### Group G: Brute-Force & Account Lockout Tests
* **TC_SEC_01**: Exceeding 5 failed login attempts within 15 minutes locks the account (Positive/Security).
* **TC_SEC_02**: Authenticating with correct credentials against a locked account is blocked (Negative/Security).
* **TC_SEC_03**: Admin user can manually unlock a locked user account (Positive).
* **TC_SEC_04**: Lock expires automatically after 15 minutes, allowing login (Positive/Edge).

---

## 4. Granular Test Case Specifications

---

### TC-01: Successful Two-Factor Login Flow
* **Description**: Verify that a user can authenticate by completing the password check and subsequent OTP verification.
* **Preconditions**: A user account exists (`doctor@neuroblooms.com` / `DoctorSecurePass123`) and is active.
* **Step 1: Primary Login Request**
  - **Method / Path**: `POST /auth/login/`
  - **Payload**:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "password": "DoctorSecurePass123"
    }
    ```
  - **Expected Result**: HTTP `200 OK`. The response confirms the OTP was sent:
    ```json
    {
      "success": true,
      "message": "Credentials verified. A login verification OTP has been sent to your email.",
      "data": null
    }
    ```
* **Step 2: Fetch OTP from Database / Console**
  - Extract the 6-digit OTP code generated for `doctor@neuroblooms.com` (e.g., `582910`).
* **Step 3: Verify OTP**
  - **Method / Path**: `POST /auth/verify-otp/`
  - **Payload**:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "otp_code": "582910",
      "purpose": "LOGIN_VERIFICATION"
    }
    ```
  - **Expected Result**: HTTP `200 OK`. Returns authorization tokens and user metadata:
    ```json
    {
      "success": true,
      "message": "OTP verified successfully.",
      "data": {
        "access": "eyJhbGciOiJIUz...",
        "refresh": "eyJhbGciOiJIUz...",
        "user": {
          "email": "doctor@neuroblooms.com",
          "first_name": "Jane",
          "last_name": "Doe",
          "roles": ["DOCTOR"]
        }
      }
    }
    ```

---

### TC-02: Invalid Credentials & Failed Attempt Tracking
* **Description**: Verify that logging in with an incorrect password returns a credential error and records a failed attempt in the database.
* **Preconditions**: A user account exists (`doctor@neuroblooms.com`).
* **Execution**:
  - **Method / Path**: `POST /auth/login/`
  - **Payload**:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "password": "WrongPassword123"
    }
    ```
  - **Expected Result**: HTTP `400 Bad Request`.
    ```json
    {
      "success": false,
      "message": "Invalid email or password.",
      "errors": null
    }
    ```
* **Database Verification Check**: Query the `accounts_failedloginattempt` table to confirm a failed attempt record was written, capturing the target email, source IP, timestamp, and the reason `INVALID_PASSWORD`.

---

### TC-03: Brute-Force Lockout (5 Failed Attempts)
* **Description**: Verify that an account is locked automatically after 5 consecutive failed login attempts within a 15-minute window.
* **Preconditions**: A user account exists (`doctor@neuroblooms.com`). The account is not currently locked.
* **Execution**:
  - Send 5 consecutive login requests to `POST /auth/login/` using the correct email but an incorrect password.
  - **Expected Result (Attempts 1-4)**: HTTP `400 Bad Request` with "Invalid email or password."
  - **Expected Result (Attempt 5)**: HTTP `400 Bad Request`. The system triggers the lockout:
    ```json
    {
      "success": false,
      "message": "Invalid email or password.",
      "errors": null
    }
    ```
* **Database Verification Check**:
  - Query `accounts_accountlock` to verify that an active lock record exists for the user, with `is_active = TRUE` and `unlock_at` set to exactly 15 minutes in the future.
  - Query `accounts_activitylog` to confirm an `ACCOUNT_LOCKED` event was written.

---

### TC-04: Authenticating Against a Locked Account
* **Description**: Verify that a locked account blocks all authentication attempts, even when correct credentials are provided.
* **Preconditions**: The account `doctor@neuroblooms.com` is locked.
* **Execution**:
  - **Method / Path**: `POST /auth/login/`
  - **Payload**:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "password": "DoctorSecurePass123"
    }
    ```
  - **Expected Result**: HTTP `400 Bad Request`. The system blocks the attempt and returns a lockout message:
    ```json
    {
      "success": false,
      "message": "This account is temporarily locked. Please try again in 15 minutes.",
      "errors": null
    }
    ```
* **Database Verification Check**: Query `accounts_failedloginattempt` to confirm the failed attempt was logged with the reason `ACCOUNT_LOCKED`.

---

### TC-05: Expired OTP Code Verification
* **Description**: Verify that the system blocks attempts to verify an expired OTP code.
* **Preconditions**: An OTP code was generated for `doctor@neuroblooms.com` but its expiration time (`expires_at`) has passed.
* **Execution**:
  - **Method / Path**: `POST /auth/verify-otp/`
  - **Payload**:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "otp_code": "123456",
      "purpose": "LOGIN_VERIFICATION"
    }
    ```
  - **Expected Result**: HTTP `400 Bad Request`.
    ```json
    {
      "success": false,
      "message": "Invalid or expired OTP code.",
      "errors": null
    }
    ```

---

### TC-06: Reused/Replayed OTP Verification
* **Description**: Verify that an OTP code is single-use and cannot be verified again after it has been marked as used.
* **Preconditions**: An OTP code was generated for `doctor@neuroblooms.com` (e.g., `881029`) and has already been verified successfully.
* **Execution**:
  - Submit the same verification payload a second time:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "otp_code": "881029",
      "purpose": "LOGIN_VERIFICATION"
    }
    ```
  - **Expected Result**: HTTP `400 Bad Request`.
    ```json
    {
      "success": false,
      "message": "Invalid or expired OTP code.",
      "errors": null
    }
    ```
* **Database Verification Check**: Query `accounts_otp` to verify that the record's `is_used` status is `TRUE`.

---

### TC-07: JWT Refresh Token Rotation & Session Sync
* **Description**: Verify that using a refresh token to get a new access token rotates the refresh token and updates the session JTI.
* **Preconditions**: The user has logged in and obtained a valid refresh token (Token A).
* **Execution**:
  - **Method / Path**: `POST /auth/refresh/`
  - **Payload**:
    ```json
    {
      "refresh": "<Token_A>"
    }
    ```
  - **Expected Result**: HTTP `200 OK`. Returns a new access token (Token B) and a new refresh token (Token C):
    ```json
    {
      "success": true,
      "message": "Token refreshed successfully.",
      "data": {
        "access": "<Access_Token_B>",
        "refresh": "<Refresh_Token_C>"
      }
    }
    ```
* **Database Verification Check**:
  - Decode Refresh Token C to extract its JTI claim.
  - Query `accounts_usersession` to verify that the session record's `refresh_token_jti` was updated to match the JTI of Refresh Token C.
  - Query the blacklist table to verify that the JTI of the original Refresh Token A is blacklisted.

---

### TC-08: Revoked Session Invalidation
* **Description**: Verify that once a session is revoked, its associated refresh token is blacklisted and cannot be used to refresh access.
* **Preconditions**: The user has logged in, created a session, and obtained a refresh token.
* **Step 1: Revoke the Session**
  - **Method / Path**: `DELETE /sessions/{session_id}/` (Authenticated)
  - **Expected Result**: HTTP `200 OK`.
* **Step 2: Attempt Token Refresh**
  - **Method / Path**: `POST /auth/refresh/`
  - **Payload**:
    ```json
    {
      "refresh": "<associated_refresh_token>"
    }
    ```
  - **Expected Result**: HTTP `401 Unauthorized`.
    ```json
    {
      "success": false,
      "message": "Session expired or revoked."
    }
    ```

---

### TC-09: Duplicate Email Registration Constraint
* **Description**: Verify that the system blocks attempts to create a user account using an email address that is already registered.
* **Preconditions**: An account with the email `doctor@neuroblooms.com` already exists.
* **Execution**:
  - **Method / Path**: `POST /users/` (Authenticated as Admin)
  - **Payload**:
    ```json
    {
      "email": "doctor@neuroblooms.com",
      "first_name": "Duplicate",
      "last_name": "User",
      "password": "SecurePassword123",
      "roles": ["DOCTOR"]
    }
    ```
  - **Expected Result**: HTTP `400 Bad Request`. The system returns a validation error for the duplicate email field:
    ```json
    {
      "success": false,
      "message": "Validation failed.",
      "errors": {
        "email": [
          "user with this email already exists."
        ]
      }
    }
    ```

---

### TC-10: RBAC Endpoint Permission Violation
* **Description**: Verify that users are blocked from accessing endpoints that do not match their assigned role.
* **Preconditions**: The user is authenticated but does **not** have the `ADMIN` role (e.g., they only have the `DOCTOR` role).
* **Execution**:
  - **Method / Path**: `GET /users/` (User Administration List)
  - **Headers**:
    ```http
    Authorization: Bearer <doctor_access_token>
    ```
  - **Expected Result**: HTTP `403 Forbidden`.
    ```json
    {
      "success": false,
      "message": "You do not have permission to perform this action.",
      "errors": null
    }
    ```

---

## 5. Database Verification Queries

During QA testing or automated integration test suites, use these SQL queries to verify the state of database records:

### 1. Check Active User Sessions
Verify if a user has active, unrevoked device sessions:
```sql
SELECT id, refresh_token_jti, ip_address, browser, device, is_active, last_activity 
FROM accounts_usersession 
WHERE user_id = 'e402fdbe-389d-4001-a189-e2b202c4819d' AND is_active = TRUE;
```

### 2. Verify Generated OTP Codes
Retrieve outstanding OTP codes generated for a user:
```sql
SELECT id, otp_code, purpose, expires_at, is_used 
FROM accounts_otp 
WHERE user_id = 'e402fdbe-389d-4001-a189-e2b202c4819d' 
ORDER BY created_at DESC 
LIMIT 5;
```

### 3. Review Active Account Locks
Check if a user is currently locked out of their account:
```sql
SELECT id, locked_at, unlock_at, reason, is_active 
FROM accounts_accountlock 
WHERE user_id = 'e402fdbe-389d-4001-a189-e2b202c4819d' 
  AND is_active = TRUE 
  AND unlock_at > NOW();
```

### 4. Count Failed Login Attempts
Count the number of failed login attempts recorded for an email address:
```sql
SELECT count(*) 
FROM accounts_failedloginattempt 
WHERE email = 'doctor@neuroblooms.com' 
  AND attempt_time >= NOW() - INTERVAL '15 minutes';
```

---

## 6. Test Execution Checklist

Before signing off on a release build of the Accounts Module, complete the following validation checklist:

- [ ] **Database Seed Check**: Verify that the `seed_roles` command executes successfully and populates the `ADMIN`, `DOCTOR`, and `RECEPTIONIST` roles.
- [ ] **Initial Admin Creation**: Verify that the `create_initial_admin` command creates the default administrator account successfully from environment variables.
- [ ] **Two-Factor Authentication**: Confirm that logging in requires both correct credentials **and** a valid OTP code.
- [ ] **Token Expiration**: Verify that access tokens expire after 24 hours and refresh tokens expire after 7 days.
- [ ] **Brute-Force Protection**: Confirm that 5 consecutive failed login attempts lock the account for 15 minutes.
- [ ] **Session Revocation**: Verify that logging out or revoking a session blacklists the refresh token and invalidates the session.
- [ ] **RBAC Restrictions**: Verify that non-admin users cannot access administrative endpoints (e.g., `/users/`, `/security-logs/`).
- [ ] **Audit Trail Logs**: Check that all critical events (logins, locks, role assignments) write detailed logs to the activity ledger.

---

## 7. Best Practices & Security Hardening Guidelines

1. **Keep Test Environments Isolated**: Always run QA and integration tests against a dedicated test database containing mock data. Never run test suites against production databases.
2. **Automate OTP Verification in Testing**: In non-production environments (like CI/CD pipelines), configure the email backend to log to the console or use a mock email service to allow automated tests to extract and verify OTP codes.
3. **Validate Hashing Algorithms**: Verify that password hashers match production configurations in the testing environment to ensure password verification speeds and security standards are tested accurately.
4. **Regularly Test Rollback Scenarios**: Verify that security state transitions (like account locking and session revocation) roll back correctly if an operation fails mid-execution, preventing accounts from getting stuck in invalid states.
