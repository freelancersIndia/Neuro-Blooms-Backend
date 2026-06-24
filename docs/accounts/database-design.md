# Neuro Blooms Healthcare Management System
## Accounts Module Database Design Documentation

---

## Table of Contents
1. [Overview](#1-overview)
2. [Database Philosophy & Design Decisions](#2-database-philosophy--design-decisions)
    - [Primary Key Strategy (UUID v4)](#primary-key-strategy-uuid-v4)
    - [Loose Coupling for Failed Login Tracking](#loose-coupling-for-failed-login-tracking)
    - [Soft Audit Persistence vs. Hard Cascades](#soft-audit-persistence-vs-hard-cascades)
    - [Active Session Tracking & JWT Rotation](#active-session-tracking--jwt-rotation)
3. [Entity Mappings & Schema Catalog](#3-entity-mappings--schema-catalog)
    - [users](#table-1-users)
    - [roles](#table-2-roles)
    - [user_roles](#table-3-user_roles)
    - [otps](#table-4-otps)
    - [user_sessions](#table-5-user_sessions)
    - [activity_logs](#table-6-activity_logs)
    - [failed_login_attempts](#table-7-failed_login_attempts)
    - [account_locks](#table-8-account_locks)
4. [Indexes & Performance Optimization](#4-indexes--performance-optimization)
5. [Database Triggers & Automated Hardening](#5-database-triggers--automated-hardening)
6. [SQL DDL Reference](#6-sql-ddl-reference)
7. [Future Scalability & Architectural Evolution](#7-future-scalability--architectural-evolution)
    - [High-Volume Logging and Partitioning](#high-volume-logging-and-partitioning)
    - [Caching Layer Integration (Redis)](#caching-layer-integration-redis)
8. [Best Practices & Security Hardening guidelines](#8-best-practices--security-hardening-guidelines)

---

## 1. Overview
The **Accounts Module** of the Neuro Blooms Healthcare Management System represents the foundational security, authentication, authorization, and audit infrastructure of the entire application. Designed for enterprise-grade compliance, scalability, and security, it manages user identities, roles (multiple roles per user), session states, multi-purpose verification codes (OTPs), failed login auditing, automatic account locks, and complete, un-alterable activity log tracking.

This document provides future backend developers, database administrators, and security engineers with a granular, comprehensive mapping of the physical and logical database structure. It documents the tables, fields, data types, constraints, indexes, relationships, and business rules governing the persistence layer.

---

## 2. Database Philosophy & Design Decisions

### Primary Key Strategy (UUID v4)
Every primary key across all tables in the Accounts Module utilizes universally unique identifiers (UUID v4) rather than auto-incrementing integers.
* **Security**: UUIDs prevent enumeration attacks. An external actor cannot deduce the total number of users or sessions, nor can they guess adjacent IDs to harvest data.
* **Distributed Systems Compatibility**: UUIDs can be generated safely on the application server level before insertion, facilitating future database microservices, horizontal scaling, and sharding without risk of primary key collisions.
* **Implementation**: Standardized as PostgreSQL `uuid` data type, generated automatically by `uuid_generate_v4()`.

### Loose Coupling for Failed Login Tracking
The `failed_login_attempts` table is intentionally designed to be loosely coupled. 
* **Design Decision**: The `email` field is stored as a raw `VARCHAR` rather than a foreign key referencing the `users` table.
* **Rationale**: If a malicious user attempts to log in using an email that does not exist in the system (e.g., an email harvesting probe), the system must still record the attempt, track the source IP address, and enforce security policies. Enforcing a foreign key constraint would crash the insertion of failed attempts for non-existent users or prevent tracking of email harvesting attempts.

### Soft Audit Persistence vs. Hard Cascades
The Accounts database implements a hybrid approach to referential integrity:
* **CASCADE**: When a `User` record is deleted (which is restricted to administrative actions), dependent entities like `UserRole`, `AccountLock`, `UserSession`, and `OTP` are automatically cleaned up via foreign key cascades.
* **SET_NULL**: The `activity_logs` table preserves its records even if the associated user is permanently deleted. The `user_id` foreign key is set to `NULL` (`on_delete=models.SET_NULL`), ensuring the historical integrity of the audit logs is never compromised. The text description in the log retains the contextual details of the operator.

### Active Session Tracking & JWT Rotation
To overcome the stateless limitations of JSON Web Tokens (JWT) while preserving high-performance validation, the database implements a state-aware session tracking layer:
* **Session Mapping**: A `UserSession` record is created upon successful multi-factor OTP verification. It maps the cryptographic `jti` (JWT ID) claim of the refresh token directly to the user's active session.
* **Rotation Sync**: On refresh token rotation, the old refresh token is blacklisted, and the `refresh_token_jti` in the corresponding active `UserSession` is updated to reflect the newly issued refresh token's `jti`.
* **State Verification**: The custom token refresh view validates not only the signature of the incoming JWT but also queries the `UserSession` table to ensure that the session matches, is active (`is_active=True`), and has not been revoked.

---

## 3. Entity Mappings & Schema Catalog

Below is the detailed schema catalog for each of the eight tables in the Accounts database.

---

### Table 1: `users`
#### Purpose
Stores core identity data, authentication credentials (hashed), administrative flags, and state trackers for all users (Admins, Doctors, and Receptionists).

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `email` | `VARCHAR(254)` | No | None | `UNIQUE`, `NOT NULL` |
| `phone_number` | `VARCHAR(20)` | Yes | `NULL` | `UNIQUE` |
| `password` | `VARCHAR(128)` | No | None | `NOT NULL` |
| `first_name` | `VARCHAR(150)` | No | `''` (Empty string) | None |
| `last_name` | `VARCHAR(150)` | No | `''` (Empty string) | None |
| `profile_image` | `VARCHAR(100)` | Yes | `NULL` | Stores relative file path |
| `is_active` | `BOOLEAN` | No | `TRUE` | `NOT NULL` |
| `is_verified` | `BOOLEAN` | No | `FALSE` | `NOT NULL` |
| `is_staff` | `BOOLEAN` | No | `FALSE` | `NOT NULL` |
| `is_superuser` | `BOOLEAN` | No | `FALSE` | `NOT NULL` |
| `last_login` | `TIMESTAMPTZ` | Yes | `NULL` | Managed by Django auth |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |
| `updated_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |

#### Relationships
* **Roles**: Many-to-Many relationship with `roles` table, resolved through the `user_roles` join table.

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Email Index**: Implicit unique B-Tree index on `email` (used for fast lookup during login and user queries).
* **Phone Number Index**: Implicit unique B-Tree index on `phone_number` (if populated).

#### Business Rules & Constraints
1. **Email Standardization**: Emails must be normalized (lowercased, domain-stripped of trailing spaces) before insertion.
2. **Password Storage**: Passwords must never be persisted in plain text. The system enforces PBKDF2 with a SHA256 hash or Argon2 (standardized via Django's password hashers).
3. **Verification State**: `is_verified` must be set to `TRUE` only after a user successfully completes the `EMAIL_VERIFICATION` OTP flow.

---

### Table 2: `roles`
#### Purpose
Stores authorization roles that represent specific permission sets within the system.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `name` | `VARCHAR(50)` | No | None | `UNIQUE`, `NOT NULL` |
| `description` | `TEXT` | No | `''` (Empty string) | None |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |

#### Relationships
* **Users**: Many-to-Many relationship with `users`, mapped through `user_roles`.

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Name Index**: Implicit unique B-Tree index on `name` (enforces uppercase role names and guarantees instant authorization lookup).

#### Business Rules & Constraints
1. **Case Integrity**: Role names must be strictly uppercase (e.g., `ADMIN`, `DOCTOR`, `RECEPTIONIST`).
2. **Predefined Roles**: The table is populated on application initialization via the `seed_roles` command. Adding ad-hoc roles is restricted to database administrators or custom migration scripts.

---

### Table 3: `user_roles`
#### Purpose
The join table resolving the Many-to-Many relationship between `users` and `roles`. Enables multiple roles per user.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `user_id` | `UUID` | No | None | `FOREIGN KEY` references `users.id` `ON DELETE CASCADE` |
| `role_id` | `UUID` | No | None | `FOREIGN KEY` references `roles.id` `ON DELETE CASCADE` |
| `assigned_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Composite Unique Constraint**: A composite unique index on `(user_id, role_id)` prevents assigning the same role to a user multiple times.
* **Foreign Key Indexes**: B-Tree indexes on `user_id` and `role_id` to speed up joins during permission checks.

#### Business Rules & Constraints
1. **Uniqueness**: A user cannot possess duplicate role memberships. Attempts to insert a duplicate `(user_id, role_id)` will raise a database integrity violation.
2. **Cascaded Lifecycle**: Deleting a user or deleting a role completely sweeps the cross-reference entries out of `user_roles`.

---

### Table 4: `otps`
#### Purpose
Stores single-use, time-limited cryptographic One-Time Password (OTP) codes used for login verification, password resets, and email verification.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `user_id` | `UUID` | No | None | `FOREIGN KEY` references `users.id` `ON DELETE CASCADE` |
| `otp_code` | `VARCHAR(6)` | No | None | `NOT NULL` |
| `purpose` | `VARCHAR(50)` | No | None | `NOT NULL` (Choices: `LOGIN_VERIFICATION`, `PASSWORD_RESET`, `EMAIL_VERIFICATION`) |
| `expires_at` | `TIMESTAMPTZ` | No | None | `NOT NULL` |
| `is_used` | `BOOLEAN` | No | `FALSE` | `NOT NULL` |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |

#### Relationships
* **User**: Belongs to one user.

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **User-Purpose Unused Lookup Index**: A composite B-Tree index on `(user_id, purpose, is_used, expires_at)` is highly recommended to expedite verifying if a valid OTP is currently outstanding.

#### Business Rules & Constraints
1. **Single-Use Enforcement**: Once verified, the record's `is_active` / `is_used` state must immediately transition to `TRUE`.
2. **Invalidation of Previous Codes**: Upon generating a new OTP code for a specific user and purpose, any previous outstanding (unused) OTP records for that user and purpose must be marked as `is_used = TRUE` to prevent reuse or replay attacks.
3. **Expiration**: The OTP code is mathematically valid for exactly 15 minutes from the `created_at` timestamp.

---

### Table 5: `user_sessions`
#### Purpose
Maintains session state, binding JWT refresh tokens to physical client devices, IP addresses, and user-agent metadata.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `user_id` | `UUID` | No | None | `FOREIGN KEY` references `users.id` `ON DELETE CASCADE` |
| `refresh_token_jti` | `VARCHAR(255)` | No | None | `NOT NULL`, Indexed |
| `ip_address` | `INET` / `VARCHAR(45)` | Yes | `NULL` | Supports IPv4 and IPv6 |
| `user_agent` | `TEXT` | Yes | `NULL` | Raw user-agent string |
| `browser` | `VARCHAR(255)` | Yes | `NULL` | Parsed browser family and version |
| `device` | `VARCHAR(255)` | Yes | `NULL` | Parsed device type (Desktop/Mobile) |
| `login_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |
| `last_activity` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |
| `is_active` | `BOOLEAN` | No | `TRUE` | `NOT NULL` |

#### Relationships
* **User**: Belongs to one user.

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Token Identifier Index**: B-Tree index on `refresh_token_jti` (crucial for quick session lookups on token refresh requests).
* **Active User Sessions Index**: B-Tree index on `(user_id, is_active)` to accelerate retrieving active devices for a user.

#### Business Rules & Constraints
1. **Device Detection**: The application layer must parse the `user_agent` string using a reliable library (e.g., `user-agents`) and persist user-friendly values into the `browser` and `device` fields.
2. **Deactivation Flow**: Revocation of a session updates `is_active` to `FALSE` and logs the timestamp. The corresponding refresh token JTI is added to the system-wide blacklist.

---

### Table 6: `activity_logs`
#### Purpose
Acts as the immutable security ledger of the Accounts Module. Tracks critical authentication, administrative, and hardening events for audit compliance.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `user_id` | `UUID` | Yes | `NULL` | `FOREIGN KEY` references `users.id` `ON DELETE SET_NULL` |
| `action` | `VARCHAR(50)` | No | None | `NOT NULL` (Choices from `ActivityType`) |
| `description` | `TEXT` | No | None | `NOT NULL` |
| `ip_address` | `INET` / `VARCHAR(45)` | Yes | `NULL` | IP address of the request initiator |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |

#### Relationships
* **User**: Soft relationship. If a user is deleted, their history remains with `user_id` set to `NULL`.

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Temporal Audit Index**: B-Tree index on `created_at` (essential for security engineers filtering logs by date ranges).
* **Action Type Index**: B-Tree index on `action` to filter security events.
* **User History Index**: B-Tree index on `user_id`.

#### Business Rules & Constraints
1. **Immutability**: Log entries must never be updated or deleted by the application. SQL permissions should ideally restrict update/delete operations on this table to security roles or log forwarding systems.
2. **Comprehensive Action Mapping**: Every action must map to a predefined constant in the `ActivityType` catalog (e.g., `LOGIN`, `LOGOUT`, `FAILED_LOGIN`, `ACCOUNT_LOCKED`, `ACCOUNT_UNLOCKED`, `ROLE_SEEDED`).

---

### Table 7: `failed_login_attempts`
#### Purpose
Tracks authentication failures in real-time to detect, analyze, and counter brute-force or credential stuffing attacks.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `email` | `VARCHAR(254)` | No | None | Raw email string (Not a Foreign Key) |
| `ip_address` | `INET` / `VARCHAR(45)` | No | None | `NOT NULL` |
| `attempt_time` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |
| `reason` | `VARCHAR(50)` | No | None | `NOT NULL` (e.g., `USER_NOT_FOUND`, `INVALID_PASSWORD`, `ACCOUNT_LOCKED`) |

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Brute Force Counter Index**: Composite B-Tree index on `(email, attempt_time)` to quickly compute failure rates over rolling windows.

#### Business Rules & Constraints
1. **No Hard Constraints**: Must accept any email string, regardless of its existence in the system.
2. **Auto-Locking Trigger**: Upon each insertion, the system counts records matching the current `email` within a rolling 15-minute window. If the count matches or exceeds 5, a lock trigger must fire to create a record in `account_locks`.

---

### Table 8: `account_locks`
#### Purpose
Maintains temporary lock records that bar users from authenticating after exceeding brute-force thresholds.

#### Fields & Types
| Field Name | Physical Data Type | Nullable | Default Value | Constraints / Foreign Keys |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | `uuid_generate_v4()` | `PRIMARY KEY` |
| `user_id` | `UUID` | No | None | `FOREIGN KEY` references `users.id` `ON DELETE CASCADE` |
| `locked_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | `NOT NULL` |
| `unlock_at` | `TIMESTAMPTZ` | No | None | `NOT NULL` |
| `reason` | `VARCHAR(100)` | No | None | `NOT NULL` (e.g., `TOO_MANY_FAILED_ATTEMPTS`) |
| `is_active` | `BOOLEAN` | No | `TRUE` | `NOT NULL` |

#### Relationships
* **User**: Belongs to one user.

#### Indexes
* **Primary Key Index**: Implicit unique B-Tree index on `id`.
* **Active Lock Index**: B-Tree index on `(user_id, is_active, unlock_at)` to evaluate if an account is currently blocked.

#### Business Rules & Constraints
1. **Lock Duration**: The default lock duration is exactly 15 minutes from the `locked_at` timestamp.
2. **Deactivation**: A lock is deactivated if `is_active` is set to `FALSE` by an administrator (unlock action) or if the current timestamp exceeds `unlock_at`. Expired locks are lazily marked inactive by the verification query.

---

## 4. Indexes & Performance Optimization

To guarantee sub-millisecond response times even under high concurrent loads, the database schema implements a deliberate indexing strategy:

```sql
-- Core Search Indexes
CREATE INDEX idx_users_email_lower ON accounts_user (LOWER(email));
CREATE INDEX idx_users_phone ON accounts_user (phone_number) WHERE phone_number IS NOT NULL;

-- Session Refresh Optimization (Extremely Critical)
-- This speeds up every standard API request which validates the rotated refresh token JTI.
CREATE INDEX idx_sessions_jti_active ON accounts_usersession (refresh_token_jti, is_active);

-- Security Tracking and Brute-force counter optimization
-- Speeds up counting failed attempts within the 15-minute window during login.
CREATE INDEX idx_failed_attempts_rate ON accounts_failedloginattempt (email, attempt_time DESC);

-- Active Lock Verification Optimization
-- Speeds up checking if a user is currently locked.
CREATE INDEX idx_active_account_locks ON accounts_accountlock (user_id, is_active, unlock_at DESC);

-- Audit Trail Temporal Pagination Indexes
CREATE INDEX idx_activity_logs_created ON accounts_activitylog (created_at DESC);
CREATE INDEX idx_activity_logs_action ON accounts_activitylog (action);
```

---

## 5. Database Triggers & Automated Hardening

To enforce database-level security and prevent malicious tampering, the PostgreSQL database is configured with the following hardening strategies:

### 1. Immature Token Clean-up Trigger
Expired or used OTP records representing historical data can be swept automatically to prevent database bloat. A scheduled routine or trigger deletes OTP records older than 30 days.

### 2. Activity Log Deletion Safeguard
To comply with medical security standards (like HIPAA or local health records acts), the `activity_logs` table should block manual database deletion.
```sql
CREATE OR REPLACE FUNCTION protect_audit_logs()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Deletion or modification of activity_logs records is strictly prohibited.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_protect_audit_logs
BEFORE UPDATE OR DELETE ON accounts_activitylog
FOR EACH ROW EXECUTE FUNCTION protect_audit_logs();
```

---

## 6. SQL DDL Reference
Below is the PostgreSQL-compliant DDL statements representing the physical layout of the database tables, constraints, and relationships.

```sql
-- Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create Roles Table
CREATE TABLE accounts_role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create Users Table
CREATE TABLE accounts_user (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(254) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    password VARCHAR(128) NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    profile_image VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create User Roles Join Table
CREATE TABLE accounts_userrole (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES accounts_role(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_role UNIQUE (user_id, role_id)
);

-- 4. Create OTPs Table
CREATE TABLE accounts_otp (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    otp_code VARCHAR(6) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Create User Sessions Table
CREATE TABLE accounts_usersession (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    refresh_token_jti VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    browser VARCHAR(255),
    device VARCHAR(255),
    login_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 6. Create Activity Logs Table
CREATE TABLE accounts_activitylog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES accounts_user(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. Create Failed Login Attempts Table
CREATE TABLE accounts_failedloginattempt (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(254) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    attempt_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(50) NOT NULL
);

-- 8. Create Account Locks Table
CREATE TABLE accounts_accountlock (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    locked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    unlock_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
```

---

## 7. Future Scalability & Architectural Evolution

### High-Volume Logging and Partitioning
In a highly active production environment, the `activity_logs` and `failed_login_attempts` tables will grow rapidly, accumulating millions of rows. 
* **Partitioning Strategy**: Implement PostgreSQL table partitioning on `activity_logs` by range based on the `created_at` field. 
* **Benefits**: Monthly partitions allow archiving or purging old audit trails (e.g., dropping partitions older than 7 years to comply with data retention laws) instantly without performing expensive, lock-heavy `DELETE` operations.
* **Example Schema**:
  ```sql
  CREATE TABLE accounts_activitylog_partitioned (
      id UUID,
      user_id UUID,
      action VARCHAR(50),
      description TEXT,
      ip_address VARCHAR(45),
      created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id, created_at)
  ) PARTITION BY RANGE (created_at);
  ```

### Caching Layer Integration (Redis)
To alleviate read stress on the PostgreSQL database, several hot datasets should be cached in a Redis layer:
* **Active User Sessions**: Store the mapping of `refresh_token_jti` to session status in Redis. Standard API token validation can query Redis in sub-milliseconds rather than hitting PostgreSQL on every request.
* **Failed Login Counter**: Rather than querying the database to count failures on every login attempt, maintain the sliding window counter in Redis using `INCR` and `EXPIRE` keys.
* **Active Locks**: Cache active `AccountLock` states in Redis. A locked user is blocked at the gateway/cache level before executing any SQL queries.

---

## 8. Best Practices & Security Hardening Guidelines

1. **Keep Connections Secure**: Ensure that all database connections in production enforce SSL/TLS (`sslmode=require`).
2. **Restrict Database User Permissions**: The Django backend should connect using a database user role restricted to `DML` operations on the accounts tables, blocking any `DDL` modifications (except during deployment migrations, which must run under a privileged migration role).
3. **Audit Database Logs**: Configure PostgreSQL's `log_connections` and `log_disconnections` to keep track of database access points.
4. **Backup Regimen**: Implement a daily logical backup (`pg_dump`) combined with continuous physical archiving using Write-Ahead Logging (WAL) (e.g., using pgBackRest) to guarantee a Recovery Point Objective (RPO) of under 5 minutes.
