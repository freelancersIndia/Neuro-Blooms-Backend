# Neuro Blooms Healthcare Management System
## Accounts Module Authentication Architecture & Flows

---

## Table of Contents
1. [Authentication Overview](#1-authentication-overview)
2. [Step-by-Step Login & Verification Flow](#2-step-by-step-login--verification-flow)
    - [Login Process Details](#login-process-details)
    - [Login Sequence Diagram](#login-sequence-diagram)
3. [JWT Architecture & Token Lifecycle](#3-jwt-architecture--token-lifecycle)
    - [Token Types & Lifetimes](#token-types--lifetimes)
    - [Token Claims & Payloads](#token-claims--payloads)
    - [Token Rotation & Blacklisting Mechanics](#token-rotation--blacklisting-mechanics)
4. [OTP Architecture & Verification Cryptography](#4-otp-architecture--verification-cryptography)
    - [Multi-Purpose OTP Design](#multi-purpose-otp-design)
    - [OTP Lifecycle States](#otp-lifecycle-states)
    - [Cryptographic Signing Tokens](#cryptographic-signing-tokens)
5. [Session Architecture & Device Tracking](#5-session-architecture--device-tracking)
    - [Active Session State Engine](#active-session-state-engine)
    - [Device & User-Agent Parsing](#device--user-agent-parsing)
    - [Session Revocation Mechanics](#session-revocation-mechanics)
6. [Security Hardening & Brute-Force Mitigation](#6-security-hardening--brute-force-mitigation)
    - [Failed Login Tracking Pipeline](#failed-login-tracking-pipeline)
    - [Automatic 15-Minute Account Locking](#automatic-15-minute-account-locking)
    - [Administrative Unlock Protocol](#administrative-unlock-protocol)
7. [Activity Logging Flow & Security Ledger](#7-activity-logging-flow--security-ledger)
    - [Logged Events catalog](#logged-events-catalog)
    - [Log Structuring & Immutability](#log-structuring--immutability)
8. [Best Practices & Security Hardening Guidelines](#8-best-practices--security-hardening-guidelines)

---

## 1. Authentication Overview
The **Neuro Blooms Accounts Module** uses a two-factor, state-aware authentication architecture to protect patient records and clinical operations. 

Rather than relying solely on passwords, the system mandates a two-step authentication process for all users. The first step verifies primary credentials (email and password), and the second step requires verifying a time-limited One-Time Password (OTP) sent to the user's registered email address. 

This architecture combines the convenience of stateless JSON Web Tokens (JWT) for API authorization with the security of database-backed active session tracking and automatic account locking.

---

## 2. Step-by-Step Login & Verification Flow

### Login Process Details

Authentication is divided into two distinct phases:

#### Phase 1: Primary Credential Verification (`POST /api/v1/auth/login/`)
1. The client submits the user's `email` and `password`.
2. The system queries the database for the user record.
3. **Security Check**: The system queries the `account_locks` table to verify the user is not currently locked out.
4. **Password Check**: The password hash is validated using the configured password hasher (e.g., PBKDF2).
5. **State Transition**: If the credentials are valid, the system generates a 6-digit numeric OTP with a `LOGIN_VERIFICATION` purpose and emails it to the user.
6. **Response**: The server returns a success message confirming the OTP was sent. No authorization tokens are issued yet.

#### Phase 2: Multi-Factor OTP Verification (`POST /api/v1/auth/verify-otp/`)
1. The client submits the user's `email`, the 6-digit `otp_code`, and the `purpose` (`LOGIN_VERIFICATION`).
2. The server validates the code against the active, unexpired record in the `otps` table.
3. On successful validation, the OTP is marked as used (`is_used = TRUE`).
4. The server generates a JWT token pair (Access and Refresh).
5. **Session Creation**: The server parses the request's `User-Agent` and `IP address`, creates an active session in the `UserSession` table, and binds the session to the refresh token's unique JTI claim.
6. **Logging**: The system logs a `LOGIN` action in the `ActivityLog` ledger.
7. **Response**: The server returns the JWT access token, rotated refresh token, and user profile metadata (including assigned roles).

---

### Login Sequence Diagram

The diagram below outlines the interaction sequence between the client, the application server components, the database, and the email service during a successful login flow.

```
Client               Gateway/View           AuthService            OTPService          EmailService         Database
  |                       |                      |                      |                    |                 |
  |--- 1. POST Login ---->|                      |                      |                    |                 |
  |    (email, password)  |--- 2. Validate ----->|                      |                    |                 |
  |                       |       Credentials    |--- 3. Check Lock ------------------------------------------>|
  |                       |                      |       (Not Locked)   |                    |                 |
  |                       |                      |<-- 4. Active Lock OK ---------------------------------------|
  |                       |                      |--- 5. Check Hash ------------------------------------------>|
  |                       |                      |<-- 6. Hash Valid -------------------------------------------|
  |                       |                      |--- 7. Generate OTP ->|                    |                 |
  |                       |                      |   (LOGIN_VERIFY)     |-- 8. Save OTP ---------------------->|
  |                       |                      |                      |-- 9. Trigger Mail->|                 |
  |                       |                      |                      |                    |-- 10. Send ---->|
  |                       |                      |                      |                    |   OTP Email     |
  |                       |<-- 11. Success ------|                      |                    |                 |
  |<-- 12. Credentials ---|    (OTP Sent)        |                      |                    |                 |
  |    Verified           |                      |                      |                    |                 |
  |                       |                      |                      |                    |                 |
  |--- 13. POST Verify -->|                      |                      |                    |                 |
  |    (Email, OTP Code)  |--- 14. Verify ------>|                      |                    |                 |
  |                       |        OTP           |--- 15. Verify OTP ----------------------------------------->|
  |                       |                      |        (Valid & Active)                   |                 |
  |                       |                      |<-- 16. OTP Confirmed ---------------------------------------|
  |                       |                      |--- 17. Mark Used ------------------------------------------>|
  |                       |                      |--- 18. Gen JWT -------------------------------------------->|
  |                       |                      |        (JTI Claim)   |                    |                 |
  |                       |                      |--- 19. Create Session ------------------------------------->|
  |                       |                      |--- 20. Log Activity --------------------------------------->|
  |                       |<-- 21. Auth Data ----|                      |                    |                 |
  |                       |    (Tokens & Roles)  |                      |                    |                 |
  |<-- 22. Success -------|                      |                      |                    |                 |
  |    (JWTs + Roles)     |                      |                      |                    |                 |
```

---

## 3. JWT Architecture & Token Lifecycle

The Accounts Module uses **JSON Web Tokens (JWT)** for stateless API authorization, backed by database session validation to allow immediate session revocation.

### Token Types & Lifetimes
1. **Access Token**:
   - **Purpose**: Authorizes individual API requests.
   - **Lifetime**: 24 hours (configured via `ACCESS_TOKEN_LIFETIME` in Django settings).
   - **Transmission**: Sent in the HTTP `Authorization` header as a Bearer token:
     ```http
     Authorization: Bearer <access_token>
     ```
2. **Refresh Token**:
   - **Purpose**: Exchanges for a new access token when the current one expires.
   - **Lifetime**: 7 days (configured via `REFRESH_TOKEN_LIFETIME` in Django settings).
   - **Transmission**: Sent in the request body to the `/auth/refresh/` or `/auth/logout/` endpoints.

### Token Claims & Payloads
The token payloads contain specific claims required for authorization and session tracking:

#### Access Token Payload
```json
{
  "token_type": "access",
  "exp": 1782294400,
  "jti": "7c19a82b-f900-4bce-928d-29be11ea2b4c",
  "user_id": "e402fdbe-389d-4001-a189-e2b202c4819d"
}
```

#### Refresh Token Payload
```json
{
  "token_type": "refresh",
  "exp": 1782812800,
  "jti": "8fa02b9e-648c-4f9e-a89e-49b82cce79d2",
  "user_id": "e402fdbe-389d-4001-a189-e2b202c4819d"
}
```
*Note: The `jti` (JWT ID) claim is a unique identifier for the token, which binds it to an active database session.*

### Token Rotation & Blacklisting Mechanics
To reduce the risk of token theft, the system enforces **Refresh Token Rotation**:
1. When a client requests a new access token using a refresh token, the server validates the incoming token.
2. If valid, the server returns a new access token **and a newly generated refresh token** (with a new `jti`).
3. The old refresh token's JTI is blacklisted in the `OutstandingToken` and `BlacklistedToken` tables to prevent replay attacks.
4. The active session record in the `UserSession` table is updated with the new refresh token's JTI to keep the session active.

```
       [Client]                                           [Server]
          |                                                   |
          |--- 1. POST /refresh/ (Refresh Token A) ---------->|
          |                                                   |-- 2. Verify Token A
          |                                                   |-- 3. Check Session (Active)
          |                                                   |-- 4. Blacklist Token A
          |                                                   |-- 5. Gen Access B & Refresh B
          |                                                   |-- 6. Update Session JTI to B
          |<-- 7. Response (Access B & Refresh B) ------------|
```

---

## 4. OTP Architecture & Verification Cryptography

### Multi-Purpose OTP Design
The One-Time Password (OTP) system handles three distinct verification workflows:
1. **`LOGIN_VERIFICATION`**: Acts as the second factor during the login process.
2. **`PASSWORD_RESET`**: Verifies the user's identity before allowing a password change.
3. **`EMAIL_VERIFICATION`**: Confirms ownership of the email address during registration.

### OTP Lifecycle States
Each OTP code transitions through a strict state machine to prevent bypass attacks:

```
  +-------------+       Trigger Event       +-------------+
  |  Uncreated  |-------------------------->|   Active    |
  +-------------+                           +------+------+
                                                   |
                             +---------------------+---------------------+
                             | Time > 15 Mins                            | Code Verified
                             v                                           v
                      +-------------+                             +-------------+
                      |   Expired   |                             |    Used     |
                      +-------------+                             +-------------+
```

### Cryptographic Signing Tokens
For workflows like password resets, verifying an OTP must not log the user in directly. Instead:
1. The user verifies the `PASSWORD_RESET` OTP.
2. If valid, the `VerifyOTPView` generates a cryptographically signed token using Django's `TimestampSigner`:
   ```python
   token = signer.sign("email@example.com:PASSWORD_RESET")
   ```
3. This token is signed using the server's `SECRET_KEY` and contains an encoded timestamp.
4. The client must submit this token to the `/auth/reset-password/` endpoint alongside the new password.
5. The server validates the token, extracts the email and purpose, checks that the token is under 15 minutes old, and updates the user's password. This prevents users from resetting passwords without completing the OTP step.

---

## 5. Session Architecture & Device Tracking

### Active Session State Engine
The `UserSession` table maintains the state of all active connections, providing a real-time ledger of devices authorized to access the APIs.

```
  User Authenticates (OTP Verified)
               │
               ▼
   ┌───────────────────────┐
   │  Session: ACTIVE      │◄────────────────────────┐
   │  is_active = TRUE     │                         │
   └───────────┬───────────┘                         │
               │                                     │ Token Refresh
               ├───────────────────┐                 │ (JTI Rotates)
               │ User Logs Out     │ Token Refreshed │
               ▼                   ▼                 │
   ┌───────────────────────┐   ┌─────────────────────┴─┐
   │  Session: INACTIVE    │   │  Session: ACTIVE      │
   │  is_active = FALSE    │   │  is_active = TRUE     │
   └───────────────────────┘   │  (New JTI Applied)    │
                               └───────────────────────┘
```

### Device & User-Agent Parsing
When a session is created, the server parses the request's `HTTP_USER_AGENT` header to extract readable device information:
* **Browser Parsing**: Identifies the browser family and version (e.g., `Chrome 125.0.0`, `Safari 17.2`).
* **Device Categorization**: Classifies the hardware type as `Desktop`, `Mobile`, `Tablet`, or `Bot` to help users identify their connected devices.

### Session Revocation Mechanics
If a user revokes a session (via the `/sessions/{id}/` DELETE endpoint) or logs out of all devices:
1. The targeted `UserSession` record's `is_active` flag is set to `FALSE`.
2. The refresh token's JTI associated with that session is added to the system blacklist.
3. The next time the client attempts to refresh their token or make an API request using that session, the validation check fails, and the client is prompted to log in again.

---

## 6. Security Hardening & Brute-Force Mitigation

### Failed Login Tracking Pipeline
To mitigate brute-force and credential-stuffing attacks, the system tracks authentication failures through a real-time monitoring pipeline:

```
  Login Request Received
            │
            ▼
    Validate Password
      /          \
  (Valid)      (Invalid)
    /              \
  Proceed           Record Failed Attempt in DB
  to OTP            (Email, IP, Timestamp, Reason)
                            │
                            ▼
                    Count Failed Attempts
                    for Email in Last 15 Mins
                           /       \
                       (< 5)      (>= 5)
                        /             \
                   Return 400       Trigger Account Lock (15 Min)
                   "Invalid..."     Log ACCOUNT_LOCKED Event
                                    Return 400 "Account Locked..."
```

### Automatic 15-Minute Account Locking
1. When 5 or more failed login attempts are recorded for an email address within a rolling 15-minute window, the system creates an `AccountLock` record.
2. The account status is set to locked for exactly 15 minutes.
3. Any subsequent authentication requests during this window are blocked immediately at the database level, returning a `400 Bad Request` explaining that the account is temporarily locked.
4. Once the 15-minute window expires, the lock is treated as inactive, and the user can attempt to log in again.

### Administrative Unlock Protocol
An administrator can manually unlock a locked user account:
1. The administrator calls the `unlock` action on the user's admin endpoint.
2. The system deactivates the active `AccountLock` record (`is_active = FALSE`).
3. The system deletes all `FailedLoginAttempt` records associated with the user's email to reset the failure counter.
4. An `ACCOUNT_UNLOCKED` event is logged in the security ledger, tracking which administrator performed the unlock.

---

## 7. Activity Logging Flow & Security Ledger

### Logged Events Catalog
The system records a comprehensive set of administrative and security events in the `ActivityLog` ledger:

| Event Action | Triggering Condition | Captured Metadata |
| :--- | :--- | :--- |
| `LOGIN` | Successful two-factor OTP verification | User ID, IP, User-Agent |
| `LOGOUT` | User logs out, blacklisting their token | User ID, IP |
| `FAILED_LOGIN` | Incorrect password or non-existent email | Target Email, IP, Reason |
| `PASSWORD_RESET` | Successful password change via reset token | User ID, IP |
| `PASSWORD_CHANGED` | User updates password while logged in | User ID, IP |
| `OTP_VERIFIED` | Successful validation of any OTP code | User ID, IP, Purpose |
| `USER_CREATED` | Admin creates a new user account | Admin ID, Target User, IP |
| `USER_UPDATED` | Admin or user updates profile details | Operator ID, Target User, IP |
| `USER_DISABLED` | Admin deactivates or deletes an account | Admin ID, Target Email, IP |
| `ACCOUNT_LOCKED` | System locks account due to failure threshold | User ID, Lock Expiry, IP |
| `ACCOUNT_UNLOCKED` | Admin manually unlocks a locked account | Admin ID, Unlocked User, IP |
| `SESSION_REVOKED` | User terminates a session or logs out all | User ID, Session ID, IP |
| `ROLE_SEEDED` | System roles are seeded during deployment | System-level event |
| `INITIAL_ADMIN` | Initial admin account is created via CLI | System-level event |
| `EMAIL_VERIFIED` | User successfully verifies their email address | User ID, IP |

### Log Structuring & Immutability
To ensure the integrity of the security ledger, the database enforces strict write-only rules on the `activity_logs` table:
* **No Modifying**: The application code does not expose any update or delete interfaces for activity logs.
* **Preserving Logs**: If a user account is deleted, the corresponding log records are kept, and the `user_id` foreign key is set to `NULL` (`ON DELETE SET_NULL`). The text description retains the user's email address to preserve the historical audit trail.

---

## 8. Best Practices & Security Hardening Guidelines

1. **Secure Session Verification**: The token refresh view must check both the JWT signature and the active session status in the database to prevent revoked tokens from being used.
2. **Brute-Force Protection**: The failed login tracking pipeline must run on every authentication failure, including attempts targeting non-existent emails, to detect distributed brute-force scans.
3. **Immutability of Audit Logs**: Ensure that database permissions restrict standard application users from modifying or deleting records in the `activity_logs` table.
4. **Token Expiration Tuning**: Regularly review access and refresh token lifetimes to maintain an optimal balance between security and user convenience.
