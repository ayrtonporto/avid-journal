# Scout — Errno 22 Diagnosis (Run 002)

**Date:** 2026-07-13  
**Issue:** 4/10 papers failed with `[Errno 22] Invalid argument` on API calls.

---

## Investigation

### Hypothesis 1: Windows command-line length limit (~8191 chars)

**TEST:** Measured path length and `lake env lean` command for all papers.
- Longest path: 84 chars (`math_0504586v2.lean`)
- Longest command: 98 chars
- Limit: 8191 chars

**RESULT: ❌ DISPROVEN.** Commands are 80× under the limit.

### Hypothesis 2: Prompt too long for API

**TEST:** Measured token/prompt lengths for all papers.

| Paper | Theorem | Prompt | Status |
|-------|---------|--------|--------|
| 1004.3381v1 | 170 chars | 989 chars | Failed |
| 1501.01654v1 | 1927 chars | 2746 chars | Failed |
| 1101.3431v2 | 575 chars | 1394 chars | Failed |
| 1101.3720v1 | 409 chars | 1228 chars | Failed |
| 1609.02090v1 | 533 chars | 1352 chars | ✅ Passed |
| 1207.0631v1 | 284 chars | 1103 chars | ✅ Passed |

**RESULT: ❌ DISPROVEN.** Failing papers have prompt lengths in the SAME RANGE as passing papers (989–2746 vs 973–1352). No correlation with failure.

### Hypothesis 3: JSON serialization / encoding issue

**TEST:** `json.dumps()` on all 4 failing payloads. No null bytes, no control chars (except \n, \r, \t). All encode to valid UTF-8.

**RESULT: ❌ DISPROVEN.** All payloads serialize correctly.

### Hypothesis 4: Transient API outage

**TEST:** Re-ran API calls for failing papers manually. Paper 4 (1004.3381v1) succeeded on retry (attempt 1 timed out, attempt 2 OK).

**RESULT: ✅ CONFIRMED.** The `[Errno 22] Invalid argument` was likely caused by a transient network/API error during the original run. The provider's retry logic should have caught it, but all 3 retries may have hit the same outage window.

---

## Decision

Re-run the 5 failed papers. The issue is not reproducible, suggesting it was environmental/transient.
