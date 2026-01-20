# Nutanix API Exploration Guide for Forklift Integration

## Overview

This guide helps you explore the Nutanix Prism v3 REST API to understand the data structures and endpoints needed for forklift integration.

**API Version**: v3 (REST)
**Base URL**: `https://<prism-central-or-element>:9440/api/nutanix/v3/`
**Authentication**: Basic Auth (username:password)

---

## Setting Up a Test Environment

### Option 1: Nutanix Community Edition (Recommended for Development)

**Pros**:
- Full-featured Nutanix cluster
- Free for non-production use
- Persistent environment

**Requirements**:
- Nested virtualization support (KVM, ESXi, or Hyper-V)
- 32GB RAM minimum (48GB recommended)
- 200GB disk space
- Download from: https://www.nutanix.com/products/community-edition

**Setup Steps**:
1. Register for Nutanix account at https://portal.nutanix.com
2. Download Nutanix CE installer
3. Create VM with:
   - 8 vCPUs
   - 32GB RAM
   - 200GB+ disk (thin provisioned)
   - 2 NICs (one for management, one for VM network)
4. Boot from CE ISO
5. Follow installation wizard
6. Access Prism Element at `https://<node-ip>:9440`

### Option 2: Nutanix Test Drive

**Pros**:
- No setup required
- Instant access
- Real Nutanix environment

**Cons**:
- Limited to 8 hours
- Cannot save work
- Pre-configured environment

**Access**: https://www.nutanix.com/test-drive
Select "Prism Central" lab for v3 API access.

### Option 3: Nutanix API Documentation Explorer

**Use without environment**:
- API Reference: https://www.nutanix.dev/api-reference/prism-central/
- Interactive explorer: Built into Prism at `https://<prism>:9440/api/nutanix/v3/api_explorer/`

---

## Nutanix API Fundamentals

### Authentication

Nutanix v3 API uses HTTP Basic Authentication:

```bash
# Set credentials
PRISM_HOST="prism-central.example.com"
USERNAME="admin"
PASSWORD="your-password"

# Test authentication
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"cluster"}' \
  https://$PRISM_HOST:9440/api/nutanix/v3/clusters/list
```

**Note**: `-k` skips SSL verification (for self-signed certs in test environments)

### API Structure

Nutanix v3 API follows RESTful patterns with some unique characteristics:

1. **List Operations**: Use POST (not GET) with a filter body
2. **Pagination**: Uses `offset` and `length` parameters
3. **Resource Types**: Identified by `kind` field
4. **UUIDs**: All resources have a `metadata.uuid` field

### Common Request Pattern

Most list operations follow this structure:

```json
POST /api/nutanix/v3/{resource}/list
{
  "kind": "{resource}",
  "offset": 0,
  "length": 100,
  "filter": "optional_filter_expression"
}
```

---

## Key API Endpoints for Forklift

### 1. Cluster Information

**Endpoint**: `POST /api/nutanix/v3/clusters/list`

**Purpose**: Get Nutanix cluster metadata (equivalent to vSphere Datacenter/Cluster)

**Request**:
```bash
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "cluster",
    "offset": 0,
    "length": 100
  }' \
  https://$PRISM_HOST:9440/api/nutanix/v3/clusters/list
```

**Key Response Fields**:
```json
{
  "entities": [
    {
      "metadata": {
        "uuid": "00000000-0000-0000-0000-000000000000",
        "name": "cluster-name"
      },
      "spec": {
        "name": "cluster-name",
        "resources": {
          "config": {
            "service_list": ["AOS"],
            "timezone": "America/Los_Angeles"
          }
        }
      },
      "status": {
        "resources": {
          "nodes": {
            "hypervisor_server_list": [
              {
                "ip": "10.0.0.1",
                "version": "20240802.100"
              }
            ]
          },
          "config": {
            "cluster_arch": "X86_64",
            "build": {
              "version": "6.8.2"
            }
          }
        }
      }
    }
  ]
}
```

**Fields Needed for Forklift**:
- `metadata.uuid` - Cluster UUID
- `metadata.name` - Cluster name
- `status.resources.nodes.hypervisor_server_list` - Host references
- `status.resources.config.build.version` - AOS version
- `status.resources.config.timezone` - Timezone

### 2. Host Information

**Endpoint**: `POST /api/nutanix/v3/hosts/list`

**Purpose**: Get AHV hypervisor node information

**Request**:
```bash
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "host",
    "offset": 0,
    "length": 100
  }' \
  https://$PRISM_HOST:9440/api/nutanix/v3/hosts/list
```

