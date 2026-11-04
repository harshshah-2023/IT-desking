# Acme Corp IT Security Policy

## 1. Access Control

### 1.1 Least Privilege
Every employee gets only the access needed for their current job. Access is requested through the IT access desk and every grant is written to the audit log.

### 1.2 System Classification
Restricted systems: prod-db and aws-prod. Internal systems: jira and vpn. Restricted systems need an open incident ticket (for example INC-1234) for any temporary access.

### 1.3 Read Access
Read access to a Restricted system may be granted for at most 72 hours, with an open incident ticket.

### 1.4 Just-in-Time Privileged Access
Write and admin access are privileged. Privileged access is granted just-in-time (JIT) only: a just-in-time privileged session may last at most 8 hours. Requests for longer periods must be refused or shortened to 8 hours or less. The person must be enrolled in MFA.

### 1.5 Contractors
A contractor may never hold write or admin access to a Restricted system, even during an outage. Contractors may receive read access to a Restricted system for at most 24 hours.

### 1.6 Leavers
When an employee leaves (status terminated), all of their AD groups must be removed within 24 hours.

## 2. Authentication

### 2.1 Passwords
The minimum password length is 14 characters. Passwords may not reuse any of the last 5 passwords.

### 2.2 Multi-Factor Authentication
MFA is mandatory for every employee and contractor. Anyone without MFA must be flagged in the daily compliance report.

## 3. Privileged Accounts

### 3.1 Re-certification
Privileged accounts are re-certified monthly by the employee's manager.

### 3.2 Audit Logging
All access grants are logged with employee, system, level, duration and reason. Logs are kept for 1 year.

## 4. Remote Access

### 4.1 VPN
If the Mumbai VPN gateway is degraded, users should connect through the Pune gateway. VPN error 809 usually means the gateway is overloaded.
