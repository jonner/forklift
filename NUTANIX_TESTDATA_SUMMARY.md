# Nutanix Test Data - Quick Reference

This document provides a quick reference for the mock Nutanix test data created for forklift development.

## 📊 Test Environment Overview

Your test environment simulates a realistic Nutanix deployment:

```
Production Cluster (prod-cluster-01)
├── 2 AHV Hosts (32 cores, 256 GB each)
├── 4 Production VMs (RHEL, Windows)
├── 3 Networks (Management, VLAN-100, VLAN-200)
└── 2 Storage Containers (8TB default, 2TB SSD)

Development Cluster (dev-cluster-01)
├── 1 AHV Host (16 cores, 128 GB)
├── 2 Dev VMs (Ubuntu, test VM)
├── 1 Network (Dev-Network)
└── 1 Storage Container (4TB default)
```

**Total Resources**:
- 2 Clusters
- 3 Hosts (80 total cores, 640 GB RAM)
- 6 VMs (5 powered on, 1 powered off)
- 4 Networks
- 3 Storage Containers
- 4 Images

## 🎯 Migration Test Scenarios Covered

The test data includes VMs that cover all major migration scenarios:

| Scenario | VM Example | Notes |
|----------|------------|-------|
| Standard UEFI Linux | `web-server-rhel8` | Single disk, single NIC, most common |
| Multi-disk VM | `db-server-rhel9` | OS disk + data disk on SSD storage |
| Multi-NIC VM | `win2022-app-server` | Dual NICs on different VLANs |
| Windows VM | `win2022-app-server` | Q35 machine type, Windows Server 2022 |
| BIOS/Legacy boot | `ubuntu-test-vm` | Legacy boot mode support |
| UEFI Secure Boot | `secure-boot-vm` | Secure boot validation |
| Powered off VM | `powered-off-vm` | Cold migration scenario |
| Nutanix Guest Tools | All VMs | NGT → qemu-guest-agent transition |
| Categories/Tags | Most VMs | Tag migration to K8s labels |

## 📁 Generated Files

All test data is located in:
```
pkg/controller/provider/container/nutanix/testdata/
├── clusters_list.json          # 2 clusters
├── hosts_list.json             # 3 AHV hosts
├── vms_list.json               # 6 VMs with various configs
├── vm_detail_example.json      # Full VM detail structure
├── subnets_list.json           # 4 networks
├── storage_containers_list.json # 3 storage containers
├── images_list.json            # 4 images (OS + ISOs)
└── README.md                   # Detailed documentation
```

## 🚀 Using the Test Data

### Analyze Test Data
```bash
cd /home/jjongsma/work/forklift
python3 analyze_testdata.py
```

### In Go Unit Tests
```go
import (
    "encoding/json"
    "os"
    "testing"
)

func TestNutanixVMParsing(t *testing.T) {
    // Load test data
    data, _ := os.ReadFile("testdata/vms_list.json")
    var response VMListResponse
    json.Unmarshal(data, &response)

    // Test your code
    assert.Equal(t, 6, len(response.Entities))

    // Find specific VM
    webServer := findVM(response.Entities, "web-server-rhel8")
    assert.Equal(t, "ON", webServer.Spec.Resources.PowerState)
    assert.Equal(t, 4, webServer.Spec.Resources.NumSockets *
                       webServer.Spec.Resources.NumVcpusPerSocket)
}
```

### Mock HTTP Server
```go
func mockNutanixAPI() *httptest.Server {
    return httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")

        switch r.URL.Path {
        case "/api/nutanix/v3/vms/list":
            data, _ := os.ReadFile("testdata/vms_list.json")
            w.Write(data)
        case "/api/nutanix/v3/clusters/list":
            data, _ := os.ReadFile("testdata/clusters_list.json")
            w.Write(data)
        // Add other endpoints...
        }
    }))
}
```

## 🔑 Quick UUID Reference

For writing tests that reference specific resources:

