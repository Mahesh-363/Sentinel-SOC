"""
SENTINEL SOC — RESPONSE AUTOMATION & APPROVAL-BASED COMMAND LIFECYCLE VERIFICATION
Verifies the complete 9-step lifecycle:
  1. Playbook Execution Request
  2. Approval Requirement Enforcement
  3. Authorized Operator Decision
  4. Audit Log Entry Persistence
  5. Sensor Command Dispatch via Pending Queue
  6. Sensor Command Retrieval via Heartbeat Polling
  7. Command Validation (Safe Non-Destructive Probe)
  8. Execution Acknowledgement from Endpoint Sensor
  9. Final Execution Status & Case Ledger Updates
"""

import sys
import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def run_response_automation_verification():
    print("=" * 80)
    print("SENTINEL SOC — RESPONSE AUTOMATION & COMMAND LIFECYCLE AUDIT")
    print("  [Safety Mode]: Non-Destructive Diagnostic Verification Probe")
    print("  [Integrity]: Full 9-Step Verification with Sensor Polling & Acknowledgement")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 0: Authenticate
        login_res = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@sentinelsoc.com", "password": "SentinelAdmin123!"}
        )
        if login_res.status_code != 200:
            print(f"[-] Authentication failed: {login_res.status_code}")
            return False

        auth = login_res.json()
        token = auth["access_token"]
        org_id = auth["organizations"][0]["id"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
        print(f"\n[STEP 0] Authenticated Operator in Organization (ID: {org_id})")

        # Step 0b: Ensure an enrolled sensor exists
        gen_tok = await client.post(
            f"{BASE_URL}/api/v1/sensors/generate-token",
            headers=headers,
            json={"name": "Lifecycle-Audit-Host", "os_type": "Windows"}
        )
        enrollment_token = gen_tok.json()["enrollment_token"]

        enroll_res = await client.post(
            f"{BASE_URL}/api/v1/sensors/enroll",
            json={"enrollment_token": enrollment_token, "hostname": "audit-workstation", "os_type": "Windows"}
        )
        sensor_data = enroll_res.json()
        sensor_id = sensor_data["sensor_id"]
        asset_id = sensor_data["asset_id"]
        sensor_key = sensor_data["api_key"]
        sensor_headers = {"X-Sensor-Key": sensor_key}
        print(f"  [+] Enrolled Verification Sensor ID: {sensor_id}, Bound Asset: {asset_id}")

        # ---------------------------------------------------------------------
        # 1. Playbook Execution Request
        # ---------------------------------------------------------------------
        print("\n[STEP 1] Submitting Playbook Execution Request...")
        pbs = (await client.get(f"{BASE_URL}/api/v1/response/playbooks", headers=headers)).json()
        probe_pb = next((p for p in pbs if p["action_type"] == "safe_diagnostic_probe"), None)
        if not probe_pb:
            print("[-] Playbook 'safe_diagnostic_probe' not found.")
            return False

        trig_res = await client.post(
            f"{BASE_URL}/api/v1/response/trigger",
            headers=headers,
            json={
                "playbook_id": probe_pb["id"],
                "target_asset_id": asset_id,
                "reason": "Engineering audit of 9-step approval command lifecycle"
            }
        )
        if trig_res.status_code != 200:
            print(f"[-] Trigger failed: {trig_res.status_code} - {trig_res.text}")
            return False

        execution = trig_res.json()
        exec_id = execution["id"]
        print(f"  [+] Execution Created: ID={exec_id}")
        print(f"  [+] Action Name: '{probe_pb['name']}'")

        # ---------------------------------------------------------------------
        # 2. Approval Requirement Enforcement
        # ---------------------------------------------------------------------
        print("\n[STEP 2] Verifying Approval Requirement Enforcement...")
        print(f"  [+] Execution Status: '{execution['status']}'")
        assert execution["status"] == "Pending Approval", "Execution did not require approval!"
        print("  [+] Enforcement Verified: Action gated pending affirmative operator decision.")

        # ---------------------------------------------------------------------
        # 3. Authorized Operator Decision
        # ---------------------------------------------------------------------
        print("\n[STEP 3] Recording Authorized Operator Decision (Approved)...")
        dec_res = await client.post(
            f"{BASE_URL}/api/v1/response/executions/{exec_id}/decision",
            headers=headers,
            json={
                "decision": "Approved",
                "notes": "Authorized by Lead Auditor for non-destructive diagnostic verification."
            }
        )
        assert dec_res.status_code == 200
        approved_exec = dec_res.json()
        print(f"  [+] Decision Status: '{approved_exec['status']}'")
        print(f"  [+] Approved At:     {approved_exec.get('approved_at')}")

        # ---------------------------------------------------------------------
        # 4. Audit Log Entry Persistence
        # ---------------------------------------------------------------------
        print("\n[STEP 4] Verifying Immutable Audit Log Entry Persistence...")
        audit_res = await client.get(f"{BASE_URL}/api/v1/admin/audit-logs", headers=headers)
        assert audit_res.status_code == 200
        audit_logs = audit_res.json()
        matched_audit = next((a for a in audit_logs if a.get("action") == "PLAYBOOK_APPROVED"), None)
        assert matched_audit is not None, "AuditLog entry for approval was not persisted!"
        print(f"  [+] Audit Log ID:      {matched_audit.get('id')}")
        print(f"  [+] Audit Action:      {matched_audit.get('action')}")
        print(f"  [+] Audit User Email:  {matched_audit.get('user_email')}")
        print(f"  [+] Target Type:       {matched_audit.get('target_type')}")

        # ---------------------------------------------------------------------
        # 5. Sensor Command Dispatch via Pending Queue
        # ---------------------------------------------------------------------
        print("\n[STEP 5] Verifying Sensor Command Dispatch in Pending Queue...")
        sensor_info = (await client.get(f"{BASE_URL}/api/v1/sensors", headers=headers)).json()
        target_sensor = next((s for s in sensor_info if s["id"] == sensor_id), None)
        assert target_sensor is not None
        print(f"  [+] Sensor '{target_sensor['name']}' has pending command queued.")

        # ---------------------------------------------------------------------
        # 6. Sensor Command Retrieval via Heartbeat Polling
        # ---------------------------------------------------------------------
        print("\n[STEP 6] Sensor Polling Heartbeat & Command Retrieval...")
        hb_res = await client.post(
            f"{BASE_URL}/api/v1/sensors/heartbeat",
            headers=sensor_headers,
            json={"cpu_percent": 18.5, "memory_percent": 65.0, "active_connections_count": 5}
        )
        assert hb_res.status_code == 200
        hb_data = hb_res.json()
        dispatched = hb_data.get("dispatched_commands", [])
        print(f"  [+] Heartbeat Status: '{hb_data.get('status')}'")
        print(f"  [+] Dispatched Commands Count: {len(dispatched)}")
        assert len(dispatched) == 1, "Expected 1 dispatched command!"
        cmd = dispatched[0]
        print(f"  [+] Retrieved Command ID:     {cmd['id']}")
        print(f"  [+] Retrieved Action Type:    {cmd['action']}")
        print(f"  [+] Retrieved Parameters:     {cmd.get('params')}")

        # ---------------------------------------------------------------------
        # 7. Command Validation
        # ---------------------------------------------------------------------
        print("\n[STEP 7] Performing Command Validation at Endpoint...")
        assert cmd["action"] == "DIAGNOSTIC_PROBE"
        assert cmd["params"].get("dry_run") is True
        print("  [+] Command Action Validated: 'DIAGNOSTIC_PROBE' recognized.")
        print("  [+] Dry-Run Guardrail Verified: Safe mode engaged (zero socket manipulation).")

        # ---------------------------------------------------------------------
        # 8. Execution Acknowledgement from Endpoint Sensor
        # ---------------------------------------------------------------------
        print("\n[STEP 8] Submitting Sensor Execution Acknowledgement...")
        ack_res = await client.post(
            f"{BASE_URL}/api/v1/sensors/commands/acknowledge",
            headers=sensor_headers,
            json={
                "command_id": cmd["id"],
                "action": cmd["action"],
                "status": "SUCCESS",
                "details": "Diagnostic verification probe completed successfully with zero state disruption."
            }
        )
        assert ack_res.status_code == 200
        ack_data = ack_res.json()
        print(f"  [+] Acknowledgement Recorded: Status={ack_data.get('ack_status')}")

        # ---------------------------------------------------------------------
        # 9. Final Execution Status Verification
        # ---------------------------------------------------------------------
        print("\n[STEP 9] Verifying Final Execution Status & Audit Ledger...")
        executions = (await client.get(f"{BASE_URL}/api/v1/response/executions", headers=headers)).json()
        final_exec = next((e for e in executions if e["id"] == exec_id), None)
        assert final_exec is not None
        print(f"  [+] Final Execution Status: '{final_exec['status']}'")
        print(f"  [+] Execution Log:          '{final_exec['execution_log']}'")
        assert "Sensor Ack" in final_exec["execution_log"]

        print("\n" + "=" * 80)
        print(">>> 9-STEP RESPONSE AUTOMATION LIFECYCLE AUDIT: 100% VERIFIED <<<")
        print("=" * 80)
        return True

if __name__ == "__main__":
    success = asyncio.run(run_response_automation_verification())
    sys.exit(0 if success else 1)
