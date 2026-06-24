# Neuro Blooms Healthcare Management System
## Accounts Module Production Deployment Playbook & Checklist

---

## Table of Contents
1. [Overview](#1-overview)
2. [Pre-Deployment Requirements](#2-pre-deployment-requirements)
3. [Environment Variables Dictionary](#3-environment-variables-dictionary)
4. [Database Preparation & Migration Steps](#4-database-preparation--migration-steps)
5. [Hardening Commands Execution](#5-hardening-commands-execution)
    - [Seeding System Roles](#1-seeding-system-roles)
    - [Creating the Initial Administrator](#2-creating-the-initial-administrator)
6. [SMTP & Email Service Configuration](#6-smtp--email-service-configuration)
7. [Production Security Validation](#7-production-security-validation)
8. [Health Checks, Smoke Testing, & Verification](#8-health-checks-smoke-testing--verification)
9. [Rollback & Recovery Strategy](#9-rollback--recovery-strategy)
10. [Production Security Checklist](#10-production-security-checklist)
    - [JWT Security Hardening](#jwt-security-hardening)
    - [OTP Lifecycle Hardening](#otp-lifecycle-hardening)
    - [Email Delivery Security](#email-delivery-security)
    - [Database Layer Protection](#database-layer-protection)
    - [Admin Account Safeguards](#admin-account-safeguards)
11. [Go-Live Execution Checklist](#11-go-live-execution-checklist)
12. [Operations, Monitoring, & Alerts Configuration](#12-operations-monitoring--alerts-configuration)
13. [Post-Deployment Maintenance Schedule](#13-post-deployment-maintenance-schedule)
14. [Best Practices & Security Hardening Guidelines](#14-best-practices--security-hardening-guidelines)

---

## 1. Overview
Deploying security-critical features like authentication, RBAC, session tracking, and account locks to a production environment requires a highly structured, repeatable process. 

This playbook provides system administrators, DevOps engineers, and security operations (SecOps) teams with a step-by-step guide for deploying and hardening the **Neuro Blooms Accounts Module**. 

It outlines the required environment variables, database migrations, seeding procedures, email configurations, rollback strategies, and long-term maintenance checklists necessary to ensure a secure, high-availability production deployment.

---

## 2. Pre-Deployment Requirements

Before initiating the deployment process on your staging or production servers, verify that the following preconditions are met:

- [ ] **VCS Audit**: All code changes are committed and pushed to the main release branch. The repository state is clean.
- [ ] **Dependency Freeze**: Verify that all python dependencies are frozen in `requirements.txt` and match approved security baselines.
- [ ] **Infrastructure Readiness**: The target PostgreSQL instance is provisioned, and network access is restricted to the application servers (via security groups or private subnets).
- [ ] **SMTP Account Provisioned**: An enterprise SMTP account (e.g., SendGrid, AWS SES, or Mailgun) is provisioned and authorized to send emails from `no-reply@neuroblooms.com`.
- [ ] **SSL/TLS Certificates**: Valid SSL/TLS certificates (e.g., Let's Encrypt or custom CA certificates) are active on the application gateway (Nginx/Cloudflare) to enforce HTTPS.

---

## 3. Environment Variables Dictionary

All sensitive configurations must be loaded via environment variables in production. Never commit production credentials, secret keys, or database passwords to the git repository.

Create a secure `.env` file or inject these variables directly into your container orchestration platform (e.g., Kubernetes Secrets, AWS ECS Task Definition):

| Variable Name | Required | Secret? | Target / Example Production Value | Description / Security Considerations |
| :--- | :---: | :---: | :--- | :--- |
| `SECRET_KEY` | **Yes** | **Yes** | `d89a1f2b938cde476a81b...` | The Django secret key used for cryptographic signing, token verification, and sessions. Generate a 50-character random string. |
| `DEBUG` | **Yes** | No | `False` | Must be set to `False` in production. Setting this to `True` leaks sensitive source code and stack traces during API errors. |
| `DB_NAME` | **Yes** | No | `neuro_blooms_production` | The name of the production PostgreSQL database. |
| `DB_USER` | **Yes** | No | `neuro_blooms_app` | The database user role dedicated to the application. This user should only have DML permissions. |
| `DB_PASSWORD` | **Yes** | **Yes** | `ProdSecureDBPass9988!` | The password for the database user. Use a strong, generated password. |
| `DB_HOST` | **Yes** | No | `db.neuroblooms.internal` | The private network address of the PostgreSQL database instance. |
| `DB_PORT` | **Yes** | No | `5432` | The port on which PostgreSQL is listening. |
| `INITIAL_ADMIN_EMAIL`| **Yes** | No | `admin@neuroblooms.com` | The email address of the default system administrator account created during deployment. |
| `INITIAL_ADMIN_PASSWORD`| **Yes** | **Yes** | `AdminTemporarySecurePass1!` | The temporary password for the default administrator account. Enforce a password change on first login. |
| `INITIAL_ADMIN_FIRST_NAME`| No | No | `System` | First name of the default admin account. |
| `INITIAL_ADMIN_LAST_NAME`| No | No | `Administrator` | Last name of the default admin account. |
| `EMAIL_HOST` | **Yes** | No | `smtp.sendgrid.net` | The SMTP server host address. |
| `EMAIL_PORT` | **Yes** | No | `587` | The SMTP server port (usually `587` for TLS or `465` for SSL). |
| `EMAIL_HOST_USER` | **Yes** | **Yes** | `apikey` | The username used to authenticate with the SMTP server. |
| `EMAIL_HOST_PASSWORD` | **Yes** | **Yes** | `SG.secure_smtp_api_key...` | The password/API key used to authenticate with the SMTP server. |
| `EMAIL_USE_TLS` | **Yes** | No | `True` | Must be set to `True` to encrypt mail in transit. |
| `EMAIL_USE_SSL` | **Yes** | No | `False` | Set to `True` only if using port `465`. |
| `DEFAULT_FROM_EMAIL`| **Yes** | No | `Neuro Blooms <no-reply@neuroblooms.com>` | The sender address and display name used for all system-generated emails (OTPs, welcome notes). |

---

## 4. Database Preparation & Migration Steps

To initialize the database schema in the production PostgreSQL instance:

### Step 1: Initialize Database and Extensions
Connect to your PostgreSQL server as a superuser and verify that the `uuid-ossp` extension is enabled. This is required for generating UUID v4 primary keys:
```sql
CREATE DATABASE neuro_blooms_production;
\c neuro_blooms_production;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Step 2: Run Schema Migrations
On the application server, run the Django migration command to execute all schema changes and build the tables:
```bash
python manage.py migrate --noinput
```
*Note: The `--noinput` flag prevents the command from prompting the user, ensuring the migration script runs successfully in automated CI/CD pipelines.*

---

## 5. Hardening Commands Execution

Once the tables are created, you must run the custom management commands to seed the authorization roles and establish the initial administrator account.

### 1. Seeding System Roles
Run the `seed_roles` command to populate the `Role` table with the default system roles:
```bash
python manage.py seed_roles
```
* **Expected Output**:
  ```
  Created role: ADMIN
  Created role: DOCTOR
  Created role: RECEPTIONIST
  ```
* **Validation**: Query the database to verify that three roles exist and that a `ROLE_SEEDED` event is logged in the `accounts_activitylog` table.

### 2. Creating the Initial Administrator
Run the `create_initial_admin` command to create the default administrative account using the credentials defined in your environment variables:
```bash
python manage.py create_initial_admin
```
* **Expected Output**:
  ```
  Successfully created initial admin: admin@neuroblooms.com
  ```
* **Security Action**: The default admin account is created with `is_superuser = TRUE` and the `ADMIN` role. An `INITIAL_ADMIN_CREATED` event is logged in the security ledger.

---

## 6. SMTP & Email Service Configuration

Since the login flow relies on time-sensitive OTP codes delivered via email, ensuring reliable email delivery is a critical deployment step.

1. **Verify Authentication Mode**: Ensure that `EMAIL_BACKEND` is set to Django's SMTP backend:
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
   ```
2. **Configure SPF, DKIM, and DMARC**:
   - Work with your DNS administrator to add **SPF** (Sender Policy Framework) records authorizing your SMTP server to send emails on behalf of `neuroblooms.com`.
   - Add **DKIM** (DomainKeys Identified Mail) public keys to your DNS records to sign outgoing system emails.
   - Configure a **DMARC** (Domain-based Message Authentication, Reporting, and Conformance) policy to prevent spoofing and domain abuse.
3. **Verify Deliverability**: Trigger a test email using the Django shell to confirm that connections are established securely and emails are delivered to the inbox (not the spam folder).

---

## 7. Production Security Validation

Before opening public traffic, perform the following security checks to verify the system is hardened against common vulnerabilities:

- [ ] **DEBUG Flag Check**: Verify that `DEBUG = False` is active on the server.
- [ ] **HTTPS Redirection**: Confirm that Nginx or your gateway redirects all HTTP requests to HTTPS. The server must only accept connections over TLS 1.2 or TLS 1.3.
- [ ] **Hashed Password Check**: Verify that all passwords stored in the database are encrypted using PBKDF2 with SHA256 (or Argon2) and are not visible in plain text.
- [ ] **Secure Cookie Flags**: If passing session tokens via cookies in the future, verify that the `Secure`, `HttpOnly`, and `SameSite=Strict` flags are configured.
- [ ] **No Default Credentials**: Verify that the default administrator account password was changed immediately after initialization.

---

## 8. Health Checks, Smoke Testing, & Verification

Once the deployment is complete, run these smoke tests to verify the system is functioning correctly:

### Step 1: Health Check Endpoint
Query the system health check endpoint to verify that database connections are active and the server is responding:
```bash
curl -f https://api.neuroblooms.com/health/
```
*Expected Response: HTTP `200 OK` with status metadata.*

### Step 2: Smoke Test the Authentication Flow
1. Send a login request for a test account to `/api/v1/auth/login/`. Confirm the server returns a success message indicating the OTP was sent.
2. Check the console or test inbox to retrieve the generated OTP code.
3. Submit the OTP code to `/api/v1/auth/verify-otp/`. Confirm the server returns the JWT access and refresh tokens.
4. Call `/api/v1/profile/me/` using the returned access token as a Bearer token. Confirm the server returns the user's profile details.
5. Call `/api/v1/auth/logout/` using the refresh token. Confirm the session is terminated and subsequent requests using that token are blocked.

---

## 9. Rollback & Recovery Strategy

If a critical failure occurs during deployment (e.g., database connection failures, migration crashes, or server startup failures):

### Step 1: Revert Server Code
Immediately roll back the application server containers or code deployments to the previously stable version tag using your deployment platform:
```bash
# Example Kubernetes rollback
kubectl rollout undo deployment/neuro-blooms-backend
```

### Step 2: Database Rollback (If Required)
* **No Structural Changes**: If the new deployment did not modify the database schema, no database rollback is required.
* **Migration Rollback**: If a database migration failed mid-execution or broke existing features, roll back the database schema to the last known stable migration state before restoring the old code:
  ```bash
  python manage.py migrate accounts <last_stable_migration_name>
  ```
* **Full Database Restore**: If data corruption occurred, restore the database from the last automated snapshot taken before the deployment window.

---

## 10. Production Security Checklist

---

### JWT Security Hardening
- [ ] The `SECRET_KEY` is kept secure, rotated periodically, and is never shared or printed in logs.
- [ ] Access token lifetimes are limited to 24 hours or less, and refresh token rotation is active (`ROTATE_REFRESH_TOKENS = True`).
- [ ] All token refresh requests validate the active database session state to prevent the use of revoked tokens.

### OTP Lifecycle Hardening
- [ ] OTP codes are strictly limited to 6 digits, single-use, and expire after 15 minutes.
- [ ] Generating a new OTP automatically invalidates all previously issued unused codes for that user and purpose.
- [ ] Cryptographic signed tokens generated during OTP verification are short-lived (15 minutes) and are validated securely using the server's `SECRET_KEY`.

### Email Delivery Security
- [ ] The SMTP server connection enforces TLS (`EMAIL_USE_TLS = True`).
- [ ] DNS records include SPF, DKIM, and DMARC configurations to prevent domain spoofing.
- [ ] Outgoing emails do not expose sensitive user data beyond what is required for the verification workflow.

### Database Layer Protection
- [ ] The database instance runs in a private subnet and is not accessible from the public internet.
- [ ] The database user role used by the application is restricted to DML operations (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on the accounts tables, blocking DDL modifications.
- [ ] The `activity_logs` table has database-level triggers or security policies active to prevent deletion or tampering.

### Admin Account Safeguards
- [ ] The default administrator account password was changed immediately after deployment.
- [ ] Admin accounts enforce two-factor authentication (OTP) at login.
- [ ] Administrative access is reviewed regularly, and unused admin accounts are deactivated immediately.

---

## 11. Go-Live Execution Checklist

Run these final checks during the go-live window before routing public user traffic:

- [ ] **DNS Cutover**: Update your DNS records to route traffic through your production load balancer or CDN (e.g., Cloudflare).
- [ ] **CDN / WAF Active**: Verify that web application firewall (WAF) rules are active on your CDN to block malicious traffic and rate-limit sensitive endpoints.
- [ ] **SSL Certificate Verified**: Confirm that your SSL/TLS certificate is valid, matches your production domain, and enforces secure TLS protocols.
- [ ] **Environment Variables Audit**: Double-check that all production environment variables are configured correctly and that `DEBUG` is set to `False`.
- [ ] **Log Forwarding Active**: Confirm that application and database logs are being forwarded to your secure, centralized log analysis platform.

---

## 12. Operations, Monitoring, & Alerts Configuration

To maintain visibility into the health and security of the Accounts Module in production, configure your monitoring systems (e.g., Datadog, Prometheus, or Grafana) to track the following metrics and trigger alerts when anomalies are detected:

### Key Performance Indicators (KPIs)
* **Authentication Latency**: Monitor the response time of the `/auth/login/` and `/auth/verify-otp/` endpoints. Latency should remain under 200ms.
* **OTP Delivery Time**: Monitor the time elapsed between an OTP request and its successful delivery via SMTP. Deliverability latency should remain under 5 seconds.
* **Database Connection Pool**: Monitor active database connection counts to prevent connection exhaustion during traffic spikes.

### Critical Security Alerts
Configure automated alerts to notify your security team immediately when these thresholds are exceeded:
* **High Failure Rate**: Alert if failed login attempts exceed 50 failures within a 5-minute window across the entire system (indicates a credential stuffing attack).
* **Mass Lockouts**: Alert if more than 10 accounts are locked due to brute-force protection within a 15-minute window.
* **Admin Privilege Changes**: Alert on any `USER_UPDATED` or `USER_CREATED` actions that assign the `ADMIN` role.
* **Database Tampering**: Alert on any attempts to modify or delete records in the `activity_logs` table.

---

## 13. Post-Deployment Maintenance Schedule

To keep the Accounts Module secure and performing optimally, execute these maintenance tasks on a recurring schedule:

### Weekly
* **Verify Log Forwarding**: Confirm that security audit logs are being forwarded successfully to your centralized log analysis platform.
* **Review Locked Accounts**: Review the list of locked accounts and investigate any recurring brute-force targets.

### Monthly
* **Database Index Rebuilds**: Rebuild indexes on high-frequency tables (like `accounts_usersession` and `accounts_activitylog`) to prevent fragmentation.
* **Purge Expired Data**: Run maintenance scripts to delete expired, unused OTP records and old failed login attempts to keep the database size optimal.

### Quarterly
* **Access Control Review**: Review all user accounts with administrative access and revoke privileges for accounts that no longer require them.
* **Verify Backups**: Restore a production database backup to a staging environment and verify that the restore process completes successfully and data integrity is maintained.
* **Security Key Rotation**: Rotate the Django `SECRET_KEY` and other sensitive API keys on a regular schedule to minimize the impact of credential leaks.
