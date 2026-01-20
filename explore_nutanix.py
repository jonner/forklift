#!/usr/bin/env python3
"""
Nutanix API Explorer for Forklift Integration

This script helps explore Nutanix Prism v3 API and save responses
for test data creation.

Usage:
    python3 explore_nutanix.py --host prism.local --user admin --password secret

Requirements:
    pip install requests
"""

import argparse
import json
import os
import sys
from getpass import getpass
from pathlib import Path

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    print("Error: requests library not found")
    print("Install with: pip install requests")
    sys.exit(1)

# Disable SSL warnings for self-signed certs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NutanixAPI:
    """Simple Nutanix Prism v3 API client"""

    def __init__(self, host, username, password, port=9440, verify_ssl=False):
        self.base_url = f"https://{host}:{port}/api/nutanix/v3"
        self.auth = HTTPBasicAuth(username, password)
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = verify_ssl

    def list_resources(self, resource_kind, filter_expr=None, offset=0, length=100):
        """
        List resources using Nutanix v3 API pattern

        Args:
            resource_kind: Type of resource (vm, cluster, host, etc.)
            filter_expr: Optional filter expression
            offset: Pagination offset
            length: Number of results to return

        Returns:
            dict: API response
        """
        url = f"{self.base_url}/{resource_kind}s/list"

        payload = {
            "kind": resource_kind,
            "offset": offset,
            "length": length
        }

        if filter_expr:
            payload["filter"] = filter_expr

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {resource_kind}s: {e}")
            return None

    def get_resource(self, resource_kind, uuid):
        """Get a specific resource by UUID"""
        url = f"{self.base_url}/{resource_kind}s/{uuid}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {resource_kind} {uuid}: {e}")
            return None

    def test_connection(self):
        """Test API connection"""
        try:
            result = self.list_resources("cluster", length=1)
            if result:
                print("✓ Connection successful!")
                return True
            return False
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False