### Clusters
- `0005e123-4567-89ab-cdef-000000000001` → prod-cluster-01
- `0005e123-4567-89ab-cdef-000000000002` → dev-cluster-01

### Hosts
- `0005f123-4567-89ab-cdef-000000000101` → ahv-node-01 (prod)
- `0005f123-4567-89ab-cdef-000000000102` → ahv-node-02 (prod)
- `0005f123-4567-89ab-cdef-000000000201` → ahv-dev-node-01 (dev)

### VMs
- `vm-0005a123-4567-89ab-cdef-000000000001` → web-server-rhel8
- `vm-0005a123-4567-89ab-cdef-000000000002` → db-server-rhel9
- `vm-0005a123-4567-89ab-cdef-000000000003` → win2022-app-server
- `vm-0005a123-4567-89ab-cdef-000000000004` → ubuntu-test-vm
- `vm-0005a123-4567-89ab-cdef-000000000005` → powered-off-vm
- `vm-0005a123-4567-89ab-cdef-000000000006` → secure-boot-vm

### Networks
- `0005d123-4567-89ab-cdef-000000000001` → Production-VLAN-100 (192.168.100.0/24)
- `0005d123-4567-89ab-cdef-000000000002` → Production-VLAN-200 (192.168.200.0/24)
- `0005d123-4567-89ab-cdef-000000000003` → Dev-Network (10.0.10.0/24)
- `0005d123-4567-89ab-cdef-000000000004` → Management-Network (10.10.1.0/24)

### Storage
- `0005c123-4567-89ab-cdef-000000000001` → default-container-prod
- `0005c123-4567-89ab-cdef-000000000002` → ssd-container-prod
- `0005c123-4567-89ab-cdef-000000000003` → default-container-dev

## 💡 Key Observations for Implementation

### 1. Boot Configuration
VMs support three boot types:
- `LEGACY` - Traditional BIOS (ubuntu-test-vm)
- `UEFI` - Modern UEFI (most VMs)
- `SECURE_BOOT` - UEFI with Secure Boot (secure-boot-vm)

All should be preserved during migration to KubeVirt.

### 2. Machine Types
- `PC` - Standard machine type (most VMs)
- `Q35` - Modern chipset (win2022-app-server)

Map to KubeVirt's `pc` and `q35` machine types.

### 3. Disk Configuration
- Disks use SCSI adapter by default
- Storage containers referenced by UUID
- Disk sizes in both MiB and bytes (use bytes for accuracy)
- `flash_mode` indicates SSD/flash storage

### 4. Network Configuration
- NICs use VIRTIO model (best performance)
- Subnet references for network mapping
- IP addresses from DHCP or static assignment
- MAC addresses should be preserved if possible

### 5. Nutanix Guest Tools
- Most VMs have NGT installed
- Version tracking available
- Should guide migration to qemu-guest-agent

### 6. Categories (Tags)
- Key-value pairs: `Environment:Production`, `Application:WebServer`
- Should map to Kubernetes labels on migrated VMs

## 📝 Next Steps

1. **Review the data structure**: Examine the JSON files to understand Nutanix API responses
2. **Design Go structs**: Create models matching the JSON structure
3. **Write unit tests**: Use this test data for testing your implementation
4. **Implement collector**: Parse these responses into internal models
5. **Test end-to-end**: Use mock HTTP server with this data

## 🔗 Related Documentation

- **Detailed test data docs**: `pkg/controller/provider/container/nutanix/testdata/README.md`
- **API exploration guide**: `NUTANIX_API_EXPLORATION.md`
- **Implementation plan**: `.claude/plans/snuggly-floating-lightning.md`
- **Python exploration script**: `explore_nutanix.py`

## ✅ Validation

Run the analysis script to verify test data integrity:

```bash
python3 analyze_testdata.py
```

Expected output:
- ✅ 2 clusters loaded
- ✅ 3 hosts across clusters
- ✅ 6 VMs with various configs
- ✅ 4 networks/subnets
- ✅ 3 storage containers
- ✅ 4 images

All UUIDs are consistent and maintain referential integrity across resources.
