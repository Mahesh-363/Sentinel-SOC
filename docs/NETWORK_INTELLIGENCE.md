# SENTINEL SOC — Network Intelligence & Router Integration Guide

## 1. Overview & Observation Architecture

The Sentinel SOC Network Intelligence module provides comprehensive visibility into local networks, subnets, physical/virtual devices, and network infrastructure topology.

### Crucial Security Principles:
1. **Truth in Telemetry & Grounding:**
   - Sentinel SOC explicitly distinguishes **Inventory Discovery** (knowing which IP/MAC endpoints exist on a subnet) from **Packet-Level Inspection** (deep packet inspection or full traffic flow visibility).
   - In the Network Topology graph, edges are strictly classified as either:
     - **OBSERVED:** Direct physical/logical connection verified by ARP table mapping, switch port binding, or active agent interface telemetry.
     - **INFERRED:** Deduced through subnet CIDR co-location, default gateway routing paths, or ICMP echo responsiveness.
2. **Authorized Monitoring Only:**
   - Sentinel SOC monitors only explicitly registered subnets and authorized observation points.
   - It **never** conducts unauthorized promiscuous packet sniffing or aggressive port scanning across external networks.
3. **Open-Source & Free-Tier First:**
   - Native integration with open-source firewall/router platforms: **pfSense Community Edition**, **OPNsense**, **OpenWrt**, and self-hosted **Ubiquiti UniFi Controllers**.

---

## 2. Router & Gateway Integration Framework

Sentinel SOC features an extensible adapter framework (`backend/app/models/network.py` and `/api/v1/network/integrations`) supporting bi-directional metadata synchronization with network gateways:

| Gateway Platform | Integration Protocol | Auth Mechanism | Discovered Telemetry |
| :--- | :--- | :--- | :--- |
| **pfSense CE** | XML-RPC / FauxAPI REST | API Key & Secret | DHCP leases, ARP table, WAN public IP, interface traffic counters |
| **OPNsense** | Core REST API (`/api/dhcpv4/...`) | API Key & Secret | Active DHCP allocations, Unbound DNS cache, interface status |
| **OpenWrt** | LuCI RPC / ubus JSON-RPC | Token / sysauth | Connected Wi-Fi stations (`iwinfo`), DHCP leases (`luci.rpc.uci`), arp-scan |
| **UniFi Controller**| Self-Hosted UniFi Network REST API | Session Cookie / API Token | Device adoption status, switch port mapping, client connection speeds, VLANs |

### Router Integration Lifecycle:
1. **Registration:** Admin configures the integration with target hostname/IP, router type, and non-privileged credentials.
2. **Verification & Ping:** Sentinel issues a read-only health check to ensure API responsiveness without disruptive changes.
3. **Metadata Synchronization (`/integrations/{id}/sync`):**
   - Retrieves active DHCP leases.
   - Resolves MAC-to-IP bindings.
   - Normalizes hardware manufacturer via OUI database lookup.
   - Updates `last_seen` timestamps on `NetworkDevice` entries.
   - Creates `OBSERVED` topology links between discovered endpoints and the gateway.

---

## 3. Coverage & Posture Metrics

Sentinel SOC tracks two primary infrastructure visibility metrics via `/api/v1/network/coverage`:

$$\text{Subnet Coverage} = \frac{\text{Configured / Monitored Subnets}}{\text{Total Discovered CIDR Ranges}} \times 100\%$$

$$\text{Agent Sensor Coverage} = \frac{\text{Discovered Assets with Active Sentinel Sensor}}{\text{Total Known Assets}} \times 100\%$$

- **Full Coverage:** Asset is running an enrolled Sentinel agent with live telemetry.
- **Partial Coverage:** Asset is visible via router DHCP/ARP lease tables but has no host-level telemetry agent.
- **Rogue / Unmonitored Asset Alerting:** Triggered when an unrecognized MAC/IP appears on a monitored subnet without prior administrative authorization.

---

## 4. Network Topology Graph Schema

The `/api/v1/network/topology` endpoint provides graph-structured nodes and edges formatted for interactive visualization:

```json
{
  "nodes": [
    {
      "id": "gateway-1",
      "label": "Gateway / Router",
      "ip": "192.168.1.1",
      "device_type": "Gateway",
      "is_gateway": true,
      "health_status": "Healthy"
    },
    {
      "id": "asset-10",
      "label": "Workstation-Finance",
      "ip": "192.168.1.45",
      "device_type": "Workstation",
      "is_gateway": false,
      "health_status": "Warning"
    }
  ],
  "links": [
    {
      "source": "192.168.1.45",
      "target": "192.168.1.1",
      "link_type": "OBSERVED",
      "discovered_via": "Router DHCP Sync",
      "confidence": "High",
      "verified_at": "2026-11-16T12:00:00Z"
    }
  ]
}
```

- **Green Solid Edge:** OBSERVED connection verified by router interface or switch MAC table.
- **Blue Dashed Edge:** INFERRED relationship derived from network CIDR co-location.
