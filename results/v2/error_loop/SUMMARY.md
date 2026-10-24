# Error Loop signature (≥3 consecutive ops with the same normalized error line, any command)

**Code:** `signatures.error_signature` / `error_loops`.

**How the error line is found:**
- An op counts as erroring if:
  - its exit code is non-zero and a line contains an error word, or
  - it exits 0 but a strong error line is present, such as a traceback or `X: command not found`.
- Read ops that exit 0 are never errors.

**Normalization:**
- The line is lower-cased.
- Hex strings, timings and /tmp names are replaced.
- Other digits are kept.

**Change made during this step:** 33 of 92 first-pass loops had no error line and were dropped. They were build progress, passing-test lines and progress dots. A rerun would give exactly the same result.

| Model | loops | runs with an Error Loop [95% CI] | ops in loops (after the first) | loops with one command | members that are exact repeats |
|---|---|---|---|---|---|
| Gemini | 27 | 1.1% [0.7, 1.7] | 0.1% | 0% | 0% |
| Luna | 24 | 1.1% [0.7, 1.7] | 0.1% | 0% | 0% |
| Terra | 8 | 0.4% [0.1, 0.7] | 0.0% | 0% | 0% |

- Every loop uses different commands, so exact-repeat counting misses all of them.
- 12 of Luna's 24 loops are the BusyBox `grep: unrecognized option: include=*.go` error.
- **Pilot contribution mix:** there is only one loop (Luna webclients, ops 9–11). Both of its later members are labelled non-distinct. The pilot is too small to estimate a mix.
- **Verdict:** the pattern is real but rare (about 1% of runs). This rests on facts only; the labels are not human-validated.
