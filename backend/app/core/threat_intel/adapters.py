import socket
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.events import ThreatIntelCache, ThreatProviderStatus, ThreatIndicator

logger = logging.getLogger("sentinel.threat_intel")

# In-memory fast cache to minimize DB overhead for rapid lookups
_IN_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}

def get_normalized_indicator(
    indicator_value: str,
    indicator_type: str,
    provider: str,
    reputation: str,
    confidence: int,
    status: str,
    attribution: str,
    first_seen: Optional[datetime] = None,
    last_seen: Optional[datetime] = None,
    reference: Optional[str] = None,
    source_timestamp: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
    raw_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs a standardized, normalized threat indicator payload.
    """
    now = datetime.utcnow()
    return {
        "indicator_value": indicator_value,
        "indicator_type": indicator_type,
        "provider": provider,
        "reputation": reputation,  # Benign, Suspicious, Malicious, Unknown
        "confidence": confidence,  # 0 to 100
        "status": status,          # CONFIGURED, NOT CONFIGURED, SUCCESS, RATE_LIMITED, ERROR
        "attribution": attribution,
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "reference": reference,
        "source_timestamp": (source_timestamp or now).isoformat(),
        "expires_at": (expires_at or (now + timedelta(hours=settings.THREAT_INTEL_CACHE_TTL_HOURS))).isoformat(),
        "raw_details": raw_details or {}
    }

async def query_abuseipdb(ip_str: str) -> Dict[str, Any]:
    """
    AbuseIPDB adapter (Official Free Tier: 1,000 requests/day).
    Checks IP abuse confidence score and historical reporting volume.
    """
    provider_name = "AbuseIPDB"
    attribution = "Threat data provided by AbuseIPDB (https://www.abuseipdb.com)"
    reference = f"https://www.abuseipdb.com/check/{ip_str}"

    if not settings.ABUSEIPDB_API_KEY or settings.ABUSEIPDB_API_KEY.startswith("your-"):
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv4" if ":" not in ip_str else "IPv6",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="NOT CONFIGURED",
            attribution=attribution,
            reference=reference,
            raw_details={"message": "AbuseIPDB API key not configured in environment."}
        )

    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {
        "Key": settings.ABUSEIPDB_API_KEY,
        "Accept": "application/json"
    }
    params = {"ipAddress": ip_str, "maxAgeInDays": 90}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json().get("data", {})
                score = int(data.get("abuseConfidenceScore", 0))
                reports = int(data.get("totalReports", 0))

                reputation = "Benign"
                if score >= 50:
                    reputation = "Malicious"
                elif score > 15:
                    reputation = "Suspicious"

                last_rep = data.get("lastReportedAt")
                last_seen_dt = datetime.fromisoformat(last_rep.replace("Z", "+00:00")) if last_rep else None

                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation=reputation,
                    confidence=score,
                    status="SUCCESS",
                    attribution=attribution,
                    last_seen=last_seen_dt,
                    reference=reference,
                    raw_details={
                        "abuse_confidence_score": score,
                        "total_reports": reports,
                        "country_code": data.get("countryCode"),
                        "isp": data.get("isp"),
                        "domain": data.get("domain"),
                        "usage_type": data.get("usageType"),
                        "is_whitelisted": data.get("isWhitelisted", False)
                    }
                )
            elif res.status_code == 429:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation="Unknown",
                    confidence=0,
                    status="RATE_LIMITED",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"message": "AbuseIPDB daily free quota reached."}
                )
            else:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation="Unknown",
                    confidence=0,
                    status="ERROR",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"error_code": res.status_code, "detail": res.text}
                )
    except Exception as exc:
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv4" if ":" not in ip_str else "IPv6",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="ERROR",
            attribution=attribution,
            reference=reference,
            raw_details={"exception": str(exc)}
        )

async def query_greynoise(ip_str: str) -> Dict[str, Any]:
    """
    GreyNoise Community Adapter.
    Identifies benign internet scanners, search engines, and malicious actors.
    """
    provider_name = "GreyNoise"
    attribution = "Noise classification data provided by GreyNoise Community (https://greynoise.io)"
    reference = f"https://viz.greynoise.io/ip/{ip_str}"

    if not settings.GREYNOISE_API_KEY or settings.GREYNOISE_API_KEY.startswith("your-"):
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv4" if ":" not in ip_str else "IPv6",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="NOT CONFIGURED",
            attribution=attribution,
            reference=reference,
            raw_details={"message": "GreyNoise API key not configured in environment."}
        )

    url = f"https://api.greynoise.io/v3/community/{ip_str}"
    headers = {"key": settings.GREYNOISE_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                raw_class = data.get("classification", "unknown").lower()
                noise = data.get("noise", False)
                riot = data.get("riot", False)  # Rule It Out (Common business service)

                reputation = "Benign"
                confidence = 30
                if raw_class == "malicious":
                    reputation = "Malicious"
                    confidence = 90
                elif raw_class == "benign" or riot:
                    reputation = "Benign"
                    confidence = 80
                elif noise:
                    reputation = "Suspicious"
                    confidence = 65

                last_seen_str = data.get("last_seen")
                last_seen_dt = None
                if last_seen_str:
                    try:
                        last_seen_dt = datetime.strptime(last_seen_str, "%Y-%m-%d")
                    except Exception:
                        pass

                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation=reputation,
                    confidence=confidence,
                    status="SUCCESS",
                    attribution=attribution,
                    last_seen=last_seen_dt,
                    reference=reference,
                    raw_details={
                        "noise": noise,
                        "riot": riot,
                        "classification": raw_class,
                        "name": data.get("name", "Unknown actor"),
                        "link": data.get("link")
                    }
                )
            elif res.status_code == 429:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation="Unknown",
                    confidence=0,
                    status="RATE_LIMITED",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"message": "GreyNoise Community rate limit reached."}
                )
            elif res.status_code == 404:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation="Benign",
                    confidence=40,
                    status="SUCCESS",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"message": "IP address not observed scanning the internet (Not in GreyNoise catalog)."}
                )
            else:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type="IPv4" if ":" not in ip_str else "IPv6",
                    provider=provider_name,
                    reputation="Unknown",
                    confidence=0,
                    status="ERROR",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"error_code": res.status_code, "detail": res.text}
                )
    except Exception as exc:
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv4" if ":" not in ip_str else "IPv6",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="ERROR",
            attribution=attribution,
            reference=reference,
            raw_details={"exception": str(exc)}
        )

async def query_alienvault_otx(ip_str: str) -> Dict[str, Any]:
    """
    AlienVault OTX (Open Threat Exchange) Adapter.
    Pulls community threat pulses, malware tags, and adversary references.
    """
    provider_name = "AlienVault OTX"
    attribution = "Threat pulses provided by AT&T Cybersecurity AlienVault OTX (https://otx.alienvault.com)"
    reference = f"https://otx.alienvault.com/indicator/ip/{ip_str}"

    if not settings.ALIENVAULT_OTX_KEY or settings.ALIENVAULT_OTX_KEY.startswith("your-"):
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv4" if ":" not in ip_str else "IPv6",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="NOT CONFIGURED",
            attribution=attribution,
            reference=reference,
            raw_details={"message": "AlienVault OTX API key not configured in environment."}
        )

    ip_type = "IPv6" if ":" in ip_str else "IPv4"
    url = f"https://otx.alienvault.com/api/v1/indicators/{ip_type}/{ip_str}/general"
    headers = {"X-OTX-API-KEY": settings.ALIENVAULT_OTX_KEY}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                pulse_info = data.get("pulse_info", {})
                pulse_count = pulse_info.get("count", 0)
                pulses = pulse_info.get("pulses", [])

                reputation = "Benign"
                confidence = 20
                if pulse_count >= 3:
                    reputation = "Malicious"
                    confidence = min(95, 60 + pulse_count * 5)
                elif pulse_count > 0:
                    reputation = "Suspicious"
                    confidence = 50

                pulse_names = [p.get("name") for p in pulses[:5] if p.get("name")]
                tags = []
                for p in pulses[:5]:
                    tags.extend(p.get("tags", []))

                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type=ip_type,
                    provider=provider_name,
                    reputation=reputation,
                    confidence=confidence,
                    status="SUCCESS",
                    attribution=attribution,
                    reference=reference,
                    raw_details={
                        "pulse_count": pulse_count,
                        "top_pulses": pulse_names,
                        "tags": list(set(tags))[:10],
                        "asn": data.get("asn"),
                        "country": data.get("country_name")
                    }
                )
            elif res.status_code == 429:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type=ip_type,
                    provider=provider_name,
                    reputation="Unknown",
                    confidence=0,
                    status="RATE_LIMITED",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"message": "AlienVault OTX rate limit reached."}
                )
            else:
                return get_normalized_indicator(
                    indicator_value=ip_str,
                    indicator_type=ip_type,
                    provider=provider_name,
                    reputation="Unknown",
                    confidence=0,
                    status="ERROR",
                    attribution=attribution,
                    reference=reference,
                    raw_details={"error_code": res.status_code, "detail": res.text}
                )
    except Exception as exc:
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type=ip_type,
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="ERROR",
            attribution=attribution,
            reference=reference,
            raw_details={"exception": str(exc)}
        )

async def query_spamhaus(ip_str: str) -> Dict[str, Any]:
    """
    Spamhaus IP Reputation Adapter.
    Inspects Spamhaus ZEN / DROP blocklists for spam sources, botnets, and trojans.
    """
    provider_name = "Spamhaus"
    attribution = "Reputation data verified against Spamhaus Block Lists (https://www.spamhaus.org)"
    reference = f"https://check.spamhaus.org/query/ip/{ip_str}"

    # Only IPv4 is supported for standard reverse DNSBL queries
    if ":" in ip_str:
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv6",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="NOT CONFIGURED",
            attribution=attribution,
            reference=reference,
            raw_details={"message": "Spamhaus DNSBL query skipped for IPv6 without dedicated DQS key."}
        )

    # Perform standard reverse DNS query against zen.spamhaus.org
    try:
        parts = ip_str.split(".")
        reversed_ip = f"{parts[3]}.{parts[2]}.{parts[1]}.{parts[0]}"
        query_host = f"{reversed_ip}.zen.spamhaus.org"
        
        # Async DNS resolution using standard socket
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            addrinfo = await loop.run_in_executor(None, socket.gethostbyname, query_host)
            
            # Spamhaus response codes:
            # 127.0.0.2 = SBL (Spam)
            # 127.0.0.3 = SBL CSS
            # 127.0.0.4-7 = XBL (Exploits, Troj/Worms)
            # 127.0.0.10-11 = PBL (End-user IP ranges)
            reputation = "Suspicious"
            confidence = 60
            category = "Spam / Reputation Warning"

            if addrinfo in ["127.0.0.4", "127.0.0.5", "127.0.0.6", "127.0.0.7"]:
                reputation = "Malicious"
                confidence = 90
                category = "XBL: Confirmed Malware / Botnet Drone"
            elif addrinfo in ["127.0.0.2", "127.0.0.3"]:
                reputation = "Malicious"
                confidence = 85
                category = "SBL: Verified Spam Source"
            elif addrinfo in ["127.0.0.10", "127.0.0.11"]:
                reputation = "Benign"
                confidence = 40
                category = "PBL: Dynamic End-user IP (Unsuitable for MTA)"

            return get_normalized_indicator(
                indicator_value=ip_str,
                indicator_type="IPv4",
                provider=provider_name,
                reputation=reputation,
                confidence=confidence,
                status="SUCCESS",
                attribution=attribution,
                reference=reference,
                raw_details={"dnsbl_response": addrinfo, "category": category}
            )
        except socket.gaierror:
            # NXDOMAIN: Clean IP (not listed on Spamhaus)
            return get_normalized_indicator(
                indicator_value=ip_str,
                indicator_type="IPv4",
                provider=provider_name,
                reputation="Benign",
                confidence=80,
                status="SUCCESS",
                attribution=attribution,
                reference=reference,
                raw_details={"message": "Not listed on Spamhaus ZEN blocklists."}
            )
    except Exception as exc:
        return get_normalized_indicator(
            indicator_value=ip_str,
            indicator_type="IPv4",
            provider=provider_name,
            reputation="Unknown",
            confidence=0,
            status="ERROR",
            attribution=attribution,
            reference=reference,
            raw_details={"exception": str(exc)}
        )

async def enrich_ip_all_providers(ip_str: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Enriches an IP address across all 4 configured threat intelligence providers.
    Uses multi-tiered caching (in-memory + database) with automatic TTL.
    """
    now = datetime.utcnow()
    ip_clean = ip_str.strip()

    # 1. Check in-memory cache
    if ip_clean in _IN_MEMORY_CACHE:
        cached = _IN_MEMORY_CACHE[ip_clean]
        if cached.get("expires_at") and datetime.fromisoformat(cached["expires_at"]) > now:
            return cached

    # 2. Check Database Cache
    if db:
        db_cache = db.query(ThreatIntelCache).filter(
            ThreatIntelCache.indicator_value == ip_clean,
            ThreatIntelCache.expires_at > now
        ).first()
        if db_cache:
            try:
                cached_data = json.loads(db_cache.normalized_json)
                _IN_MEMORY_CACHE[ip_clean] = cached_data
                return cached_data
            except Exception:
                pass

    # 3. Query all providers asynchronously
    import asyncio
    abuse_task = query_abuseipdb(ip_clean)
    greynoise_task = query_greynoise(ip_clean)
    otx_task = query_alienvault_otx(ip_clean)
    spamhaus_task = query_spamhaus(ip_clean)

    results = await asyncio.gather(abuse_task, greynoise_task, otx_task, spamhaus_task, return_exceptions=True)

    def clean_res(res, provider):
        if isinstance(res, Exception):
            return get_normalized_indicator(
                indicator_value=ip_clean,
                indicator_type="IPv4" if ":" not in ip_clean else "IPv6",
                provider=provider,
                reputation="Unknown",
                confidence=0,
                status="ERROR",
                attribution=f"Data from {provider}",
                raw_details={"error": str(res)}
            )
        return res

    abuse_res = clean_res(results[0], "AbuseIPDB")
    greynoise_res = clean_res(results[1], "GreyNoise")
    otx_res = clean_res(results[2], "AlienVault OTX")
    spamhaus_res = clean_res(results[3], "Spamhaus")

    # Calculate aggregate verdict
    scores = [
        r["confidence"] for r in [abuse_res, greynoise_res, otx_res, spamhaus_res]
        if r["reputation"] in ["Malicious", "Suspicious"] and r["status"] == "SUCCESS"
    ]
    is_malicious = any(r["reputation"] == "Malicious" for r in [abuse_res, greynoise_res, otx_res, spamhaus_res])
    is_suspicious = any(r["reputation"] == "Suspicious" for r in [abuse_res, greynoise_res, otx_res, spamhaus_res])

    overall_reputation = "Benign"
    overall_confidence = 10
    if is_malicious:
        overall_reputation = "Malicious"
        overall_confidence = max(scores) if scores else 85
    elif is_suspicious:
        overall_reputation = "Suspicious"
        overall_confidence = max(scores) if scores else 55

    ttl_hours = getattr(settings, "THREAT_INTEL_CACHE_TTL_HOURS", 6)
    expires_at = now + timedelta(hours=ttl_hours)

    consolidated = {
        "ip_address": ip_clean,
        "overall_reputation": overall_reputation,
        "overall_confidence": overall_confidence,
        "cached": False,
        "expires_at": expires_at.isoformat(),
        "providers": {
            "abuseipdb": abuse_res,
            "greynoise": greynoise_res,
            "alienvault_otx": otx_res,
            "spamhaus": spamhaus_res
        }
    }

    # Store in memory cache
    _IN_MEMORY_CACHE[ip_clean] = consolidated

    # Store in DB cache if DB session is available
    if db:
        try:
            existing_cache = db.query(ThreatIntelCache).filter(ThreatIntelCache.indicator_value == ip_clean).first()
            if existing_cache:
                existing_cache.normalized_json = json.dumps(consolidated)
                existing_cache.reputation = overall_reputation
                existing_cache.confidence = overall_confidence
                existing_cache.expires_at = expires_at
            else:
                new_cache = ThreatIntelCache(
                    indicator_value=ip_clean,
                    indicator_type="IPv4" if ":" not in ip_clean else "IPv6",
                    normalized_json=json.dumps(consolidated),
                    reputation=overall_reputation,
                    confidence=overall_confidence,
                    expires_at=expires_at
                )
                db.add(new_cache)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to commit threat intel cache for {ip_clean}: {e}")
            db.rollback()

    return consolidated

def get_threat_provider_health(db: Session) -> List[Dict[str, Any]]:
    """
    Returns the real-time configuration, quota, and operational status of all 4 threat intelligence providers.
    """
    providers_info = [
        {
            "provider_name": "AbuseIPDB",
            "is_configured": bool(settings.ABUSEIPDB_API_KEY and not settings.ABUSEIPDB_API_KEY.startswith("your-")),
            "daily_limit": 1000,
            "api_endpoint": "https://api.abuseipdb.com/api/v2/check",
            "attribution": "AbuseIPDB IP Verification Engine (https://www.abuseipdb.com)"
        },
        {
            "provider_name": "GreyNoise",
            "is_configured": bool(settings.GREYNOISE_API_KEY and not settings.GREYNOISE_API_KEY.startswith("your-")),
            "daily_limit": 500,
            "api_endpoint": "https://api.greynoise.io/v3/community",
            "attribution": "GreyNoise Intelligence Community (https://greynoise.io)"
        },
        {
            "provider_name": "AlienVault OTX",
            "is_configured": bool(settings.ALIENVAULT_OTX_KEY and not settings.ALIENVAULT_OTX_KEY.startswith("your-")),
            "daily_limit": 10000,
            "api_endpoint": "https://otx.alienvault.com/api/v1",
            "attribution": "AT&T Cybersecurity AlienVault OTX (https://otx.alienvault.com)"
        },
        {
            "provider_name": "Spamhaus",
            "is_configured": True,  # Standard DNSBL is publicly checkable
            "daily_limit": 5000,
            "api_endpoint": "zen.spamhaus.org (DNSBL)",
            "attribution": "The Spamhaus Project (https://www.spamhaus.org)"
        }
    ]

    results = []
    for p in providers_info:
        status_val = "CONFIGURED" if p["is_configured"] else "NOT CONFIGURED"
        db_status = db.query(ThreatProviderStatus).filter(ThreatProviderStatus.provider_name == p["provider_name"]).first()
        if db_status:
            requests_today = db_status.requests_today
            last_sync = db_status.last_sync_at
        else:
            requests_today = 0
            last_sync = None

        results.append({
            "provider_name": p["provider_name"],
            "status": status_val,
            "api_endpoint": p["api_endpoint"],
            "requests_today": requests_today,
            "daily_limit": p["daily_limit"],
            "last_sync_at": last_sync.isoformat() if last_sync else None,
            "attribution": p["attribution"]
        })

    return results