**Key Response Fields**:
```json
{
  "entities": [
    {
      "metadata": {
        "uuid": "host-uuid",
        "name": "host-name"
      },
      "spec": {
        "name": "host-name",
        "cluster_reference": {
          "kind": "cluster",
          "uuid": "cluster-uuid"
        }
      },
      "status": {
        "resources": {
          "serial_number": "1234567890",
          "hypervisor": {
            "hypervisor_full_name": "AHV 20240802.100",
            "num_vms": 5
          },
          "cpu_model": "Intel Xeon",
          "cpu_capacity_hz": 2400000000,
          "num_cpu_sockets": 2,
          "num_cpu_cores": 16,
          "memory_capacity_mib": 131072,
          "host_type": "HYPER_CONVERGED"
        }
      }
    }
  ]
}
```

**Fields Needed for Forklift**:
- `metadata.uuid` - Host UUID
- `metadata.name` - Host name
- `spec.cluster_reference.uuid` - Parent cluster
- `status.resources.serial_number` - Serial number
- `status.resources.num_cpu_sockets` - CPU sockets
- `status.resources.num_cpu_cores` - CPU cores
- `status.resources.memory_capacity_mib` - Memory in MiB

### 3. Virtual Machines

**Endpoint**: `POST /api/nutanix/v3/vms/list`

**Purpose**: List all VMs (main resource for migration)

**Request**:
```bash
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "vm",
    "offset": 0,
    "length": 100,
    "filter": "power_state==ON"
  }' \
  https://$PRISM_HOST:9440/api/nutanix/v3/vms/list
```

**Get Single VM**:
```bash
VM_UUID="vm-uuid-here"
curl -k -u "$USERNAME:$PASSWORD" \
  -X GET \
  https://$PRISM_HOST:9440/api/nutanix/v3/vms/$VM_UUID
```

**Key Response Fields**:
```json
{
  "metadata": {
    "uuid": "vm-uuid",
    "name": "vm-name"
  },
  "spec": {
    "name": "vm-name",
    "description": "VM description",
    "cluster_reference": {
      "kind": "cluster",
      "uuid": "cluster-uuid"
    },
    "resources": {
      "power_state": "ON",
      "num_sockets": 2,
      "num_vcpus_per_socket": 2,
      "memory_size_mib": 4096,
      "boot_config": {
        "boot_type": "UEFI",
        "boot_device_order_list": ["DISK", "CDROM", "NETWORK"]
      },
      "machine_type": "PC",
      "nic_list": [
        {
          "uuid": "nic-uuid",
          "nic_type": "NORMAL_NIC",
          "mac_address": "50:6b:8d:12:34:56",
          "model": "VIRTIO",
          "subnet_reference": {
            "kind": "subnet",
            "uuid": "subnet-uuid"
          },
          "ip_endpoint_list": [
            {
              "ip": "10.0.0.100",
              "type": "ASSIGNED"
            }
          ]
        }
      ],
      "disk_list": [
        {
          "uuid": "disk-uuid",
          "device_properties": {
            "device_type": "DISK",
            "disk_address": {
              "device_index": 0,
              "adapter_type": "SCSI"
            }
          },
          "disk_size_mib": 102400,
          "storage_config": {
            "storage_container_reference": {
              "kind": "storage_container",
              "uuid": "container-uuid"
            }
          }
        }
      ],
      "guest_tools": {
        "nutanix_guest_tools": {
          "enabled": true,
          "iso_mount_state": "MOUNTED",
          "version": "3.2.0"
        }
      },
      "guest_customization": {
        "is_overridable": false
      }
    }
  },
  "status": {
    "resources": {
      "host_reference": {
        "kind": "host",
        "uuid": "host-uuid"
      },
      "hypervisor_type": "kKvm"
    }
  }
}
```

**Critical Fields for Migration**:
- `metadata.uuid` - VM UUID
- `metadata.name` - VM name
- `spec.resources.power_state` - Power state (ON/OFF)
- `spec.resources.num_sockets` - CPU sockets
- `spec.resources.num_vcpus_per_socket` - vCPUs per socket
- `spec.resources.memory_size_mib` - Memory in MiB
- `spec.resources.boot_config` - Boot configuration
- `spec.resources.nic_list` - Network interfaces
- `spec.resources.disk_list` - Virtual disks
- `spec.resources.guest_tools` - Nutanix Guest Tools status
- `status.resources.host_reference` - Current host

### 4. Networks/Subnets

**Endpoint**: `POST /api/nutanix/v3/subnets/list`

**Purpose**: Get network/VLAN information for network mapping

**Request**:
```bash
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "subnet",
    "offset": 0,
    "length": 100
  }' \
  https://$PRISM_HOST:9440/api/nutanix/v3/subnets/list
```

