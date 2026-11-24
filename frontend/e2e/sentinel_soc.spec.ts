import { test, expect } from '@playwright/test';

// Common helper to inject authenticated state into localStorage before navigating
const mockAuth = async (page: any) => {
  await page.addInitScript(() => {
    localStorage.setItem('sentinel_token', 'test_e2e_jwt_token_valid');
    localStorage.setItem(
      'sentinel_user',
      JSON.stringify({
        id: 'usr-e2e-1',
        email: 'analyst@defense.org',
        full_name: 'Lead SOC Analyst',
        is_platform_admin: true,
      })
    );
    localStorage.setItem(
      'sentinel_orgs',
      JSON.stringify([
        {
          id: 'org-e2e-test-1234',
          name: 'E2E Defense Corp',
          slug: 'e2e-defense-corp',
          role: 'Organization Owner',
        },
      ])
    );
    localStorage.setItem('sentinel_active_org', 'org-e2e-test-1234');
    localStorage.setItem(
      'sentinel_active_org_obj',
      JSON.stringify({
        id: 'org-e2e-test-1234',
        name: 'E2E Defense Corp',
        slug: 'e2e-defense-corp',
        role: 'Organization Owner',
      })
    );
  });
};

test.describe('SENTINEL SOC — E2E Test Suite', () => {
  // 1. Login Page
  test('Login Page: Form submission and error state', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid email or password' }),
      });
    });

    await page.goto('/login');
    await expect(page.getByText('AI-Assisted Security Operations Center Platform')).toBeVisible();

    await page.fill('input[type="email"]', 'analyst@defense.org');
    await page.fill('input[type="password"]', 'WrongPassword123!');
    await page.click('button[type="submit"]');

    // Inline error banner should be visible
    await expect(page.getByText('Invalid email or password')).toBeVisible();
  });

  // 2. Registration Page
  test('Registration Page: Form inputs and loading state', async ({ page }) => {
    await page.route('**/api/v1/auth/register', async (route) => {
      await new Promise((r) => setTimeout(r, 200));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'fake_reg_token',
          organizations: [{ id: 'org-new', name: 'New Org' }],
        }),
      });
    });

    await page.goto('/register');
    await expect(page.getByRole('heading', { name: /Sentinel SOC Enrollment/i })).toBeVisible();

    await page.fill('input[placeholder*="Chief Security Officer"]', 'Security Analyst');
    await page.fill('input[placeholder*="cso@defense.org"]', 'newanalyst@defense.org');
    await page.fill('input[placeholder*="Enterprise Security Command"]', 'Defense Corp Global');
    await page.fill('input[placeholder*="••••••••••••"]', 'SecurePass123!');

    const submitBtn = page.getByRole('button', { name: /Establish Organization/i });
    await expect(submitBtn).toBeEnabled();
  });

  // 3. Dashboard Navigation & Metrics
  test('Dashboard: Navigation and Metrics Cards', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/dashboard/stats', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_assets: 8,
          online_sensors: 5,
          offline_sensors: 3,
          total_events_24h: 1250,
          critical_high_alerts: 2,
          open_incidents: 1,
          network_devices_count: 14,
          aws_findings_count: 3,
          severity_distribution: { Critical: 1, High: 1, Medium: 4, Low: 10, Informational: 25 },
          event_trend_24h: [{ time: '12:00', events: 50 }],
          recent_suspicious_ips: [{ ip: '185.220.101.5', severity: 'High', rule: 'PORT_SCAN' }],
          recent_activity: [],
          sensor_health_summary: { Online: 5, Offline: 3, Pending: 0 },
          integration_health: {
            database: { status: 'ONLINE' },
            ai_provider: { status: 'HEALTHY' },
          },
        }),
      });
    });

    await page.goto('/dashboard');
    await expect(page.getByText('Security Operations Center Overview')).toBeVisible();
    await expect(page.getByText('Registered Assets')).toBeVisible();
    await expect(page.getByText('Active Sensors')).toBeVisible();
    await expect(page.getByText('Open Incidents')).toBeVisible();
    await expect(page.getByText('Events (24h)')).toBeVisible();
  });

  // 4. Asset Management
  test('Asset Management: Inventory Table and Filter Controls', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/assets', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'asset-1',
            hostname: 'win-dc-primary',
            os_family: 'Windows',
            os_version: 'Server 2022',
            asset_type: 'Server',
            private_ips: '["10.0.0.10"]',
            health_status: 'online',
            risk_level: 'Low',
            last_seen: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.goto('/assets');
    await expect(page.getByText('Asset Inventory & Endpoint Management')).toBeVisible();
    await expect(page.getByText('win-dc-primary')).toBeVisible();
  });

  // 5. Sensor Management
  test('Sensor Management: Enrollment Token Generator and Health States', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/sensors*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'sensor-1',
            name: 'DC-Primary-Agent',
            os_type: 'Windows',
            version: '1.2.0',
            status: 'Online',
            last_heartbeat: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.goto('/sensors');
    await expect(page.getByText('Sensor Management & Enrollment')).toBeVisible();
    await expect(page.getByText('DC-Primary-Agent')).toBeVisible();
    await expect(page.getByRole('button', { name: /Generate Enrollment Token/i })).toBeVisible();
  });

  // 6. IP Intelligence & Grounding Breakdown
  test('IP Investigation: 5-Tier Grounding, Timeline, and Verdicts', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/ip-intelligence/providers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { provider_name: 'AbuseIPDB', status: 'CONFIGURED', attribution: 'AbuseIPDB APIv2', requests_today: 5, daily_limit: 1000 },
          { provider_name: 'GreyNoise', status: 'CONFIGURED', attribution: 'GreyNoise Community', requests_today: 2, daily_limit: 500 },
        ]),
      });
    });

    await page.route('**/api/v1/ip-intelligence/investigations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/api/v1/ip-intelligence/investigate*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ip_address: '185.220.101.5',
          ip_version: 'IPv4',
          classification: 'Public',
          is_routable: true,
          reputation: 'Malicious',
          asn: { asn: 'AS208323', org: 'Tor Exit Network', country: 'DE' },
          approximate_geolocation: { country: 'Germany', city: 'Frankfurt' },
          grounding: {
            directly_observed: { total_security_events: 4, total_network_connections: 12 },
            imported_threat_intel: {
              results: {
                AbuseIPDB: { reputation: 'Malicious', confidence: 100, attribution: 'AbuseIPDB APIv2' },
                GreyNoise: { reputation: 'Suspicious', confidence: 80, attribution: 'GreyNoise Community' },
              },
            },
            third_party_enrichment: { asn: 'AS208323', as_org: 'Tor Exit Network', country: 'Germany', city: 'Frankfurt' },
            inferred_information: { calculated_reputation: 'Malicious', confidence_score: 95 },
            unavailable_telemetry: ['DNS resolution logs', 'Encrypted TLS payloads'],
          },
          timeline: [
            { timestamp: new Date().toISOString(), event: 'Port Scan Detected', category: 'EVENT', details: 'Triggered PORT_SCAN' },
          ],
        }),
      });
    });

    await page.goto('/ip-intel');
    await expect(page.getByText('Advanced IP Investigation & Threat Feeds')).toBeVisible();

    await page.fill('input[placeholder*="185.220.101.5"]', '185.220.101.5');
    await page.click('button:has-text("Investigate IP")');

    await expect(page.getByText('Evidence Grounding Breakdown')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Directly Observed' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Imported Intel' })).toBeVisible();
  });

  // 7. Network Intelligence & Topology
  test('Network Intelligence: Coverage Gauges and Topology View Switching', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/network/subnets', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/network/devices', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/network/integrations', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/network/coverage', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_subnets: 2,
          monitored_subnets: 2,
          subnet_coverage_percent: 100,
          total_devices: 6,
          monitored_devices_count: 4,
          device_sensor_coverage_percent: 66.7,
          authorized_devices_count: 5,
          unauthorized_devices_count: 1,
        }),
      });
    });
    await page.route('**/api/v1/network/topology', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          observed_links: 1,
          inferred_links: 0,
          nodes: [
            { id: '192.168.1.1', label: 'Default Gateway', node_type: 'GATEWAY', status: 'Online', ip_address: '192.168.1.1' },
            { id: '192.168.1.50', label: 'Workstation-01', node_type: 'ASSET', is_monitored: true, ip_address: '192.168.1.50' },
          ],
          links: [
            { source: '192.168.1.50', target: '192.168.1.1', link_type: 'OBSERVED', discovered_via: 'ARP Cache' },
          ],
        }),
      });
    });

    await page.goto('/network');
    await expect(page.getByText('Network Intelligence & Topology')).toBeVisible();
    await expect(page.getByText('Subnet Coverage', { exact: true })).toBeVisible();
    await expect(page.getByText('Sensor Coverage', { exact: true })).toBeVisible();

    // Switch view to Interactive Topology Graph
    await page.click('button:has-text("Interactive Topology Graph")');
    await expect(page.getByText('Topological Observation Architecture:')).toBeVisible();
    await expect(page.getByText('Enrolled Endpoints & Neighbors')).toBeVisible();
    await expect(page.getByText('Workstation-01')).toBeVisible();
  });

  // 8. Detection Center & Parameter Tuning
  test('Detection Center: Catalog and Parameter Tuning Modal', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/detections/alerts', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/detections/correlations', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/detections/rules', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'rule-1',
            rule_code: 'AUTH_FAILED_BURST',
            name: 'Repeated Failed Login Attempts (Single Host)',
            category: 'Authentication',
            severity: 'High',
            is_enabled: true,
            threshold: 5,
            time_window_seconds: 300,
            is_correlation_rule: false,
          },
        ]),
      });
    });

    await page.goto('/detections');
    await expect(page.getByText('Detection Center & Threat Rules Engine')).toBeVisible();

    // Switch to Configured Rules tab
    await page.click('button:has-text("Configured Rules")');
    await expect(page.getByText('Repeated Failed Login Attempts (Single Host)')).toBeVisible();

    // Click tune button
    await page.click('button[title="Tune rule parameters"]');
    await expect(page.getByText('Tune Detection Rule Parameters')).toBeVisible();
    await expect(page.getByText('Trigger Threshold (Hit Count)')).toBeVisible();

    // Cancel modal
    await page.click('button:has-text("Cancel")');
  });

  // 9. Incident Management & CSV Export
  test('Incident Management: Master-Detail Triage and Timeline CSV Export', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/incidents*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'inc-01',
            title: 'Brute-Force SSH Attack on Bastion',
            severity: 'High',
            status: 'Investigating',
            created_at: new Date().toISOString(),
            description: 'Repeated authentication failures observed from 198.51.100.42',
            comments: [],
          },
        ]),
      });
    });

    await page.route('**/api/v1/incidents/inc-01/timeline', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'entry-1',
            event_type: 'INCIDENT_CREATED',
            actor_type: 'SYSTEM',
            actor_name: 'Detection Engine',
            title: 'Incident Automatically Escalated',
            description: 'Escalated from high-severity alert',
            timestamp: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.goto('/incidents');
    await expect(page.getByText('Incident Management & Case Response')).toBeVisible();
    await expect(page.getByRole('heading', { level: 3, name: 'Brute-Force SSH Attack on Bastion' })).toBeVisible();

    // Switch to Timeline tab
    await page.click('button:has-text("Chronological Timeline")');
    await expect(page.getByText('Download CSV')).toBeVisible();
  });

  // 10. AWS Cloud Security
  test('AWS Security: Zero-Cost Safety Notice and IAM Template Modal', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/aws/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          provider: 'aws',
          connected_accounts_count: 0,
          total_findings: 0,
          simulation_fixtures_loaded: false,
          free_tier_enforced: true,
        }),
      });
    });
    await page.route('**/api/v1/aws/accounts', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/aws/findings', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/aws/resources', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/v1/aws/iam-policy-template', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          policy_name: 'SentinelSOCReadOnlySecurityAuditPolicy',
          policy_json: {
            Version: '2012-10-17',
            Statement: [
              {
                Sid: 'SentinelReadOnlySecurityHubAndGuardDuty',
                Effect: 'Allow',
                Action: ['securityhub:GetFindings', 'guardduty:GetFindings'],
                Resource: '*',
              },
            ],
          },
        }),
      });
    });

    await page.goto('/aws-security');
    await expect(page.getByText('AWS Cloud Security & Findings')).toBeVisible();
    await expect(page.getByText('Zero Cost AWS Integration Architecture:')).toBeVisible();
    await expect(page.getByText('Load Zero-Cost Fixtures')).toBeVisible();

    // Open IAM Policy Template modal
    await page.click('button:has-text("IAM Policy Template")');
    await expect(page.getByText('Least-Privilege Read-Only IAM Policy')).toBeVisible();
    await page.click('button:has-text("Close")');
  });

  // 11. AI Security Analyst
  test('AI Security Analyst: Investigation Form and Advisory Briefing', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/ai-analyst/investigate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          provider: 'fallback',
          model: 'heuristic-rules-v1',
          analysis:
            '### 1. Observable Facts\nMultiple failed logins from 198.51.100.42.\n\n### 2. Threat Intel\nConfirmed SSH brute force IP.\n\n### 3. Hypotheses\nAttacker attempting credential stuffing.\n\n### 4. Recommendations\nIsolate host and block remote IP.\n\n### 5. Unknowns\nInternal packet capture not configured on subnet.',
          evidence_sources: ['SecurityEventLog', 'AbuseIPDB Feed'],
        }),
      });
    });

    await page.goto('/ai-analyst');
    await expect(page.getByText('Sentinel AI Security Analyst')).toBeVisible();
    await expect(page.getByText('Advisory AI • Human-in-the-Loop')).toBeVisible();

    // Execute an investigation
    await page.click('button:has-text("Execute Investigation")');
    await expect(page.getByText('Advisory Security Investigation Briefing')).toBeVisible();
  });

  // 12. AI Helpdesk & RAG
  test('AI Helpdesk: Conversation Chat and Documentation Context', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/ai-helpdesk/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/ai-helpdesk');
    await expect(page.getByText('Sentinel AI Helpdesk & Troubleshooting Assistant')).toBeVisible();
    await expect(page.getByRole('button', { name: /New Conversation/i })).toBeVisible();
  });

  // 13. Reports & Compliance Exports
  test('Reports & Compliance Exports: Executive Stats and Download Buttons', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/reports/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_assets_monitored: 8,
          total_network_devices_discovered: 14,
          total_security_events_recorded: 2500,
          total_incidents: 3,
          resolved_incidents: 2,
          active_aws_findings: 1,
          incident_resolution_rate: '66.7%',
          generated_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto('/reports');
    await expect(page.getByText('Security Reports & Compliance Exports')).toBeVisible();
    await expect(page.getByText('Incident Cases Ledger')).toBeVisible();
    await expect(page.getByText('Security Telemetry Events')).toBeVisible();
    await expect(page.getByText('Threat Intelligence Indicators')).toBeVisible();
    await expect(page.getByText('Network Inventory & Devices')).toBeVisible();
    await expect(page.getByText('AWS Cloud Security Findings')).toBeVisible();
  });

  // 14. Notifications Center
  test('Notifications Center: List Alerts and Mark Read', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/notifications', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'notif-1',
            title: 'Critical Alert: Brute Force Detected',
            message: 'Multiple failed SSH attempts on bastion host',
            severity: 'Critical',
            is_read: false,
            created_at: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.route('**/api/v1/notifications/mark-all-read', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' }),
      });
    });

    await page.goto('/notifications');
    await expect(page.getByText('Notifications & Security Broadcasts')).toBeVisible();
    await expect(page.getByText('Critical Alert: Brute Force Detected')).toBeVisible();
    await expect(page.getByRole('button', { name: /Mark All as Read/i })).toBeVisible();
  });

  // 15. Error State Handling
  test('Error State Handling: Graceful Alert on API 500 Failure', async ({ page }) => {
    await mockAuth(page);

    await page.route('**/api/v1/ip-intelligence/investigate*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error in Intelligence Adapter' }),
      });
    });

    await page.route('**/api/v1/ip-intelligence/providers', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.route('**/api/v1/ip-intelligence/investigations', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto('/ip-intel');

    await page.fill('input[placeholder*="185.220.101.5"]', '1.1.1.1');
    await page.click('button:has-text("Investigate IP")');

    await expect(page.getByText('Internal Server Error in Intelligence Adapter')).toBeVisible();
  });
});
