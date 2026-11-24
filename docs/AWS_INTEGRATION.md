# SENTINEL SOC — AWS Cloud Security Integration Guide
**Last Updated:** November 16, 2026 (Release 2 Verification Gap Closure)

## 1. Zero-Cost & Free-Tier Architectural Guarantees

Sentinel SOC provides cloud security monitoring and posture management (CSPM) for Amazon Web Services (AWS) under a strict **Zero-Cost Policy**:

- **No Auto-Provisioned Paid Cloud Resources:** Sentinel SOC **never** provisions EC2 instances, RDS databases, NAT Gateways, KMS keys, or managed clusters.
- **Zero-Cost Offline Learning Mode:** Users do **not** need an AWS account or active cloud subscription to test, evaluate, or demonstrate Sentinel SOC. A 1-click built-in offline fixture generator seeds realistic, high-fidelity findings and cloud assets.
- **Read-Only Telemetry:** When connected to a real AWS account, Sentinel SOC requires **strictly read-only permissions** to query existing security telemetry (Security Hub, GuardDuty, IAM credential reports, S3 bucket posture).

---

## 2. Cross-Account AssumeRole Architecture

Sentinel SOC uses standard AWS Security Best Practices for multi-account and third-party monitoring via the **AWS Security Token Service (STS) `AssumeRole`** API.

### Confused Deputy Prevention with External ID
To protect against the "Confused Deputy" vulnerability (where an attacker supplies another tenant's Role ARN):
1. Sentinel SOC generates a cryptographically random, tenant-isolated **External ID** for every registered AWS account connection.
2. The user configures this External ID in their IAM Role's trust policy (`sts:ExternalId`).
3. During every API synchronization, Sentinel passes this unique External ID to `sts:AssumeRole`. AWS denies the request if the External ID does not match.

#### Trust Relationship Policy (`TrustPolicy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_SENTINEL_ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "YOUR_ORGANIZATION_EXTERNAL_ID"
        }
      }
    }
  ]
}
```

---

## 3. Least-Privilege Read-Only IAM Policy Template

Sentinel SOC provides an interactive, 1-click JSON policy generator directly in the UI (`/aws-security`) and via API (`/api/v1/aws/iam-policy-template`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SentinelReadOnlySecurityHubAndGuardDuty",
      "Effect": "Allow",
      "Action": [
        "guardduty:Get*",
        "guardduty:List*",
        "securityhub:Get*",
        "securityhub:List*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SentinelReadOnlyIAMAndS3Audit",
      "Effect": "Allow",
      "Action": [
        "iam:GenerateCredentialReport",
        "iam:Get*",
        "iam:List*",
        "s3:GetBucketAcl",
        "s3:GetBucketPolicy",
        "s3:GetBucketPublicAccessBlock",
        "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SentinelReadOnlyEC2AndVPCFlow",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
        "ec2:DescribeFlowLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 4. Error Code Mapping & Failure States

The adapter maps AWS STS and service exceptions to clear, user-facing error states:

| AWS Exception / Condition | Sentinel SOC Status Code | Error Message / Explanation | Remediation Guidance |
|---|:---:|---|---|
| `AccessDeniedException` on `AssumeRole` | `403 Forbidden` | `Failed to assume IAM role in target account` | Verify that the target IAM role grants trust to the Sentinel account and that the Role ARN is correct. |
| `InvalidExternalId` | `403 Forbidden` | `External ID mismatch during AssumeRole` | Verify that `sts:ExternalId` in the trust policy matches the exact tenant External ID shown in Sentinel. |
| Missing Subsystem Permissions (e.g. GuardDuty) | `200 OK` (Partial) | `Subsystem sync degraded: Access Denied` | Review IAM policy attachment; ensure `guardduty:Get*` is allowed. |
| Expired / Invalid Local Credentials | `503 Unavailable`| `Sentinel AWS integration host credentials expired` | Re-authenticate the hosting environment with AWS CLI or instance profile. |
| Disconnected Account | `200 OK` | `AWS account successfully disconnected` | Purges account registration and stops automated polling. |

---

## 5. Offline Zero-Cost Simulation Mode

Sentinel SOC provides complete offline simulated findings to enable testing without live AWS credentials:

- **1-Click Offline Loader:** Click **"Load Zero-Cost Fixtures"** on `/aws-security` or `POST /api/v1/aws/fixtures/load-all-fixtures`.
- **High-Fidelity Sample Findings:**
  1. *GuardDuty:* `CryptoCurrency:EC2/BitcoinTool.B!DNS` (Critical)
  2. *GuardDuty:* `Trojan:EC2/DNSDataExfiltration` (High)
  3. *IAM Posture:* `RootAccountMFAAbsent` (Critical)
  4. *S3 Posture:* `PublicReadAclEnabled` on storage buckets (High)
  5. *VPC Flow:* Anomalous SSH outbound connection burst (Medium)
- **Zero Cost Guarantee:** Offline simulation loads data directly into the local database without making outbound AWS API calls.
