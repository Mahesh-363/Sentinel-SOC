# SENTINEL SOC — Threat Intelligence Integration Guide
**Last Updated:** November 16, 2026 (Release 2 Verification Gap Closure)

## 1. Overview & Free-Tier Architecture

Sentinel SOC integrates with leading open-access and community threat intelligence providers to enrich public IP addresses, detect command-and-control (C2) servers, identify malicious scanners, and alert on compromised infrastructure.

In strict adherence to Sentinel SOC's **Free-Tier Policy**:
- **Zero Paid Subscriptions:** All supported integrations utilize genuinely free community tiers.
- **Graceful Degradation:** If API keys are omitted or quotas are exhausted, Sentinel SOC operates normally without failures. Unconfigured providers are reported as `NOT CONFIGURED` with explicit attribution.
- **Local Caching (TTL-based):** Results are cached locally (in-memory and database `ThreatIntelCache`) for a default of 6 hours (configurable via `THREAT_INTEL_CACHE_TTL_HOURS`) to prevent redundant queries and preserve free API rate limits.
- **Truth in Grounding:** Sentinel SOC strictly distinguishes **Directly Observed Local Telemetry** from **Imported Third-Party Threat Intelligence**. Unfamiliar public IPs are never assumed to be malicious without verifiable corroboration.

---

## 2. Supported Threat Intelligence Providers

| Provider | Integration Type | Free Tier Quota / Model | Primary Indicators | Config Environment Variable |
| :--- | :--- | :--- | :--- | :--- |
| **AbuseIPDB** | REST API v2 | 1,000 checks / day (Free registered account) | Abuse Confidence Score (0–100%), Total Reports, Distinct Reporters, ISP, Usage Type | `ABUSEIPDB_API_KEY` |
| **GreyNoise** | REST API v3 (Community) | Free Community Account (Unlimited rate-limited checks) | Mass internet background scanner vs. targeted attack, Benign RIOT tag (Cloudflare, Google, CDNs), Actor, Classification | `GREYNOISE_API_KEY` |
| **AlienVault OTX** | REST API v1 | Free Community Open Threat Exchange | Community Pulses, Associated Threat Groups, Malware Families, IOC References | `ALIENVAULT_OTX_KEY` |
| **Spamhaus** | DNSBL / DQS (Data Query Service) | Free Community Account (Up to 300,000 queries / month) | Blocklist categories: SBL (Spam/Direct Malware), XBL (Exploits/Botnets), PBL (End-user IP ranges), CSS (Spam Snowshoe) | `SPAMHAUS_DQS_KEY` |

---

## 3. Provider Detailed Specifications

### 3.1 AbuseIPDB
- **Endpoint:** `GET https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90`
- **Authentication Header:** `Key: {ABUSEIPDB_API_KEY}`
- **Normalized Data Extracted:**
  - `confidence`: `abuseConfidenceScore` (0–100)
  - `threat_type`: Determined by categories (e.g., SSH Brute-force, Port Scan, Web Attack)
  - `last_seen`: `lastReportedAt`
  - `reputation`: Severe if confidence >= 50%, Suspicious if confidence > 15%, Benign otherwise
- **Handling Free-Tier Limits:**
  - Standard HTTP 429 indicates daily limit (1,000 queries) reached. Sentinel marks provider status `RATE_LIMITED` and returns cached or un-enriched ground truth.

### 3.2 GreyNoise Community API
- **Endpoint:** `GET https://api.greynoise.io/v3/community/{ip}`
- **Authentication Header:** `key: {GREYNOISE_API_KEY}`
- **Normalized Data Extracted:**
  - `noise`: Boolean flag indicating mass scanning activity
  - `riot`: Boolean flag for Known Benign Services (Googlebot, Microsoft 365, Cloudflare)
  - `classification`: `malicious`, `benign`, or `unknown`
  - `actor` / `tags`: Known scanning campaign (e.g., Shodan, Censys, Mirai)
