#!/usr/bin/env python3
"""
Analyze and visualize Nutanix test data

This script loads the mock Nutanix API responses and provides
a summary of the test environment.

Usage:
    python3 analyze_testdata.py
"""

import json
import os
from pathlib import Path

TESTDATA_DIR = Path(__file__).parent / "pkg/controller/provider/container/nutanix/testdata"


def load_json(filename):
    """Load JSON file from testdata directory"""
    filepath = TESTDATA_DIR / filename
    if not filepath.exists():
        print(f"Warning: {filepath} not found")
        return None

    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_clusters(data):
    """Analyze cluster data"""
    if not data:
        return

    print("\n" + "="*70)
    print("CLUSTERS")
    print("="*70)

    for cluster in data.get('entities', []):
        name = cluster['metadata']['name']
        uuid = cluster['metadata']['uuid']
        version = cluster['status']['resources']['config']['build'].get('version', 'N/A')
        vm_count = cluster['status']['resources']['analysis'].get('vm_count', 0)

        storage = cluster['status']['resources']['analysis'].get('storage_summary', {})
        total_tb = storage.get('total_capacity_bytes', 0) / (1024**4)
        used_tb = storage.get('usage_bytes', 0) / (1024**4)

        print(f"\n📊 {name}")
        print(f"   UUID: {uuid}")
        print(f"   AOS Version: {version}")
        print(f"   VMs: {vm_count}")
        print(f"   Storage: {used_tb:.1f} TB / {total_tb:.1f} TB used")


def analyze_hosts(data):
    """Analyze host data"""
    if not data:
        return

    print("\n" + "="*70)
    print("HOSTS")
    print("="*70)

    for host in data.get('entities', []):
        name = host['metadata']['name']
        uuid = host['metadata']['uuid']
        cluster = host['spec']['cluster_reference']['name']

        resources = host['status']['resources']
        cpu_sockets = resources.get('num_cpu_sockets', 0)
        cpu_cores = resources.get('num_cpu_cores', 0)
        memory_gb = resources.get('memory_capacity_mib', 0) / 1024
        num_vms = resources['hypervisor'].get('num_vms', 0)
        state = resources.get('state', 'UNKNOWN')

        print(f"\n🖥️  {name}")
        print(f"   UUID: {uuid}")
        print(f"   Cluster: {cluster}")
        print(f"   CPU: {cpu_sockets} sockets × {cpu_cores//cpu_sockets} cores = {cpu_cores} total cores")
        print(f"   Memory: {memory_gb:.0f} GB")
        print(f"   VMs: {num_vms}")
        print(f"   State: {state}")


def analyze_vms(data):
    """Analyze VM data"""
    if not data:
        return

    print("\n" + "="*70)
    print("VIRTUAL MACHINES")
    print("="*70)

    total = data.get('metadata', {}).get('total_matches', 0)
    print(f"\nTotal VMs: {total}")

    for vm in data.get('entities', []):
        name = vm['metadata']['name']
        uuid = vm['metadata']['uuid']

        resources = vm['spec']['resources']
        power_state = resources.get('power_state', 'UNKNOWN')
        vcpus = resources.get('num_sockets', 0) * resources.get('num_vcpus_per_socket', 0)
        memory_gb = resources.get('memory_size_mib', 0) / 1024
        boot_type = resources.get('boot_config', {}).get('boot_type', 'UNKNOWN')
        num_disks = len(resources.get('disk_list', []))
        num_nics = len(resources.get('nic_list', []))

        # Get host if VM is running
        host = "N/A"
        if 'status' in vm and 'resources' in vm['status']:
            host_ref = vm['status']['resources'].get('host_reference', {})
            host = host_ref.get('name', 'N/A')

        # Categories/tags
        categories = vm['metadata'].get('categories', {})
        tags = ", ".join([f"{k}:{v}" for k, v in categories.items()]) if categories else "None"

        icon = "✅" if power_state == "ON" else "⭕"

        print(f"\n{icon} {name} ({power_state})")
        print(f"   UUID: {uuid}")
        print(f"   vCPUs: {vcpus}, Memory: {memory_gb:.0f} GB")
        print(f"   Boot: {boot_type}")
        print(f"   Disks: {num_disks}, NICs: {num_nics}")
        print(f"   Host: {host}")
        if tags != "None":
            print(f"   Tags: {tags}")


def analyze_networks(data):
    """Analyze network/subnet data"""
    if not data:
        return

    print("\n" + "="*70)
    print("NETWORKS (Subnets)")
    print("="*70)

    for subnet in data.get('entities', []):
        name = subnet['metadata']['name']
        uuid = subnet['metadata']['uuid']

        resources = subnet['spec']['resources']
        vlan_id = resources.get('vlan_id', 'N/A')
        subnet_type = resources.get('subnet_type', 'UNKNOWN')

        ip_config = resources.get('ip_config', {})
        subnet_ip = ip_config.get('subnet_ip', '')
        prefix = ip_config.get('prefix_length', '')
        gateway = ip_config.get('default_gateway_ip', 'N/A')

        cidr = f"{subnet_ip}/{prefix}" if subnet_ip else "N/A"

        pool_list = ip_config.get('pool_list', [])
        dhcp_pool = pool_list[0].get('range', 'N/A') if pool_list else 'N/A'

        print(f"\n🌐 {name}")
        print(f"   UUID: {uuid}")
        print(f"   Type: {subnet_type}, VLAN: {vlan_id}")
        print(f"   CIDR: {cidr}")
        print(f"   Gateway: {gateway}")
        print(f"   DHCP Pool: {dhcp_pool}")


