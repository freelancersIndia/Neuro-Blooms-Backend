# Neuro Blooms Healthcare Management System
## Accounts Module Entity-Relationship Diagram (ERD) Documentation

---

## Table of Contents
1. [Overview](#1-overview)
2. [High-Level Conceptual ERD](#2-high-level-conceptual-erd)
3. [Detailed Physical ERD](#3-detailed-physical-erd)
4. [Relationship Explanations & Business Rules](#4-relationship-explanations--business-rules)
    - [User to Role (Many-to-Many via UserRole)](#user-to-role-many-to-many-via-userrole)
    - [User to OTP (One-to-Many)](#user-to-otp-one-to-many)
    - [User to UserSession (One-to-Many)](#user-to-usersession-one-to-many)
    - [User to AccountLock (One-to-Many)](#user-to-accountlock-one-to-many)
    - [User to ActivityLog (One-to-Many, Soft Association)](#user-to-activitylog-one-to-many-soft-association)
    - [FailedLoginAttempt (Loosely Coupled, Raw Email Tracking)](#failedloginattempt-loosely-coupled-raw-email-tracking)
5. [Referential Integrity & Deletion Behaviors](#5-referential-integrity--deletion-behaviors)
6. [Future Expansion Recommendations](#6-future-expansion-recommendations)
    - [Adding Permissions at the Role Level](#adding-permissions-at-the-role-level)
    - [Tenant-Level isolation (Multi-clinic partitioning)](#tenant-level-isolation-multi-clinic-partitioning)
7. [Best Practices & Maintenance Guidelines](#7-best-practices--maintenance-guidelines)

---

## 1. Overview
In an enterprise healthcare application, understanding how data entities relate to one another is vital for maintaining data consistency, application security, and system performance. The **Neuro Blooms Accounts Module** uses a relational database structure designed to enforce identity integrity while isolating security metadata to prevent side-channel leaks.

This document provides a conceptual and physical mapping of the relationships within the Accounts database. It details the cardinalities, structural dependencies, and deletion policies that protect sensitive user and session data.

---

## 2. High-Level Conceptual ERD
The diagram below shows the conceptual entities and their relationships. The relationships represent how business logic binds these elements together (e.g., a User owns multiple Sessions, whereas Users and Roles are joined through User Roles).

```
                               +---------------+
                               |     Roles     |
                               +-------+-------+
                                       | 1
                                       |
                                       | 0..N
                               +-------v-------+
                               |   UserRoles   |
                               +-------^-------+
                                       | 0..N
                                       |
                                       | 1
+--------------------+         +-------+-------+         +--------------------+
|    ActivityLogs    |o--------+     Users     +--------o|        OTPs        |
| (Soft Association) |   0..N  +---+---+---+---+   0..N  +--------------------+
+--------------------+             |   |   |
                                   |   |   |
                             0..N  |   |   | 0..N
             +---------------------+   |   +---------------------+
             |                         |                         |
     +-------v--------+                | 0..N            +-------v--------+
     |  UserSessions  |                |                 |  AccountLocks  |
     +----------------+                |                 +----------------+
                               +-------v-------+
                               |  FailedLogins |
                               | (Loose Email) |
                               +---------------+
```

---

## 3. Detailed Physical ERD
This physical diagram documents the database tables, fields, data types, primary keys (`PK`), foreign keys (`FK`), and unique constraints. It represents the exact physical structure of the PostgreSQL schema.

```
+------------------------------------+          +------------------------------------+
|            accounts_user           |          |            accounts_role           |
+------------------------------------+          +------------------------------------+
| PK | id           : UUID           |          | PK | id           : UUID           |
| UK | email        : VARCHAR(254)   |          | UK | name         : VARCHAR(50)    |
| UK | phone_number : VARCHAR(20)    |          |    | description  : TEXT           |
|    | password     : VARCHAR(128)   |          |    | created_at   : TIMESTAMPTZ    |
|    | first_name   : VARCHAR(150)   |          +-----------------+------------------+
|    | last_name    : VARCHAR(150)   |                            | 1
|    | profile_image: VARCHAR(100)   |                            |
|    | is_active    : BOOLEAN        |                            |
|    | is_verified  : BOOLEAN        |                            |
|    | is_staff     : BOOLEAN        |                            | 0..N
|    | is_superuser : BOOLEAN        |          +-----------------v------------------+
|    | last_login   : TIMESTAMPTZ    |          |          accounts_userrole         |
|    | created_at   : TIMESTAMPTZ    |          +------------------------------------+
|    | updated_at   : TIMESTAMPTZ    |          | PK | id          : UUID            |
|    +--------------+----------------+          | FK | user_id     : UUID   [Cascade]|
|                   |                |          | FK | role_id     : UUID   [Cascade]|
|                   |                |          | UK | (user_id, role_id)            |
|                   | 1              | 1        |    | assigned_at : TIMESTAMPTZ     |
|                   |                |          +-----------------^------------------+
|                   |                |                            |
|                   |                +----------------------------+ 0..N
|                   | 1
|                   +----------------------------------+
|                   |                                  |
|                   | 1                                | 1
|           +-------v--------+                 +-------v--------+
|           |  accounts_otp  |                 | accounts_lock  |
|           +----------------+                 +----------------+
|           | PK | id        |                 | PK | id        |
|           | FK | user_id   |                 | FK | user_id   |
|           |    | otp_code  |                 |    | locked_at |
|           |    | purpose   |                 |    | unlock_at |
|           |    | expires_at|                 |    | reason    |
|           |    | is_used   |                 |    | is_active |
|           |    | created_at|                 +----------------+
|           +----------------+
|                   |
|                   | 1
|           +-------v--------+
|           |accounts_session|
|           +----------------+
|           | PK | id        |
|           | FK | user_id   |
|           |    | jti       |
|           |    | ip        |
|           |    | user_agent|
|           |    | browser   |
|           |    | device    |
|           |    | login_at  |
|           |    | activity  |
|           |    | is_active |
|           +----------------+
|                   |
|                   | 1 (Soft / ON DELETE SET NULL)
|           +-------v--------+                 +------------------------------------+
|           |  accounts_log  |                 |    accounts_failedloginattempt     |
|           +----------------+                 +------------------------------------+
|           | PK | id        |                 | PK | id           : UUID           |
|           | FK | user_id   |                 |    | email        : VARCHAR(254)   |
|           |    | action    |                 |    | ip_address   : VARCHAR(45)    |
|           |    | desc      |                 |    | attempt_time : TIMESTAMPTZ    |
|           |    | ip        |                 |    | reason       : VARCHAR(50)    |
|           |    | created_at|                 +------------------------------------+
|           +----------------+                 (Loosely coupled - No foreign keys)
+------------------------------------+
```

---

## 4. Relationship Explanations & Business Rules

### User to Role (Many-to-Many via UserRole)
* **Cardinality**: `Users (1) <---> (0..N) UserRoles (0..N) <---> (1) Roles`
* **Why it exists**: In clinical environments, administrative and medical duties often overlap. A doctor might need medical access (`DOCTOR` role) but also require scheduling permissions (`RECEPTIONIST` role) or system administrative access (`ADMIN` role). Modeling this as a Many-to-Many relationship allows assigning multiple roles to a single user.
* **Relationship Rules**:
  - A user can be assigned zero, one, or multiple roles.
  - A role can belong to zero, one, or many users.
  - Role assignments are recorded in `accounts_userrole` with a timestamp (`assigned_at`), providing an audit trail of when privileges were granted.
  - The combination of `user_id` and `role_id` must be unique (`unique_together = ('user', 'role')`).

### User to OTP (One-to-Many)
* **Cardinality**: `Users (1) ----> (0..N) OTPs`
* **Why it exists**: Users require multi-factor authentication (OTP) at login, email verification upon account registration, and password reset codes when credentials are forgotten. Since these events occur repeatedly over the lifespan of an account, a user can have many historical OTP records.
* **Relationship Rules**:
  - Each OTP record belongs to exactly one user.
  - An OTP record stores its purpose (`LOGIN_VERIFICATION`, `PASSWORD_RESET`, `EMAIL_VERIFICATION`) to prevent a code generated for one action from being exploited for another.
  - Expired or verified OTPs are marked `is_used = TRUE` and kept for audit purposes, or swept by a periodic maintenance job.

### User to UserSession (One-to-Many)
* **Cardinality**: `Users (1) ----> (0..N) UserSessions`
* **Why it exists**: Users can log in from multiple devices simultaneously (e.g., a desktop terminal in a clinic, a tablet during patient rounds, and a mobile phone). The system tracks each active connection separately.
* **Relationship Rules**:
  - A user can have multiple concurrent active sessions.
  - Each session records its associated JWT refresh token JTI, client IP address, parsed browser metadata, and device type.
  - If a user logs out, that specific session is deactivated. If they select "Logout All," all active session records for that user are marked inactive.

### User to AccountLock (One-to-Many)
* **Cardinality**: `Users (1) ----> (0..N) AccountLocks`
* **Why it exists**: Accounts are locked automatically after 5 consecutive failed login attempts to prevent brute-force attacks. An account may be locked and unlocked multiple times over its lifetime.
* **Relationship Rules**:
  - An account lock is bound to one user.
  - An active lock blocks all authentication attempts for that user.
  - Admin unlocking deactivates the lock record (`is_active = FALSE`), allowing the user to attempt login again immediately.

### User to ActivityLog (One-to-Many, Soft Association)
* **Cardinality**: `Users (0..1) ----> (0..N) ActivityLogs`
* **Why it exists**: Every critical action must be logged for security compliance. This includes administrative actions (creating a user), authentication actions (logins, logouts), and security actions (session revocations).
* **Relationship Rules**:
  - An activity log is linked to the user who performed the action.
  - If the action is anonymous (e.g., a failed login with a non-existent email), the `user_id` is recorded as `NULL`.
  - To maintain an unalterable audit trail, deleting a user must not delete their activity logs. Instead, the database engine sets `user_id` to `NULL` (`ON DELETE SET_NULL`), preserving the log entry and its text description (which contains the user's email at the time of the action).

### FailedLoginAttempt (Loosely Coupled, Raw Email Tracking)
* **Cardinality**: `No Foreign Key Relationship`
* **Why it exists**: A failed login attempt might target an email that does not exist in the system. Bypassing foreign key constraints ensures the system can log all malicious probes without throwing database integrity errors.
* **Relationship Rules**:
  - Stores the raw `email` string and source `ip_address` for every authentication failure.
  - The security service queries these logs using a sliding 15-minute window to determine if the threshold has been exceeded, triggering an account lock on the matching user.

---

## 5. Referential Integrity & Deletion Behaviors

The Accounts database implements strict referential integrity policies to prevent orphaned rows while protecting historical security audit trails.

| Target Table | Source / Parent Table | FK Column | Deletion Behavior (`ON DELETE`) | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `user_roles` | `users` | `user_id` | `CASCADE` | If a user is deleted, their role assignments are removed. |
| `user_roles` | `roles` | `role_id` | `CASCADE` | If a system role is deleted, all user assignments are removed. |
| `otps` | `users` | `user_id` | `CASCADE` | Outstanding OTP codes are deleted if the owning user is removed. |
| `user_sessions` | `users` | `user_id` | `CASCADE` | Active sessions are terminated if the user is deleted. |
| `account_locks` | `users` | `user_id` | `CASCADE` | Account locks are removed if the user is deleted. |
| `activity_logs` | `users` | `user_id` | `SET_NULL` | **Critical Security Rule**: Deleting a user must not alter or erase the historical audit ledger. The log remains intact, and the `user_id` is set to `NULL`. |

---

## 6. Future Expansion Recommendations

As the Neuro Blooms application scales, the database schema can be expanded to support more complex enterprise requirements:

### Adding Permissions at the Role Level
Currently, permissions are checked in code based on role names (e.g., `has_role('ADMIN')`). To make authorization dynamic, a `permissions` table can be added, linking to `roles` via a Many-to-Many join table.

```
+-------------------+       1        0..N      +-------------------+
|     permissions   +--------------------------+  role_permissions |
+-------------------+                          +---------+---------+
                                                         | 0..N
                                                         |
                                                         | 1
                                               +---------v---------+
                                               |       roles       |
                                               +-------------------+
```
* **DDL Implementation**:
  ```sql
  CREATE TABLE accounts_permission (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      codename VARCHAR(100) UNIQUE NOT NULL,
      description VARCHAR(255) NOT NULL
  );

  CREATE TABLE accounts_rolepermission (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      role_id UUID NOT NULL REFERENCES accounts_role(id) ON DELETE CASCADE,
      permission_id UUID NOT NULL REFERENCES accounts_permission(id) ON DELETE CASCADE,
      CONSTRAINT unique_role_permission UNIQUE (role_id, permission_id)
  );
  ```

### Tenant-Level Isolation (Multi-Clinic Partitioning)
To scale the platform as a Software-as-a-Service (SaaS) solution where multiple independent clinics share the same database infrastructure:
1. Introduce a `clinics` or `tenants` table.
2. Add a `clinic_id` foreign key column to the `users` and `activity_logs` tables.
3. Enforce a composite unique constraint on `users` for `(email, clinic_id)`, allowing the same email to exist across separate clinics if necessary, while isolating patient and user data.

---

## 7. Best Practices & Maintenance Guidelines

1. **Scheduled Data Purging**: Set up a cron job or pgAgent task to delete expired, unused OTP records and old failed login attempts to keep index sizes optimal.
   ```sql
   -- Purge unused OTPs older than 30 days
   DELETE FROM accounts_otp WHERE expires_at < NOW() - INTERVAL '30 days';
   
   -- Purge failed login attempts older than 90 days
   DELETE FROM accounts_failedloginattempt WHERE attempt_time < NOW() - INTERVAL '90 days';
   ```
2. **Monitor Index Usage**: Review index hit rates periodically. High-frequency tables like `accounts_usersession` and `accounts_activitylog` require regular index rebuilding (`REINDEX`) to prevent fragmentation.
3. **Database Backups**: Back up the schema and data daily. Maintain separate backup retention policies for clinical data (which may have long retention requirements) and session/security logs.
