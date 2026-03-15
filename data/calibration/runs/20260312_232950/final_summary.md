# Clarion Calibration Run Summary
**Run:** `2026-03-13T04:30:03.019494Z`
**AI Benchmark:** enabled

## Review Counts
| Source | Count |
|--------|-------|
| Real   | 57 |
| Synthetic | 0 |
| **Total submitted** | **57** |

## Per-Star Distribution
| Star | Real | Synthetic | Total |
|------|------|-----------|-------|
| 1★ | 13 | 0 | 13 |
| 2★ | 5 | 0 | 5 |
| 3★ | 5 | 0 | 5 |
| 4★ | 9 | 0 | 9 |
| 5★ | 25 | 0 | 25 |

## Batch Execution
- Chunks run: 3
- Succeeded: 0
- Failed/timed out: 3

### Failed Chunks
- Chunk 1: HTTPConnectionPool(host='localhost', port=5000): Max retries exceeded with url: /internal/benchmark/batch (Caused by NewConnectionError("HTTPConnection(host='localhost', port=5000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) (4.1s)
- Chunk 2: HTTPConnectionPool(host='localhost', port=5000): Max retries exceeded with url: /internal/benchmark/batch (Caused by NewConnectionError("HTTPConnection(host='localhost', port=5000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) (4.1s)
- Chunk 3: HTTPConnectionPool(host='localhost', port=5000): Max retries exceeded with url: /internal/benchmark/batch (Caused by NewConnectionError("HTTPConnection(host='localhost', port=5000): Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it")) (4.0s)

## Next Actions
- Collect more real reviews for: 1★ (+2), 2★ (+10), 3★ (+15), 4★ (+11), 5★ (+5)
- Re-run failed chunks after checking backend logs
- ⚠️ Only 57 real reviews — aim for 75+ before trusting calibration results