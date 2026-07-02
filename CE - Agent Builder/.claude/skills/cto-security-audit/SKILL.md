# CTO Skill: Security Audit

## When to Use
Invoke this skill when conducting security assessments, reviewing application security, or evaluating compliance posture.

## Security Assessment Framework

### 1. OWASP Top 10 Checklist (2021)

| # | Vulnerability | Check |
|---|--------------|-------|
| A01 | Broken Access Control | Are authorization checks on every request? Is RBAC properly implemented? |
| A02 | Cryptographic Failures | Is sensitive data encrypted at rest and in transit? Are strong algorithms used? |
| A03 | Injection | Are inputs validated and parameterized? SQL, NoSQL, LDAP, OS command? |
| A04 | Insecure Design | Is security built into architecture? Threat modeling done? |
| A05 | Security Misconfiguration | Default credentials removed? Security headers set? Error handling secure? |
| A06 | Vulnerable Components | Are dependencies up to date? Known CVEs addressed? |
| A07 | Identification & Auth Failures | Strong password policy? MFA available? Session management secure? |
| A08 | Software & Data Integrity Failures | Signed updates? CI/CD pipeline secured? Dependency verification? |
| A09 | Security Logging & Monitoring | Are security events logged? Alerts configured? Incident response ready? |
| A10 | SSRF | Are outbound requests validated? Internal network protected? |

### 2. Authentication & Authorization Review

```markdown
## Authentication Checklist
- [ ] Password requirements (length, complexity, history)
- [ ] MFA implementation and enforcement
- [ ] Session timeout and management
- [ ] Brute force protection (lockout, CAPTCHA)
- [ ] Secure password reset flow
- [ ] Secure credential storage (bcrypt, argon2)

## Authorization Checklist
- [ ] Principle of least privilege
- [ ] Role-based access control (RBAC)
- [ ] Resource-level permissions
- [ ] API authorization on all endpoints
- [ ] No direct object reference vulnerabilities
```

### 3. Data Protection Assessment

| Data Type | Classification | At Rest | In Transit | Access Control |
|-----------|---------------|---------|------------|----------------|
| PII | Confidential | AES-256 | TLS 1.3 | Role-restricted |
| Credentials | Secret | Vault/KMS | TLS 1.3 | System only |
| Business data | Internal | [State] | TLS 1.2+ | Authenticated |
| Public data | Public | N/A | TLS 1.2+ | None |

### 4. Infrastructure Security

```markdown
## Cloud Security (AWS/Azure/GCP)
- [ ] IAM policies follow least privilege
- [ ] Security groups properly configured
- [ ] Encryption enabled on storage
- [ ] Logging enabled (CloudTrail, etc.)
- [ ] No public S3 buckets/blob storage
- [ ] VPC/network segmentation

## Container/K8s Security
- [ ] Base images scanned and updated
- [ ] No root containers
- [ ] Pod security policies
- [ ] Network policies configured
- [ ] Secrets management (not in env vars)
```

### 5. Compliance Mapping

| Requirement | SOC 2 | GDPR | HIPAA | PCI-DSS |
|-------------|-------|------|-------|---------|
| Access Control | CC6.1 | Art. 32 | §164.312(a) | Req. 7 |
| Encryption | CC6.7 | Art. 32 | §164.312(e) | Req. 3,4 |
| Logging | CC7.2 | Art. 30 | §164.312(b) | Req. 10 |
| Incident Response | CC7.4 | Art. 33 | §164.308(a)(6) | Req. 12 |

## Output Template

```markdown
## Security Audit Summary

### Scope & Methodology
- **System Assessed**: [Name]
- **Date**: [Date]
- **Methodology**: [OWASP, NIST, etc.]

### Risk Summary
| Severity | Count | Examples |
|----------|-------|----------|
| Critical | X | [Brief description] |
| High | X | [Brief description] |
| Medium | X | [Brief description] |
| Low | X | [Brief description] |

### Critical Findings
1. **[Finding Title]** - Severity: Critical
   - Description: [What's the issue]
   - Impact: [What could happen]
   - Recommendation: [How to fix]
   - Priority: Immediate

### Compliance Status
| Framework | Status | Key Gaps |
|-----------|--------|----------|
| SOC 2 | 🟡 Partial | [Gaps] |
| GDPR | 🟢 Compliant | None |

### Remediation Roadmap
| Finding | Owner | Timeline | Status |
|---------|-------|----------|--------|
| [Issue] | [Who] | [When] | 🔴 Open |

### Next Steps
1. [Immediate actions]
2. [Short-term improvements]
3. [Long-term security program]
```
