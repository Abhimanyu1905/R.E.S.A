---
title: Support Agent Internal Tooling and Systems FAQ
doc_type: faq
min_role_level: 2
---

## How do I resolve VPN connection failures when accessing internal tools?
All internal support platforms require an active encrypted connection through Cisco AnyConnect. If you encounter error message "Gateway Unreachable":
1. Verify connection to primary gateway address `vpn.resasupport.com:8443`.
2. Ensure your local network allows outbound traffic on UDP port 443 and TCP port 10443.
3. If primary gateway is down, switch connection profile to backup node `vpn-backup.resasupport.com:8443`.
4. If errors persist beyond 10 minutes, open a high-priority ticket with Enterprise IT.

## What should I do if Horizon Portal freezes or crashes during customer lookup?
If Horizon Portal displays a white screen or perpetual loading spinner:
- Execute a hard browser cache refresh by pressing `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (macOS).
- Navigate to Developer Tools > Application > Storage and click "Clear Site Data" to flush corrupted IndexedDB local state (`horizon_local_cache`).
- If the primary web cluster is unresponsive, access secondary mirror node `https://horizon-node2.internal.resasupport.com`.

## What causes Softphone WebRTC Error Code ERR-SIP-408 and how is it fixed?
Error Code `ERR-SIP-408` indicates a SIP registration handshake timeout between your browser audio endpoint and our Twilio voice infrastructure:
- Verify that your corporate headset is configured as the default audio communications device in operating system sound settings.
- Confirm local firewall permits bidirectional WebRTC traffic across UDP ports 16384 through 32767.
- Toggle your softphone status from "Offline" to "Available" to re-trigger a fresh TLS handshake.

## How do I submit an IT emergency ticket during an active service outage?
For system-wide outages affecting more than 3 agents simultaneously:
- Access the Emergency Helpdesk Portal at `helpdesk.internal.resasupport.com`.
- Select Incident Priority `Severity-1 (Critical Business Impact)`.
- The on-call Site Reliability Engineering (SRE) team is bound by an SLA response target of 15 minutes.
- SRE outage updates are broadcast live in corporate Slack channel `#support-system-status`.

For hardware diagnostic tracking under standard MARKER-L2-0013, remote agent workstation firmware builds must bear build hash build-v4-9912-prod.