**Key Response Fields**:
```json
{
  "metadata": {
    "uuid": "subnet-uuid",
    "name": "VM Network"
  },
  "spec": {
    "name": "VM Network",
    "cluster_reference": {
      "kind": "cluster",
      "uuid": "cluster-uuid"
    },
    "resources": {
      "vlan_id": 100,
      "subnet_type": "VLAN",
      "ip_config": {
        "subnet_ip": "10.0.0.0",
        "prefix_length": 24,
        "default_gateway_ip": "10.0.0.1",
        "pool_list": [
          {
            "range": "10.0.0.100 10.0.0.200"
          }
        ],
        "dhcp_options": {
          "domain_name_server_list": ["8.8.8.8", "8.8.4.4"]
        }
      }
    }
  }
}
```

**Fields Needed for Forklift**:
- `metadata.uuid` - Network UUID
- `metadata.name` - Network name
- `spec.resources.vlan_id` - VLAN ID
- `spec.resources.subnet_type` - Type (VLAN/OVERLAY)
- `spec.resources.ip_config` - IP configuration

### 5. Storage Containers

**Endpoint**: `POST /api/nutanix/v3/storage_containers/list`

**Purpose**: Get storage container information for storage mapping

**Request**:
```bash
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "storage_container",
    "offset": 0,
    "length": 100
  }' \
  https://$PRISM_HOST:9440/api/nutanix/v3/storage_containers/list
```

**Key Response Fields**:
```json
{
  "metadata": {
    "uuid": "container-uuid",
    "name": "default-container"
  },
  "spec": {
    "name": "default-container",
    "cluster_reference": {
      "kind": "cluster",
      "uuid": "cluster-uuid"
    }
  },
  "status": {
    "resources": {
      "replication_factor": 2,
      "max_capacity_bytes": 1099511627776,
      "usage_stats": {
        "storage.user_usage_bytes": 536870912000
      },
      "compression_enabled": true,
      "dedup_enabled": false,
      "erasure_code": "off"
    }
  }
}
```

**Fields Needed for Forklift**:
- `metadata.uuid` - Container UUID
- `metadata.name` - Container name
- `status.resources.replication_factor` - RF
- `status.resources.max_capacity_bytes` - Capacity
- `status.resources.compression_enabled` - Compression

### 6. Images

**Endpoint**: `POST /api/nutanix/v3/images/list`

**Purpose**: Get disk images and ISOs

**Request**:
```bash
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "image",
    "offset": 0,
    "length": 100
  }' \
  https://$PRISM_HOST:9440/api/nutanix/v3/images/list
```

---

## API Exploration Script

Save this as `explore_nutanix_api.sh`:

```bash
#!/bin/bash

# Configuration
PRISM_HOST="${PRISM_HOST:-prism.local}"
USERNAME="${NUTANIX_USER:-admin}"
PASSWORD="${NUTANIX_PASSWORD}"
OUTPUT_DIR="./nutanix_api_responses"

if [ -z "$PASSWORD" ]; then
    echo "Error: Set NUTANIX_PASSWORD environment variable"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Exploring Nutanix API at $PRISM_HOST"
echo "Responses will be saved to $OUTPUT_DIR/"
echo ""

# Test connection
echo "1. Testing connection..."
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"cluster"}' \
  -o "$OUTPUT_DIR/clusters_list.json" \
  -w "HTTP Status: %{http_code}\n" \
  https://$PRISM_HOST:9440/api/nutanix/v3/clusters/list

# Get hosts
echo -e "\n2. Fetching hosts..."
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"host","offset":0,"length":100}' \
  -o "$OUTPUT_DIR/hosts_list.json" \
  -w "HTTP Status: %{http_code}\n" \
  https://$PRISM_HOST:9440/api/nutanix/v3/hosts/list

# Get VMs
echo -e "\n3. Fetching VMs..."
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"vm","offset":0,"length":100}' \
  -o "$OUTPUT_DIR/vms_list.json" \
  -w "HTTP Status: %{http_code}\n" \
  https://$PRISM_HOST:9440/api/nutanix/v3/vms/list

# Get networks/subnets
echo -e "\n4. Fetching subnets..."
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"subnet","offset":0,"length":100}' \
  -o "$OUTPUT_DIR/subnets_list.json" \
  -w "HTTP Status: %{http_code}\n" \
  https://$PRISM_HOST:9440/api/nutanix/v3/subnets/list

# Get storage containers
echo -e "\n5. Fetching storage containers..."
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"storage_container","offset":0,"length":100}' \
  -o "$OUTPUT_DIR/storage_containers_list.json" \
  -w "HTTP Status: %{http_code}\n" \
  https://$PRISM_HOST:9440/api/nutanix/v3/storage_containers/list

# Get images
echo -e "\n6. Fetching images..."
curl -k -u "$USERNAME:$PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"kind":"image","offset":0,"length":100}' \
  -o "$OUTPUT_DIR/images_list.json" \
  -w "HTTP Status: %{http_code}\n" \
  https://$PRISM_HOST:9440/api/nutanix/v3/images/list

echo -e "\n✓ API exploration complete!"
echo "Review responses in: $OUTPUT_DIR/"
echo ""
echo "Pretty-print with jq:"
echo "  cat $OUTPUT_DIR/vms_list.json | jq ."
```

