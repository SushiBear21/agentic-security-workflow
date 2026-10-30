# Project 4 - Final laboratory decision

Status: blocked
Recommended configuration: NONE - blocked

| Configuration | Contract passes | Human passes | Median ms | Max ms | Estimated USD | Eligible |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| temperature-0 | 36/36 | 9/12 | 556.591 | 1426.361 | 0.005179 | False |
| temperature-0.5 | 36/36 | 9/12 | 644.063 | 869.136 | 0.005179 | False |

## Decision basis

36/36 contract checks; 12/12 human drafts; every model call <=15000 ms; known total run cost within its positive soft budget <=USD 1
Set in session 8 after measurement; retrospective lab check, not a prespecified benchmark
Eligible configurations: lowest observed median latency, cost as tie-breaker
The choice is provisional: 12 model calls per configuration cannot establish statistical superiority.
These targets are lab criteria, not a production availability or latency SLO.
Cost estimates use recorded prices; the soft stop is not a guaranteed billing cap.

## Evidence

Report SHA-256: ee9b9b23aa5e87bba9bfb4be21be1ac55abac4a9169ec42286048940949210e9
Review SHA-256: c299052b396923c6fe40c011d6ced714e2688e9b22a44d66bc0f39e579f8bf6e
Fallback drill: broken candidate rejected; reference fallback passed; no production change.

## Remaining boundaries

Synthetic fixtures, a small development dataset, and a single human reviewer limit these results.
Existing app.agent/app.workflow integration, model-driven planning, durable concurrent idempotency, and production deployment remain untested by this companion.
See the governance matrix for the open risks. No NIST compliance or production-readiness certification is asserted.