def analyze_storage(data):
    """Analyze storage container data"""
    if not data:
        return

    print("\n" + "="*70)
    print("STORAGE CONTAINERS")
    print("="*70)

    for container in data.get('entities', []):
        name = container['metadata']['name']
        uuid = container['metadata']['uuid']

        resources = container['status']['resources']
        rf = resources.get('replication_factor', 'N/A')

        max_capacity_tb = resources.get('max_capacity_bytes', 0) / (1024**4)

        usage_stats = resources.get('usage_stats', {})
        used_tb = int(usage_stats.get('storage.user_usage_bytes', 0)) / (1024**4)
        free_tb = int(usage_stats.get('storage.user_free_bytes', 0)) / (1024**4)

        compression = "✅" if resources.get('compression_enabled') else "❌"
        dedup = "✅" if resources.get('dedup_enabled') else "❌"
        ec = resources.get('erasure_code', 'off')

        usage_pct = (used_tb / max_capacity_tb * 100) if max_capacity_tb > 0 else 0

        print(f"\n💾 {name}")
        print(f"   UUID: {uuid}")
        print(f"   Capacity: {max_capacity_tb:.1f} TB total, {used_tb:.1f} TB used ({usage_pct:.0f}%)")
        print(f"   Replication Factor: {rf}")
        print(f"   Compression: {compression}, Dedup: {dedup}, Erasure Coding: {ec}")


def analyze_images(data):
    """Analyze image data"""
    if not data:
        return

    print("\n" + "="*70)
    print("IMAGES")
    print("="*70)

    for image in data.get('entities', []):
        name = image['metadata']['name']
        uuid = image['metadata']['uuid']

        resources = image['status']['resources']
        image_type = resources.get('image_type', 'UNKNOWN')
        size_gb = resources.get('size_bytes', 0) / (1024**3)
        arch = resources.get('architecture', 'UNKNOWN')

        icon = "📀" if image_type == "ISO_IMAGE" else "💿"

        print(f"\n{icon} {name}")
        print(f"   UUID: {uuid}")
        print(f"   Type: {image_type}")
        print(f"   Size: {size_gb:.2f} GB")
        print(f"   Architecture: {arch}")


def print_summary():
    """Print overall summary"""
    clusters = load_json('clusters_list.json')
    hosts = load_json('hosts_list.json')
    vms = load_json('vms_list.json')
    networks = load_json('subnets_list.json')
    storage = load_json('storage_containers_list.json')
    images = load_json('images_list.json')

    print("\n" + "="*70)
    print("NUTANIX TEST DATA SUMMARY")
    print("="*70)

    num_clusters = len(clusters.get('entities', [])) if clusters else 0
    num_hosts = len(hosts.get('entities', [])) if hosts else 0
    num_vms = len(vms.get('entities', [])) if vms else 0
    num_networks = len(networks.get('entities', [])) if networks else 0
    num_storage = len(storage.get('entities', [])) if storage else 0
    num_images = len(images.get('entities', [])) if images else 0

    print(f"""
📊 Clusters:          {num_clusters}
🖥️  Hosts:             {num_hosts}
💻 Virtual Machines:  {num_vms}
🌐 Networks:          {num_networks}
💾 Storage:           {num_storage}
📀 Images:            {num_images}
""")

    if vms:
        vm_entities = vms.get('entities', [])
        powered_on = sum(1 for vm in vm_entities if vm['spec']['resources'].get('power_state') == 'ON')
        powered_off = num_vms - powered_on

        boot_types = {}
        for vm in vm_entities:
            boot_type = vm['spec']['resources'].get('boot_config', {}).get('boot_type', 'UNKNOWN')
            boot_types[boot_type] = boot_types.get(boot_type, 0) + 1

        print(f"VM Power States:")
        print(f"  ✅ Powered ON:  {powered_on}")
        print(f"  ⭕ Powered OFF: {powered_off}")
        print(f"\nVM Boot Types:")
        for boot_type, count in boot_types.items():
            print(f"  {boot_type}: {count}")


def main():
    print("\n" + "🔍 Analyzing Nutanix Test Data")
    print("📂 Location: {}".format(TESTDATA_DIR))

    if not TESTDATA_DIR.exists():
        print(f"\n❌ Error: Test data directory not found at {TESTDATA_DIR}")
        print("   Run from the forklift repository root directory")
        return

    # Print summary first
    print_summary()

    # Detailed analysis
    clusters = load_json('clusters_list.json')
    hosts = load_json('hosts_list.json')
    vms = load_json('vms_list.json')
    networks = load_json('subnets_list.json')
    storage = load_json('storage_containers_list.json')
    images = load_json('images_list.json')

    analyze_clusters(clusters)
    analyze_hosts(hosts)
    analyze_vms(vms)
    analyze_networks(networks)
    analyze_storage(storage)
    analyze_images(images)

    print("\n" + "="*70)
    print("✅ Analysis complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