**Usage**:
```bash
chmod +x explore_nutanix_api.sh
export NUTANIX_PASSWORD="your-password"
export PRISM_HOST="10.0.0.100"  # or prism.example.com
./explore_nutanix_api.sh
```

---

## Using the Nutanix API Explorer (Built-in)

If you have access to a Nutanix cluster:

1. Navigate to: `https://<prism>:9440/api/nutanix/v3/api_explorer/`
2. Authenticate with your credentials
3. Explore endpoints interactively:
   - `/clusters/list` - Cluster information
   - `/hosts/list` - Host information
   - `/vms/list` - Virtual machines
   - `/subnets/list` - Networks
   - `/storage_containers/list` - Storage
4. Try requests directly in browser
5. View example responses
6. Copy response JSON for test data

---

## Creating Test Data for Forklift Development

Even without a Nutanix environment, you can develop using mock data:

### 1. Use Official Documentation Examples

Nutanix API docs include example responses:
https://www.nutanix.dev/api-reference/prism-central/v3/

### 2. Create Minimal Test Fixtures

Create `pkg/controller/provider/container/nutanix/testdata/` with:

**clusters_response.json**:
```json
{
  "entities": [
    {
      "metadata": {
        "uuid": "00000000-0000-0000-0000-000000000001",
        "name": "test-cluster"
      },
      "spec": {
        "name": "test-cluster"
      },
      "status": {
        "resources": {
          "config": {
            "build": {
              "version": "6.8.2"
            }
          }
        }
      }
    }
  ]
}
```

**vms_response.json**:
```json
{
  "entities": [
    {
      "metadata": {
        "uuid": "vm-00000000-0000-0000-0000-000000000001",
        "name": "test-vm-1"
      },
      "spec": {
        "name": "test-vm-1",
        "cluster_reference": {
          "uuid": "00000000-0000-0000-0000-000000000001"
        },
        "resources": {
          "power_state": "ON",
          "num_sockets": 2,
          "num_vcpus_per_socket": 2,
          "memory_size_mib": 4096,
          "nic_list": [],
          "disk_list": [
            {
              "disk_size_mib": 102400,
              "device_properties": {
                "device_type": "DISK"
              }
            }
          ]
        }
      }
    }
  ]
}
```

### 3. Mock HTTP Server for Testing

Create a simple mock server using the test data:

```go
// In your test files
func mockNutanixServer() *httptest.Server {
    return httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.URL.Path == "/api/nutanix/v3/vms/list" {
            data, _ := os.ReadFile("testdata/vms_response.json")
            w.Write(data)
        }
        // ... handle other endpoints
    }))
}
```

---

## Next Steps

1. **Set up test environment** (choose CE or Test Drive)
2. **Run API exploration script** to get real responses
3. **Save responses** to `testdata/` for development
4. **Analyze response structures** to refine data models
5. **Start implementing** client.go based on actual API behavior

---

## Common Issues and Solutions

### SSL Certificate Errors

**Problem**: Self-signed certificates in test environments

**Solution**: Use `-k` flag with curl or configure Go client:
```go
client := &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{
            InsecureSkipVerify: true,
        },
    },
}
```

### Authentication Failures

**Problem**: Invalid credentials or RBAC restrictions

**Solution**:
- Verify credentials with basic curl test
- Check user has appropriate permissions
- For test: use admin account
- For production: create read-only service account

### Pagination Issues

**Problem**: Only getting first 100 results

**Solution**: Implement pagination loop:
```bash
offset=0
length=100
while true; do
    response=$(curl -k -u "$USER:$PASS" -X POST \
        -d "{\"kind\":\"vm\",\"offset\":$offset,\"length\":$length}" \
        https://$PRISM/api/nutanix/v3/vms/list)

    count=$(echo "$response" | jq '.metadata.total_matches')
    offset=$((offset + length))

    [ $offset -ge $count ] && break
done
```

---

## Resources

- **Nutanix Developer Portal**: https://www.nutanix.dev/
- **API Reference**: https://www.nutanix.dev/api-reference/prism-central/
- **Nutanix Community**: https://next.nutanix.com/
- **Prism Central Guide**: https://portal.nutanix.com/page/documents/details?targetId=Prism-Central-Guide