- **SOC Analyst Value:** Eliminates false alarms caused by benign internet scanners or legitimate CDNs.

### 3.3 AlienVault OTX (Open Threat Exchange)
- **Endpoint:** `GET https://otx.alienvault.com/api/v1/indicators/{IPv4|IPv6}/{ip}/general`
- **Authentication Header:** `X-OTX-API-KEY: {ALIENVAULT_OTX_KEY}`
- **Normalized Data Extracted:**
  - `pulse_count`: Number of curated community threat pulses referencing this IP
  - `malware_families`: Names of malware families associated with pulses (e.g., Cobalt Strike, Emotet)
  - `references`: URLs to investigative reports, pastebins, or security write-ups

### 3.4 Spamhaus DQS (Data Query Service)
- **Lookup Method:** DNSBL query via `<ip_reversed>.zen.spamhaus.org` (or dedicated DQS key `<ip_reversed>.<auth_key>.dq.spamhaus.net`)
- **Return Code Taxonomy:**
  - `127.0.0.2`: SBL (Spamhaus Block List — verified spammers & spam hosts)
  - `127.0.0.3`: CSS (Composite Snowshoe Spam List)
  - `127.0.0.4 - 127.0.0.7`: XBL (Exploits Block List — hijacked PCs, 3rd party exploits, worm/virus/botnet infected hosts)
  - `127.0.0.10 - 127.0.0.11`: PBL (Policy Block List — dynamic/residential IP address pools that should not send unauthenticated mail)

---

## 4. Normalized Indicator Schema

All disparate external threat feeds are transformed into Sentinel SOC's unified indicator format:

```json
{
  "indicator_value": "185.220.101.5",
  "indicator_type": "IPv4",
  "provider": "AbuseIPDB",
  "reputation": "Malicious",
  "confidence": 100,
  "status": "SUCCESS",
  "attribution": "Threat data provided by AbuseIPDB (https://www.abuseipdb.com)",
  "first_seen": null,
  "last_seen": "2026-11-16T10:15:00Z",
  "reference": "https://www.abuseipdb.com/check/185.220.101.5",
  "source_timestamp": "2026-11-16T12:00:00Z",
  "expires_at": "2026-11-16T18:00:00Z",
  "raw_details": {
    "abuse_confidence_score": 100,
    "total_reports": 450,
    "country_code": "DE",
    "isp": "Tor Exit Node",
    "is_whitelisted": false
  }
}
```

---

## 5. Verification & Health Monitoring

To verify provider configuration and status via the API:
```bash
curl -X GET http://localhost:8000/api/v1/ip-intelligence/providers \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-Organization-Id: <ORG_ID>"
```

Response:
```json
[
  {
    "provider_name": "AbuseIPDB",
    "status": "CONFIGURED",
    "attribution": "AbuseIPDB Community Database",
    "requests_today": 12,
    "daily_limit": 1000
  },
  {
    "provider_name": "GreyNoise",
    "status": "CONFIGURED",
    "attribution": "GreyNoise Community",
    "requests_today": 8,
    "daily_limit": 500
  },
  {
    "provider_name": "AlienVault OTX",
    "status": "NOT CONFIGURED",
    "attribution": "AT&T Cybersecurity AlienVault OTX",
    "requests_today": 0,
    "daily_limit": 10000
  },
  {
    "provider_name": "Spamhaus",
    "status": "NOT CONFIGURED",
    "attribution": "Spamhaus Block Lists",
    "requests_today": 0,
    "daily_limit": 300000
  }
]
```

### Verification Note:
In the default offline testing environment, threat adapters are verified via `backend/tests/test_threat_intel_adapters.py`. When live API keys are not supplied in `.env`, the system safely marks each provider as `NOT CONFIGURED` and operates using local telemetry without attempting paid upgrades or fabricating results.
