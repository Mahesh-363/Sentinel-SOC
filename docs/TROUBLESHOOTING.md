# SENTINEL SOC — Troubleshooting & Diagnostic Playbook

This guide provides troubleshooting procedures and diagnostic checklists for issues that may arise during installation, sensor deployment, or day-to-day SOC operations.

---

## 🔍 Quick Diagnostic Checklist

| Check | Command / Verification | Expected Result |
|---|---|---|
| **API Health** | `curl -f http://localhost:8000/health` | `{"status":"ok","app":"Sentinel SOC"}` |
| **Backend Tests** | `pytest backend/tests -v` | `6 passed in <5s` |
| **Database File** | Verify `sentinel.db` exists in project root | File size > 50KB |
| **Frontend UI** | Browse to `http://localhost:3000` | Login screen renders without errors |
| **Sensor Agent** | `python sensor/install.py run` | Logs output showing collection cycles |

---

## 🚨 Common Issues & Remediation

### 1. "AI quota temporarily unavailable. Core Sentinel SOC functionality is still operational."
- **Cause:** The Google Gemini Free Tier rate limit or daily quota has been exceeded (HTTP 429), or no API key has been configured.
- **Impact:** Non-destructive. Sentinel SOC automatically engages its deterministic rule-based fallback engine. All asset tracking, detection rules, incident management, and reporting remain fully operational.
- **Resolution:**
  - Verify your API key in `.env`: `GEMINI_API_KEY=...`
  - Switch to a local offline LLM by setting:
    ```env
    AI_PROVIDER=local
    LOCAL_AI_URL=http://localhost:11434
    LOCAL_AI_MODEL=llama3
    ```
  - Or continue using the built-in deterministic fallback (`AI_PROVIDER=fallback`).

### 2. Sensor Enrollment Returns "Token expired or invalid" (HTTP 400)
- **Cause:** Enrollment tokens are single-use and expire after 60 minutes by default.
- **Resolution:**
  1. Open the Sentinel SOC console and navigate to **Sensors** (`/sensors`).
  2. Click **Generate Enrollment Token** to create a fresh token.
  3. Re-run enrollment on the host:
     ```bash
     python install.py enroll --url http://<server_ip>:8000/api/v1 --token <NEW_TOKEN>
     ```

### 3. Sensor Returns "HTTP 403 Forbidden: Sensor credentials have been revoked"
- **Cause:** An analyst clicked **Revoke Sensor Credentials** in the console or executed the containment playbook.
- **Resolution:**
  - The previous API key is permanently invalidated.
  - To re-admit the host, delete `sensor/config.yaml`, generate a new enrollment token in the console, and re-enroll the agent.

### 4. Cross-Tenant "HTTP 403 Forbidden: Access denied to organization"
- **Cause:** The authenticated user is attempting to query data belonging to an organization in which they do not hold an active membership.
- **Resolution:**
  - In the Sentinel UI top navigation bar, ensure the active organization dropdown matches the organization containing the target assets.
  - An Organization Administrator can invite the user via `/organizations` if access is required.

### 5. Windows Event Log Collector: "Access Denied" (Event ID 4625/4624)
- **Cause:** Reading the Windows Security Event Log requires administrative privileges (`SeSecurityPrivilege`).
- **Resolution:**
  - Run PowerShell or Command Prompt as **Administrator** when executing `python install.py run` or installing the Windows Service via `python install.py install-windows`.

### 6. Linux Sensor: "Permission Denied: /var/log/auth.log"
- **Cause:** Debian/Ubuntu restricts `/var/log/auth.log` reading to root and members of the `adm` group.
- **Resolution:**
  - Add the service user to the `adm` group:
    ```bash
    sudo usermod -a -G adm sentinel
    ```
  - Or run the sensor service via `systemd` with root service credentials:
    ```bash
    sudo python install.py install-systemd
    ```

### 7. Attack Simulation Records Appearing in Production Reports
- **Cause:** Simulated attack scenarios were triggered in the Attack Lab (`/simulation`).
- **Resolution:**
  - All simulated records are marked `is_simulated = True` and badge-tagged `SIMULATED` in the UI.
  - To remove all simulated data without affecting genuine telemetry:
    1. Navigate to **Attack Lab** (`/simulation`).
    2. Click **Safe Reset Simulation Data**.
    3. All simulated events, alerts, and incidents are instantly removed.

---

## 🛠️ Diagnostic "Explain This Error" Tool

Sentinel SOC includes an integrated diagnostic tool powered by local RAG documentation.
- When an error occurs in the UI, click the floating **Diagnostic Assistant / Explain Error** button.
- Paste the error message or stack trace.
- The assistant redacts sensitive credentials and cross-references Sentinel documentation to provide immediate remediation guidance.