def save_json(data, filepath):
    """Save JSON data to file with pretty printing"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Saved to: {filepath}")


def explore_clusters(api, output_dir):
    """Explore cluster information"""
    print("\n📊 Clusters:")
    data = api.list_resources("cluster")

    if data and "entities" in data:
        for cluster in data["entities"]:
            uuid = cluster.get("metadata", {}).get("uuid")
            name = cluster.get("metadata", {}).get("name")
            version = cluster.get("status", {}).get("resources", {}).get("config", {}).get("build", {}).get("version", "unknown")
            print(f"  - {name} (UUID: {uuid}, Version: {version})")

        save_json(data, output_dir / "clusters_list.json")
        return data
    return None


def explore_hosts(api, output_dir):
    """Explore host information"""
    print("\n🖥️  Hosts:")
    data = api.list_resources("host")

    if data and "entities" in data:
        for host in data["entities"]:
            uuid = host.get("metadata", {}).get("uuid")
            name = host.get("metadata", {}).get("name")
            resources = host.get("status", {}).get("resources", {})
            cpu_cores = resources.get("num_cpu_cores", "?")
            memory_mib = resources.get("memory_capacity_mib", 0)
            memory_gb = memory_mib / 1024 if memory_mib else 0

            print(f"  - {name} (UUID: {uuid})")
            print(f"    CPU Cores: {cpu_cores}, Memory: {memory_gb:.1f} GB")

        save_json(data, output_dir / "hosts_list.json")
        return data
    return None


def explore_vms(api, output_dir):
    """Explore VM information"""
    print("\n💻 Virtual Machines:")
    data = api.list_resources("vm")

    if data and "entities" in data:
        total = data.get("metadata", {}).get("total_matches", 0)
        print(f"  Total VMs: {total}")

        for vm in data["entities"][:10]:  # Show first 10
            uuid = vm.get("metadata", {}).get("uuid")
            name = vm.get("metadata", {}).get("name")
            resources = vm.get("spec", {}).get("resources", {})
            power_state = resources.get("power_state", "unknown")
            vcpus = resources.get("num_sockets", 0) * resources.get("num_vcpus_per_socket", 0)
            memory_mib = resources.get("memory_size_mib", 0)

            print(f"  - {name} ({power_state})")
            print(f"    UUID: {uuid}")
            print(f"    vCPUs: {vcpus}, Memory: {memory_mib} MiB")
            print(f"    NICs: {len(resources.get('nic_list', []))}, Disks: {len(resources.get('disk_list', []))}")

        if total > 10:
            print(f"  ... and {total - 10} more VMs")

        save_json(data, output_dir / "vms_list.json")

        # Get detailed info for first VM
        if data["entities"]:
            first_vm_uuid = data["entities"][0].get("metadata", {}).get("uuid")
            if first_vm_uuid:
                print(f"\n  Fetching detailed info for first VM...")
                vm_detail = api.get_resource("vm", first_vm_uuid)
                if vm_detail:
                    save_json(vm_detail, output_dir / "vm_detail_example.json")

        return data
    return None


def explore_networks(api, output_dir):
    """Explore network/subnet information"""
    print("\n🌐 Networks (Subnets):")
    data = api.list_resources("subnet")

    if data and "entities" in data:
        for subnet in data["entities"]:
            uuid = subnet.get("metadata", {}).get("uuid")
            name = subnet.get("metadata", {}).get("name")
            resources = subnet.get("spec", {}).get("resources", {})
            vlan_id = resources.get("vlan_id", "N/A")
            subnet_type = resources.get("subnet_type", "unknown")

            ip_config = resources.get("ip_config", {})
            subnet_ip = ip_config.get("subnet_ip", "")
            prefix = ip_config.get("prefix_length", "")
            cidr = f"{subnet_ip}/{prefix}" if subnet_ip else "N/A"

            print(f"  - {name} (UUID: {uuid})")
            print(f"    Type: {subnet_type}, VLAN: {vlan_id}, CIDR: {cidr}")

        save_json(data, output_dir / "subnets_list.json")
        return data
    return None


def explore_storage(api, output_dir):
    """Explore storage container information"""
    print("\n💾 Storage Containers:")
    data = api.list_resources("storage_container")

    if data and "entities" in data:
        for container in data["entities"]:
            uuid = container.get("metadata", {}).get("uuid")
            name = container.get("metadata", {}).get("name")
            resources = container.get("status", {}).get("resources", {})
            rf = resources.get("replication_factor", "?")
            max_capacity = resources.get("max_capacity_bytes", 0)
            max_capacity_gb = max_capacity / (1024**3) if max_capacity else 0

            usage = resources.get("usage_stats", {}).get("storage.user_usage_bytes", 0)
            usage_gb = usage / (1024**3) if usage else 0

            compression = "Yes" if resources.get("compression_enabled") else "No"
            dedup = "Yes" if resources.get("dedup_enabled") else "No"

            print(f"  - {name} (UUID: {uuid})")
            print(f"    Capacity: {max_capacity_gb:.1f} GB, Used: {usage_gb:.1f} GB, RF: {rf}")
            print(f"    Compression: {compression}, Dedup: {dedup}")

        save_json(data, output_dir / "storage_containers_list.json")
        return data
    return None


def explore_images(api, output_dir):
    """Explore image information"""
    print("\n📀 Images:")
    data = api.list_resources("image")

    if data and "entities" in data:
        for image in data["entities"]:
            uuid = image.get("metadata", {}).get("uuid")
            name = image.get("metadata", {}).get("name")
            resources = image.get("status", {}).get("resources", {})
            image_type = resources.get("image_type", "unknown")
            size_bytes = resources.get("size_bytes", 0)
            size_gb = size_bytes / (1024**3) if size_bytes else 0

            print(f"  - {name} (UUID: {uuid})")
            print(f"    Type: {image_type}, Size: {size_gb:.2f} GB")

        save_json(data, output_dir / "images_list.json")
        return data
    return None


def create_test_fixtures(output_dir):
    """Create minimal test fixtures for development without Nutanix env"""
    print("\n📝 Creating minimal test fixtures...")

    fixtures_dir = output_dir / "testdata_minimal"

    # Minimal cluster response
    clusters = {
        "entities": [
            {
                "metadata": {
                    "uuid": "00000000-0000-0000-0000-000000000001",
                    "name": "test-cluster-1"
                },
                "spec": {"name": "test-cluster-1"},
                "status": {
                    "resources": {
                        "config": {
                            "build": {"version": "6.8.2"},
                            "timezone": "America/Los_Angeles"
                        }
                    }
                }
            }
        ],
        "metadata": {"total_matches": 1}
    }

    # Minimal VM response
    vms = {
        "entities": [
            {
                "metadata": {
                    "uuid": "vm-00000000-0000-0000-0000-000000000001",
                    "name": "test-vm-rhel-1"
                },
                "spec": {
                    "name": "test-vm-rhel-1",
                    "cluster_reference": {
                        "kind": "cluster",
                        "uuid": "00000000-0000-0000-0000-000000000001"
                    },
                    "resources": {
                        "power_state": "ON",
                        "num_sockets": 2,
                        "num_vcpus_per_socket": 2,
                        "memory_size_mib": 4096,
                        "boot_config": {
                            "boot_type": "UEFI",
                            "boot_device_order_list": ["DISK", "NETWORK"]
                        },
                        "nic_list": [
                            {
                                "uuid": "nic-1",
                                "nic_type": "NORMAL_NIC",
                                "mac_address": "50:6b:8d:12:34:56",
                                "model": "VIRTIO"
                            }
                        ],
                        "disk_list": [
                            {
                                "uuid": "disk-1",
                                "disk_size_mib": 102400,
                                "device_properties": {
                                    "device_type": "DISK",
                                    "disk_address": {
                                        "adapter_type": "SCSI",
                                        "device_index": 0
                                    }
                                }
                            }
                        ]
                    }
                },
                "status": {
                    "resources": {
                        "hypervisor_type": "kKvm"
                    }
                }
            }
        ],
        "metadata": {"total_matches": 1}
    }

    save_json(clusters, fixtures_dir / "clusters_response.json")
    save_json(vms, fixtures_dir / "vms_response.json")

    print(f"\n✓ Test fixtures created in: {fixtures_dir}")
    print("  Use these for development when you don't have a Nutanix environment")


def main():
    parser = argparse.ArgumentParser(
        description="Explore Nutanix Prism v3 API for Forklift integration"
    )
    parser.add_argument("--host", required=True, help="Prism Central/Element hostname or IP")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--password", help="Password (will prompt if not provided)")
    parser.add_argument("--port", type=int, default=9440, help="API port (default: 9440)")
    parser.add_argument("--output", default="./nutanix_api_data", help="Output directory")
    parser.add_argument("--create-fixtures", action="store_true",
                        help="Create minimal test fixtures for development")

    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass(f"Password for {args.user}@{args.host}: ")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔍 Nutanix API Explorer")
    print(f"   Host: {args.host}:{args.port}")
    print(f"   User: {args.user}")
    print(f"   Output: {output_dir}")
    print(f"\n{'='*60}")

    # Create API client
    api = NutanixAPI(args.host, args.user, password, args.port)

    # Test connection
    if not api.test_connection():
        print("\n❌ Could not connect to Nutanix API")
        print("   Check host, credentials, and network connectivity")
        sys.exit(1)

    # Explore all resources
    try:
        explore_clusters(api, output_dir)
        explore_hosts(api, output_dir)
        explore_vms(api, output_dir)
        explore_networks(api, output_dir)
        explore_storage(api, output_dir)
        explore_images(api, output_dir)

        print(f"\n{'='*60}")
        print(f"✓ API exploration complete!")
        print(f"\n📂 All responses saved to: {output_dir}/")
        print(f"\n💡 Next steps:")
        print(f"   1. Review JSON responses to understand data structures")
        print(f"   2. Use responses to create testdata/ fixtures")
        print(f"   3. Start implementing Nutanix provider in forklift")

        # Optionally create test fixtures
        if args.create_fixtures:
            create_test_fixtures(output_dir)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
