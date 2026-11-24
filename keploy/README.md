# Keploy API Record and Replay Testing for ClaimBack

ClaimBack API endpoints can be recorded and re-tested using Keploy for zero-code API regression testing.

## Prerequisites
- Install Keploy CLI:
  ```bash
  curl -O -L https://keploy.io/install.sh && bash install.sh
  ```

## Record Mode
1. Start the ClaimBack server under Keploy recording:
   ```bash
   keploy record -c "python -m app.server 8080"
   ```
2. Make test API calls from the web browser UI (`http://localhost:8080`) or via curl:
   ```bash
   curl -X POST http://localhost:8080/api/analyze \
     -H "Content-Type: application/json" \
     -d '{"rejection_text": "Repudiated citing Clause 4.1 waiting period."}'
   ```
3. Keploy automatically generates and saves HTTP mocks and test cases in `keploy/test-set-0/tests/`.

## Test / Replay Mode
Run automated regression replay against any changes:
```bash
keploy test -c "python -m app.server 8080" --delay 5
```
Keploy simulates incoming requests and compares API responses against recorded golden contracts.
