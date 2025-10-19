# How to Clean Up Your Current VM

You have a working but messy VM. Here's how to clean it up without starting over.

## 🎯 Quick Clean-Up (10 minutes)

### Option A: In-Place Cleanup (Recommended)

```bash
# In the VM:
cd ~/netemulator

# 1. Stop current services
sudo pkill -f "python3 -m netemulator.control.api"
sudo wg-quick down wg0 2>/dev/null || true
sudo mn -c

# 2. Pull latest scripts
git pull

# 3. Run complete setup
sudo ./scripts/setup_complete_system.sh

# 4. Deploy topology
curl -X POST http://localhost:8080/api/v1/topologies \
  -H "Content-Type: text/plain" \
  --data-binary @examples/dual_isp_topology.yaml

# 5. Connect Mininet
sudo ./scripts/connect_mininet_to_host.sh

# 6. Re-onboard monitoring point
sudo ./scripts/onboard_mp.sh appneta-mac-01
```

Then on your Mac, reconnect WireGuard with the new config.

### Option B: Nuclear Reset (30 minutes)

```bash
# On your Mac:
multipass stop netemulator
multipass delete netemulator
multipass purge

# Then follow CLEAN_SETUP.md from the beginning
```

## 📋 What Gets Fixed

**Before (messy state):**
- ❌ API running manually in background
- ❌ Manual iptables rules
- ❌ Manual bridge IP assignment
- ❌ No systemd service
- ❌ Hard to restart/reproduce

**After (clean state):**
- ✅ API managed by systemd
- ✅ Automatic forwarding rules
- ✅ Scripted bridge setup
- ✅ Easy service management
- ✅ Fully reproducible

## 🧪 Test the Clean State

After cleanup, verify:

```bash
# Check systemd service
sudo systemctl status netemulator-api

# Check API
curl http://localhost:8080/api/v1/health

# Check WireGuard
sudo wg show

# Check Mininet connectivity
ping -c 2 10.0.0.1

# From your Mac
ping 10.100.0.1
ping 10.0.0.1
```

## 💾 Save Your Current Work

Before cleaning up, save anything important:

```bash
# In the VM:
# Export current topologies
curl http://localhost:8080/api/v1/topologies > ~/current_state.json

# Save WireGuard configs
cp /etc/wireguard/wg0.conf ~/wg0.conf.backup

# Save any custom topologies
cp examples/*.yaml ~/custom_topologies/
```

---

**Recommendation:** Do Option A (in-place cleanup) - it's faster and keeps your work!

