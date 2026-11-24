import ipaddress
from typing import Dict, Any, Optional

def classify_ip(ip_str: str) -> Dict[str, Any]:
    """
    Parses and strictly classifies an IP address into:
    Public, Private, Loopback, Link-local, Reserved, or Invalid.
    """
    if not ip_str or not isinstance(ip_str, str):
        return {
            "ip": ip_str,
            "version": 0,
            "classification": "Invalid",
            "is_valid": False,
            "is_public": False,
            "is_private": False,
            "is_loopback": False
        }
    
    cleaned = ip_str.strip().split("%")[0]  # Strip IPv6 zone ID if present
    try:
        obj = ipaddress.ip_address(cleaned)
    except ValueError:
        return {
            "ip": ip_str,
            "version": 0,
            "classification": "Invalid",
            "is_valid": False,
            "is_public": False,
            "is_private": False,
            "is_loopback": False
        }
    
    classification = "Public"
    if obj.is_loopback:
        classification = "Loopback"
    elif obj.is_link_local:
        classification = "Link-local"
    elif obj.is_private:
        classification = "Private"
    elif obj.is_reserved or obj.is_unspecified or obj.is_multicast:
        classification = "Reserved"
    else:
        classification = "Public"
        
    return {
        "ip": str(obj),
        "version": obj.version,
        "classification": classification,
        "is_valid": True,
        "is_public": classification == "Public",
        "is_private": classification == "Private",
        "is_loopback": classification == "Loopback",
        "is_link_local": classification == "Link-local"
    }

def get_approximate_geoip(ip_str: str) -> Dict[str, Any]:
    """
    Provides approximate country, ASN, and reputation for an IP address.
    Free offline deterministic mapping for known test/demo addresses,
    with safe graceful fallback.
    """
    classification_info = classify_ip(ip_str)
    if not classification_info["is_valid"] or not classification_info["is_public"]:
        return {
            "country": "Local / Private Network",
            "country_code": "LOCAL",
            "city": "Internal",
            "asn": "AS0 (Private)",
            "as_org": "Internal Network",
            "reputation_score": 0,
            "threat_level": "Benign"
        }
    
    # Known test / demo public ranges for learning and demonstration
    sample_known = {
        "8.8.8.8": {"country": "United States", "country_code": "US", "city": "Mountain View", "asn": "AS15169", "as_org": "Google LLC", "reputation_score": 0, "threat_level": "Benign"},
        "1.1.1.1": {"country": "Australia", "country_code": "AU", "city": "Sydney", "asn": "AS13335", "as_org": "Cloudflare, Inc.", "reputation_score": 0, "threat_level": "Benign"},
        "185.220.101.5": {"country": "Germany", "country_code": "DE", "city": "Frankfurt", "asn": "AS205100", "as_org": "Tor Exit Node", "reputation_score": 92, "threat_level": "Malicious"},
        "45.33.32.156": {"country": "United States", "country_code": "US", "city": "Dallas", "asn": "AS63949", "as_org": "Linode LLC", "reputation_score": 75, "threat_level": "Suspicious"},
        "194.26.29.112": {"country": "Russia", "country_code": "RU", "city": "Moscow", "asn": "AS44050", "as_org": "Known Scanner Feed", "reputation_score": 95, "threat_level": "Malicious"},
        "198.51.100.24": {"country": "Documentation Net", "country_code": "DOC", "city": "Lab Simulation", "asn": "AS64500", "as_org": "Sentinel Lab Range", "reputation_score": 85, "threat_level": "Suspicious"},
    }
    
    if ip_str in sample_known:
        return sample_known[ip_str]
        
    # Default public fallback
    return {
        "country": "Global Internet",
        "country_code": "GL",
        "city": "Public Routing",
        "asn": "AS-PUBLIC",
        "as_org": "Public Autonomous System",
        "reputation_score": 10,
        "threat_level": "Benign"
    }

def is_ip_in_network(ip_str: str, cidr_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        net = ipaddress.ip_network(cidr_str.strip(), strict=False)
        return ip in net
    except Exception:
        return False
