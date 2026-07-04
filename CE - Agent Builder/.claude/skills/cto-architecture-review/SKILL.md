# CTO Skill: Architecture Review

## When to Use
Invoke this skill when reviewing system architecture, evaluating technical designs, or assessing architecture decisions for client or internal projects.

## Architecture Review Framework

### 1. Review Dimensions

#### Functional Fit
- Does the architecture meet stated requirements?
- Are there gaps in functionality?
- How well does it handle edge cases?

#### Quality Attributes (Non-Functional)
| Attribute | Questions to Ask |
|-----------|------------------|
| **Scalability** | How does it handle 10x load? What's the scaling model? |
| **Performance** | What are latency requirements? Throughput targets? |
| **Availability** | What's the uptime target? Recovery time objective? |
| **Security** | How is data protected? What's the threat model? |
| **Maintainability** | How easy to modify? What's the coupling level? |
| **Observability** | Can we see what's happening? Logging? Monitoring? |

#### Architecture Patterns
- Is the pattern appropriate for the problem?
- Is it consistently applied?
- Are deviations documented and justified?

### 2. Architecture Decision Records (ADR) Template

```markdown
# ADR-XXX: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-YYY]

## Context
[What is the issue? What forces are at play?]

## Decision
[What is the change being proposed or made?]

## Consequences
### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Risks
- [Risk and mitigation]
```

### 3. Technical Debt Assessment

| Category | Examples | Business Impact |
|----------|----------|-----------------|
| **Code Debt** | Duplicated code, poor naming, missing tests | Slower development, more bugs |
| **Design Debt** | Tight coupling, wrong patterns, missing abstractions | Hard to change, expensive features |
| **Infrastructure Debt** | Manual deployments, no monitoring, outdated dependencies | Outages, security vulnerabilities |
| **Documentation Debt** | Missing docs, outdated diagrams | Onboarding delays, knowledge loss |

### 4. Risk Assessment Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | H/M/L | H/M/L | [Strategy] |
| [Risk 2] | H/M/L | H/M/L | [Strategy] |

## Output Template

```markdown
## Architecture Review Summary

### Overview
- **System**: [Name/Description]
- **Review Date**: [Date]
- **Scope**: [What was reviewed]

### Assessment Summary
| Dimension | Rating | Notes |
|-----------|--------|-------|
| Functional Fit | ⭐⭐⭐⭐☆ | [Summary] |
| Scalability | ⭐⭐⭐☆☆ | [Summary] |
| Security | ⭐⭐⭐⭐⭐ | [Summary] |
| Maintainability | ⭐⭐⭐☆☆ | [Summary] |
| Observability | ⭐⭐☆☆☆ | [Summary] |

### Key Findings
1. **[Finding Category]**: [Description]
   - Impact: [Business/Technical impact]
   - Recommendation: [What to do]

### Technical Debt Inventory
| Item | Severity | Effort | Priority |
|------|----------|--------|----------|
| [Debt item] | High | Medium | P1 |

### Recommended Actions
1. **Immediate**: [Actions needed now]
2. **Short-term**: [Actions for next sprint/month]
3. **Long-term**: [Strategic improvements]

### Risks
- [Risk with mitigation strategy]
```
