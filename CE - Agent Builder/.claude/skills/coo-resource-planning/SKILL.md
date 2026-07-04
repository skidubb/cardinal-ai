# COO Skill: Resource Planning for Professional Services

## When to Use
Invoke this skill when planning resource allocation, capacity planning, managing utilization, or making hiring decisions.

## Resource Planning Framework

### 1. Capacity Model

```markdown
## Capacity Calculation

### Available Hours Calculation
Per Person Per Year:
- Working days: 260 (52 weeks × 5 days)
- Less: Holidays: -10 days
- Less: PTO: -15 days
- Less: Training/Development: -5 days
- Less: Internal meetings: -10 days
= Available days: 220 days
× Hours per day: 8 hours
= Available hours: 1,760 hours/year

### Billable Capacity by Role
| Role | FTEs | Target Util | Billable Hrs/FTE | Total Capacity |
|------|------|-------------|------------------|----------------|
| Senior | X | 70% | 1,232 | X,XXX |
| Mid | X | 80% | 1,408 | X,XXX |
| Junior | X | 85% | 1,496 | X,XXX |
| **Total** | | | | **XX,XXX hrs** |
```

### 2. Demand Forecasting

```markdown
## Demand Sources

### Committed Work
| Project | Start | End | Hours Remaining | Resource Needs |
|---------|-------|-----|-----------------|----------------|
| [Project A] | [Date] | [Date] | [Hours] | [Skills needed] |

### Pipeline Work (Probability-Weighted)
| Opportunity | Probability | Hours if Won | Expected Hours |
|-------------|-------------|--------------|----------------|
| [Opp A] | 80% | 500 | 400 |
| [Opp B] | 50% | 800 | 400 |

### Recurring/Retainer Work
| Client | Monthly Hours | Annual Hours |
|--------|---------------|--------------|
| [Client A] | 80 | 960 |
```

### 3. Gap Analysis

```markdown
## Capacity vs. Demand

### 12-Week Rolling View
| Week | Capacity | Demand | Gap | Action |
|------|----------|--------|-----|--------|
| W1 | 400 hrs | 450 hrs | -50 | Overtime/Contractor |
| W2 | 400 hrs | 380 hrs | +20 | OK |
| W3 | 400 hrs | 520 hrs | -120 | Problem - staff needed |

### By Skill/Role
| Skill | Supply (hrs) | Demand (hrs) | Gap | Action |
|-------|--------------|--------------|-----|--------|
| Senior Dev | 800 | 1,000 | -200 | Hire or upskill |
| Designer | 400 | 300 | +100 | Business dev focus |
```

### 4. Utilization Management

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Overall Utilization | 75% | XX% | 🟢🟡🔴 |
| Billable Utilization | 72% | XX% | 🟢🟡🔴 |
| Bench Rate | <15% | XX% | 🟢🟡🔴 |
| Overtime Hours | <5% | XX% | 🟢🟡🔴 |

### 5. Hiring Decision Framework

```markdown
## Hire vs. Contract Analysis

### Indicators to HIRE
- Sustained demand >6 months
- Critical skill gap
- Cultural/team need
- Cost advantage over time
- Client requires named resources

### Indicators to CONTRACT
- Short-term spike (<6 months)
- Specialized skill (not core)
- Uncertain demand
- Need to move fast
- Budget constraints

### Full Cost Comparison
| Factor | FTE | Contractor |
|--------|-----|------------|
| Annual cost | $XXX,XXX | $XXX,XXX |
| Billable hours | X,XXX | X,XXX |
| Effective hourly | $XXX | $XXX |
| Ramp time | X weeks | X weeks |
| Flexibility | Low | High |
```

## Output Template

```markdown
## Resource Planning Analysis

### Current State
**Team Size**: [X] FTEs
**Current Utilization**: [X]%
**Bench**: [X] people / [X]%

### Capacity Summary (Next Quarter)
| Month | Available | Committed | Pipeline | Net |
|-------|-----------|-----------|----------|-----|
| [M1] | [Hrs] | [Hrs] | [Hrs] | [+/-] |
| [M2] | [Hrs] | [Hrs] | [Hrs] | [+/-] |
| [M3] | [Hrs] | [Hrs] | [Hrs] | [+/-] |

### Skill Gap Analysis
| Skill | Gap | Priority | Recommended Action |
|-------|-----|----------|-------------------|
| [Skill] | [Hours] | High | Hire |
| [Skill] | [Hours] | Medium | Train existing |

### Resource Recommendations
1. **[Action]**: [Rationale]
   - Timeline: [When]
   - Cost: [Investment]
   - Expected impact: [Utilization/capacity improvement]

### Hiring Plan
| Role | When | Why | Budget |
|------|------|-----|--------|
| [Role] | [Timeline] | [Justification] | [$XX,XXX] |

### Risks & Mitigations
- [Risk 1]: [Mitigation]
- [Risk 2]: [Mitigation]

### Action Items
1. [ ] [Immediate action]
2. [ ] [This week]
3. [ ] [This month]
```
