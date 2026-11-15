# Adoption measurement and operational handoff

The measurement code is implemented; **no real adoption results have been collected**.

```sh
python -m tower.adoption tests/fixtures/adoption-v1.json --output adoption-synthetic.json
```

Use a versioned input with an explicit `synthetic` boolean. Supply pseudonymous
eligible-user IDs, prior-active IDs, a timezone-aware [start,end) window, unique
event IDs and optional paired task timings. The fixture illustrates 2/3 activation,
1/2 retention, 2/3 completion, 1/2 draft acceptance and 10 seconds mean paired
savings. These are calculated synthetic examples, not customer outcomes.

| Measure | Definition |
| --- | --- |
| Activation | Distinct users completing a workflow / eligible cohort |
| Retention | Prior-active eligible users completing this window / prior-active cohort |
| Completion | Completed events / completed plus failed workflow events |
| Draft acceptance | Accepted / accepted plus rejected draft events |
| Paired time difference | Mean(manual seconds minus assisted seconds) on matched task IDs |

Zero denominators and absent timings return null. Negative savings remain negative.
Out-of-window observations, unknown users/actions, duplicate event IDs and invalid
durations are rejected. An event is a recorded outcome, not an attempt deduced
from a dashboard view; retries need their own recorded attempts. Cohort membership
and timing reports are supplied by the operator, not independently authenticated.

## Pilot and handoff protocol

1. Name a product owner, engineering owner, security reviewer and support contact.
2. Obtain consent for measurement; use pseudonyms and collect no message content.
3. Freeze a two-week pilot cohort and success criteria before collecting results.
   Proposed criteria for review: at least 10 eligible users, 60% activation,
   80% completion, and no unauthorized actions. These are proposed targets.
4. Capture baseline/assisted timings on comparable tasks, including unsuccessful
   work. Record task complexity and sampling limitations separately.
5. Review results weekly alongside security/quality findings. Do not call a small,
   self-selected sample causal productivity evidence.
6. Obtain documented stakeholder acceptance, record unresolved POA&M risks,
   identify service support hours, alert ownership, rollback authority and runbooks.
7. Retain private raw inputs under an approved retention policy. Publish only
   reviewed aggregate results with sample sizes and clear synthetic/live labels.

Handoff artifacts: deployment plan/result, image digest and SBOM, vulnerability
report, acceptance evidence, current SSP/POA&M, adoption report, and named
operational owners. Real stakeholder sign-off remains outstanding.
