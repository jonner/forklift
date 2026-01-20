# Nutanix Provider Requirements for Forklift

**Document Version**: 1.0
**Date**: December 2024
**Status**: Draft for Community Review
**Author**: Platform Engineering Team

---

## Executive Summary

This document defines the requirements for adding Nutanix AHV as a supported source provider in Forklift, enabling organizations to migrate virtual machines from Nutanix infrastructure to OpenShift with KubeVirt.

**Scope**: Phase 1 focuses on provider registration, authentication, inventory collection, and basic validation. Phase 2 will add full VM migration capabilities.

**Impact**: Extends Forklift's multi-cloud migration capabilities to support Nutanix AHV environments, addressing a significant market segment currently without a native migration path to OpenShift.

---

## Table of Contents

1. [Background](#1-background)
2. [Objectives](#2-objectives)
3. [Functional Requirements](#3-functional-requirements)
4. [Technical Requirements](#4-technical-requirements)
5. [API Requirements](#5-api-requirements)
6. [Data Model Requirements](#6-data-model-requirements)
7. [Migration Requirements](#7-migration-requirements)
8. [Security Requirements](#8-security-requirements)
9. [Performance Requirements](#9-performance-requirements)
10. [Testing Requirements](#10-testing-requirements)
11. [Documentation Requirements](#11-documentation-requirements)
12. [Success Criteria](#12-success-criteria)
13. [Implementation Phases](#13-implementation-phases)
14. [Dependencies](#14-dependencies)
15. [Risks and Mitigation](#15-risks-and-mitigation)
16. [Open Questions](#16-open-questions)

---

## 1. Background

### 1.1 Problem Statement

Organizations using Nutanix AHV for virtualization infrastructure currently lack a native, supported path to migrate workloads to OpenShift with KubeVirt. Forklift supports VMware vSphere, Red Hat Virtualization (oVirt), and OpenStack, but Nutanix—a significant player in hyperconverged infrastructure—is not supported.

### 1.2 Market Context

- **Nutanix Market Share**: Significant presence in enterprise HCI market
- **AHV Adoption**: Growing number of organizations standardizing on Nutanix AHV
- **Migration Demand**: Enterprises modernizing workloads to Kubernetes/OpenShift
- **Competitive Gap**: VMware alternatives increasingly important

### 1.3 Strategic Value

Adding Nutanix support to Forklift:
- Expands addressable market for OpenShift migrations
- Provides competitive advantage for organizations evaluating VMware alternatives
- Aligns with Red Hat's multi-cloud strategy
- Reduces migration friction for Nutanix customers

### 1.4 Technical Feasibility

**High feasibility** due to:
- Nutanix AHV is KVM-based (same as KubeVirt) - no VM conversion needed
- Native QCOW2 disk format - simpler than VMDK conversion
- Well-documented REST API (Prism v3)
- Similar architecture patterns to existing vSphere provider

---

## 2. Objectives

### 2.1 Primary Objectives

1. **Enable Nutanix as a source provider** in Forklift
2. **Inventory and discover** Nutanix infrastructure resources
3. **Validate VMs** for migration compatibility
4. **Migrate VMs** from Nutanix AHV to OpenShift KubeVirt
5. **Preserve VM configuration** (CPU, memory, networks, storage)

### 2.2 Secondary Objectives

1. Support both Prism Central and Prism Element deployment modes
2. Map Nutanix categories (tags) to Kubernetes labels
3. Provide pre-migration validation and warnings
4. Document migration best practices and limitations
5. Enable community contributions and testing

### 2.3 Non-Objectives (Out of Scope)

- Bi-directional migration (KubeVirt → Nutanix) - future consideration
- Nutanix Files/Objects/Volumes migration - focus on VMs only
- Nutanix-specific features not applicable to KubeVirt (e.g., Flow microsegmentation)
- Support for deprecated Nutanix API versions (v1/v2)

---

## 3. Functional Requirements

### 3.1 Provider Registration

**FR-1.1**: User SHALL be able to create a Nutanix Provider custom resource
**FR-1.2**: Provider SHALL support connection to Prism Central (primary)
**FR-1.3**: Provider SHALL support connection to Prism Element (fallback)
**FR-1.4**: Provider SHALL validate credentials during registration
**FR-1.5**: Provider SHALL test connectivity and report status
**FR-1.6**: Provider SHALL store credentials securely in Kubernetes Secrets

**Acceptance Criteria**:
```yaml
apiVersion: forklift.konveyor.io/v1beta1
kind: Provider
metadata:
  name: nutanix-prod
  namespace: konveyor-forklift
spec:
  type: nutanix
  url: https://prism-central.example.com:9440
  secret:
    name: nutanix-credentials
    namespace: konveyor-forklift
  settings:
    prismType: "central"  # or "element"
```

### 3.2 Inventory Collection

**FR-2.1**: System SHALL discover and inventory Nutanix clusters
**FR-2.2**: System SHALL discover and inventory AHV hosts
**FR-2.3**: System SHALL discover and inventory virtual machines
**FR-2.4**: System SHALL discover and inventory networks (subnets)
**FR-2.5**: System SHALL discover and inventory storage containers
**FR-2.6**: System SHALL discover and inventory disk images
**FR-2.7**: System SHALL refresh inventory periodically (configurable interval)
**FR-2.8**: System SHALL detect and handle inventory changes (VMs added/removed/modified)

**Inventory Scope**:
- Minimum: Clusters, Hosts, VMs, Networks, Storage
- Optional: Images, Protection Domains, Categories

### 3.3 Resource Details

**FR-3.1**: System SHALL expose VM configuration details via REST API
**FR-3.2**: VM details SHALL include CPU topology (sockets, cores per socket)
**FR-3.3**: VM details SHALL include memory allocation
**FR-3.4**: VM details SHALL include boot configuration (BIOS/UEFI/Secure Boot)
**FR-3.5**: VM details SHALL include network interfaces with MAC addresses and IPs
**FR-3.6**: VM details SHALL include disk configuration and sizes
**FR-3.7**: VM details SHALL include power state (ON/OFF)
**FR-3.8**: VM details SHALL include guest tools status
**FR-3.9**: VM details SHALL include categories/tags
**FR-3.10**: VM details SHALL include current host assignment

### 3.4 Migration Planning

**FR-4.1**: User SHALL be able to create migration plans with Nutanix as source
**FR-4.2**: System SHALL validate VM compatibility for migration
**FR-4.3**: System SHALL provide network mapping (Nutanix subnet → NetworkAttachmentDefinition)
**FR-4.4**: System SHALL provide storage mapping (Storage Container → StorageClass)
**FR-4.5**: System SHALL detect and warn about unsupported configurations
**FR-4.6**: System SHALL calculate estimated migration time and resource requirements

### 3.5 VM Migration

**FR-5.1**: System SHALL migrate VM configuration to KubeVirt VirtualMachine
**FR-5.2**: System SHALL transfer VM disks to persistent volumes
**FR-5.3**: System SHALL preserve CPU and memory allocation
**FR-5.4**: System SHALL preserve network configuration
**FR-5.5**: System SHALL preserve boot configuration (BIOS/UEFI/Secure Boot)
**FR-5.6**: System SHALL handle multi-disk VMs
**FR-5.7**: System SHALL handle multi-NIC VMs
**FR-5.8**: System SHALL support both warm and cold migrations
**FR-5.9**: System SHALL provide migration progress tracking
**FR-5.10**: System SHALL handle migration failures gracefully with rollback

### 3.6 Validation and Concerns

**FR-6.1**: System SHALL identify VMs with unsupported features
**FR-6.2**: System SHALL warn about features that cannot be migrated
**FR-6.3**: System SHALL validate network availability in target cluster
**FR-6.4**: System SHALL validate storage availability in target cluster
**FR-6.5**: System SHALL provide pre-migration validation report

**Unsupported Features** (should generate warnings):
- GPU/vGPU assignments (without node configuration)
- Volume Groups (will be flattened to individual disks)
- Nutanix-specific features (Protection Domains, Categories beyond labels)

### 3.7 User Interface

**FR-7.1**: Nutanix SHALL appear as a provider type in UI
**FR-7.2**: UI SHALL display Nutanix inventory in provider tree
**FR-7.3**: UI SHALL support filtering and searching Nutanix resources
**FR-7.4**: UI SHALL display VM details and migration readiness
**FR-7.5**: UI SHALL provide network and storage mapping wizards
**FR-7.6**: UI SHALL display migration progress and status

---

## 4. Technical Requirements

### 4.1 Architecture

**TR-1.1**: Implementation SHALL follow existing Forklift provider patterns
**TR-1.2**: Implementation SHALL use Nutanix Prism v3 REST API
**TR-1.3**: Implementation SHALL support both Prism Central and Prism Element
**TR-1.4**: Implementation SHALL use Kubernetes custom resources for state management
**TR-1.5**: Provider SHALL run as a container in the Forklift operator

### 4.2 Code Organization

**TR-2.1**: Code SHALL be organized following vSphere provider structure
**TR-2.2**: Models SHALL be defined in `pkg/controller/provider/model/nutanix/`
**TR-2.3**: Client and collector SHALL be in `pkg/controller/provider/container/nutanix/`
**TR-2.4**: Web handlers SHALL be in `pkg/controller/provider/web/nutanix/`
**TR-2.5**: Provider type SHALL be registered in `pkg/apis/forklift/v1beta1/provider.go`

### 4.3 Language and Frameworks

**TR-3.1**: Implementation SHALL use Go (consistent with Forklift codebase)
**TR-3.2**: HTTP client SHALL support TLS with custom CA certificates
**TR-3.3**: HTTP client SHALL support connection pooling and timeouts
**TR-3.4**: REST API handlers SHALL use Gin framework (consistent with Forklift)

### 4.4 Dependencies

**TR-4.1**: SHOULD use official Nutanix Go SDK if available and maintained
**TR-4.2**: MAY implement custom REST client if SDK is insufficient
**TR-4.3**: SHALL NOT introduce dependencies with incompatible licenses
**TR-4.4**: SHALL minimize external dependencies

**Recommended**:
- Option 1: `github.com/nutanix-cloud-native/prism-go-client`
- Option 2: Custom REST client using standard `net/http`

### 4.5 Database and State

**TR-5.1**: Inventory SHALL be stored in local SQLite database (consistent with Forklift)
**TR-5.2**: Database schema SHALL support efficient querying and relationships
**TR-5.3**: Inventory refresh SHALL use incremental updates where possible
**TR-5.4**: Database migrations SHALL be handled automatically

---

## 5. API Requirements

### 5.1 Nutanix API Endpoints

**Required Endpoints**:

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `POST /api/nutanix/v3/clusters/list` | Discover clusters | P0 |
| `POST /api/nutanix/v3/hosts/list` | Discover hosts | P0 |
| `POST /api/nutanix/v3/vms/list` | List VMs | P0 |
| `GET /api/nutanix/v3/vms/{uuid}` | Get VM details | P0 |
| `POST /api/nutanix/v3/subnets/list` | List networks | P0 |
| `POST /api/nutanix/v3/storage_containers/list` | List storage | P0 |
| `POST /api/nutanix/v3/images/list` | List images | P1 |
| `POST /api/nutanix/v3/categories/list` | List categories | P2 |

**P0** = Required for POC
**P1** = Required for production
**P2** = Nice to have

### 5.2 Authentication

**AR-2.1**: API client SHALL use HTTP Basic Authentication
**AR-2.2**: API client SHALL support username/password credentials
**AR-2.3**: API client SHALL support API token authentication (if available)
**AR-2.4**: API client SHALL cache authentication for session duration
**AR-2.5**: API client SHALL handle authentication failures gracefully

### 5.3 Error Handling

**AR-3.1**: Client SHALL retry transient failures (5xx errors, timeouts)
**AR-3.2**: Client SHALL use exponential backoff for retries
**AR-3.3**: Client SHALL log detailed error information
**AR-3.4**: Client SHALL surface meaningful errors to users
**AR-3.5**: Client SHALL handle API version mismatches

### 5.4 Pagination

**AR-4.1**: Client SHALL handle paginated responses (offset/length)
**AR-4.2**: Client SHALL fetch all pages for complete inventory
**AR-4.3**: Client SHALL respect API rate limits
**AR-4.4**: Client SHALL use reasonable page sizes (default: 100 items)

### 5.5 API Compatibility

**AR-5.1**: Implementation SHALL target Nutanix AOS 6.5+
**AR-5.2**: Implementation SHALL support Prism Central PC.2022.x and later
**AR-5.3**: Implementation SHOULD gracefully degrade for older versions
**AR-5.4**: Implementation SHALL verify API version during connection test

---

## 6. Data Model Requirements

### 6.1 Resource Models

**DM-1.1**: Models SHALL accurately represent Nutanix API responses
**DM-1.2**: Models SHALL include all fields necessary for migration
**DM-1.3**: Models SHALL support efficient database storage
**DM-1.4**: Models SHALL maintain relationships between resources

### 6.2 Core Models

**Required Models**:

#### Cluster
```go
type Cluster struct {
    Base
    ClusterUUID    string
    Version        string
    Timezone       string
    NumNodes       int
    HypervisorType string
    Hosts          []Ref
    Networks       []Ref
    StorageContainers []Ref
}
```

#### Host
```go
type Host struct {
    Base
    Cluster          string  // Cluster reference
    HostUUID         string
    SerialNumber     string
    NumCpuSockets    int
    NumCpuCores      int
    MemoryCapacityMB int64
    HypervisorType   string
    State            string
}
```

#### VM
```go
type VM struct {
    Base
    Cluster           string
    Host              string
    UUID              string
    PowerState        string
    NumSockets        int
    NumVcpusPerSocket int
    MemorySizeMB      int64
    BootConfig        BootConfig
    MachineType       string
    NICs              []NIC
    Disks             []Disk
    GuestTools        GuestTools
    Categories        map[string]string
    Concerns          []Concern
}
```

#### Network
```go
type Network struct {
    Base
    Cluster        string
    NetworkUUID    string
    VlanID         int
    NetworkAddress string
    PrefixLength   int
    DefaultGateway string
    SubnetType     string
}
```

#### StorageContainer
```go
type StorageContainer struct {
    Base
    Cluster              string
    StorageContainerUUID string
    MaxCapacityBytes     int64
    UsageBytes           int64
    ReplicationFactor    int
    CompressionEnabled   bool
    DeduplicationEnabled bool
}
```

### 6.3 Data Mapping

**DM-3.1**: Nutanix UUIDs SHALL be preserved in internal models
**DM-3.2**: Resource names SHALL be stored and searchable
**DM-3.3**: Hierarchical relationships SHALL be maintained (Cluster → Host → VM)
**DM-3.4**: References SHALL use consistent Ref structure
**DM-3.5**: Timestamps SHALL use standard ISO 8601 format

### 6.4 Data Validation

**DM-4.1**: Models SHALL validate required fields on creation
**DM-4.2**: Models SHALL handle missing optional fields gracefully
**DM-4.3**: Models SHALL validate data types and ranges
**DM-4.4**: Models SHALL detect and report invalid references

---

## 7. Migration Requirements

### 7.1 VM Configuration Mapping

**MR-1.1**: CPU topology SHALL be preserved (sockets × cores)
**MR-1.2**: Memory allocation SHALL be preserved
**MR-1.3**: Boot mode SHALL be mapped:
- Nutanix LEGACY → KubeVirt BIOS
- Nutanix UEFI → KubeVirt UEFI
- Nutanix SECURE_BOOT → KubeVirt UEFI with Secure Boot

**MR-1.4**: Machine type SHALL be mapped:
- Nutanix PC → KubeVirt pc
- Nutanix Q35 → KubeVirt q35

**MR-1.5**: VGA console setting SHALL be preserved

### 7.2 Network Migration

**MR-2.1**: Each NIC SHALL be mapped to a NetworkAttachmentDefinition
**MR-2.2**: MAC addresses SHOULD be preserved when possible
**MR-2.3**: VLAN configuration SHALL be mapped via Multus CNI
**MR-2.4**: Static IP addresses SHOULD be preserved when feasible
**MR-2.5**: Multi-NIC VMs SHALL maintain interface order

### 7.3 Storage Migration

**MR-3.1**: Each disk SHALL be migrated to a PersistentVolumeClaim
**MR-3.2**: Disk sizes SHALL be preserved
**MR-3.3**: Disk order SHALL be preserved
**MR-3.4**: Boot disk SHALL be correctly identified
**MR-3.5**: QCOW2 format SHALL be used (native to both platforms)

**Disk Transfer Methods** (in priority order):
1. Nutanix Image Service API (preferred)
2. Direct access via SSH to Controller VM
3. Volume snapshot → S3 → CDI import

### 7.4 Guest Tools Transition

**MR-4.1**: Nutanix Guest Tools status SHALL be reported
**MR-4.2**: Migration documentation SHALL include qemu-guest-agent installation steps
**MR-4.3**: Post-migration checklist SHALL remind users to install qemu-guest-agent

### 7.5 Categories and Metadata

**MR-5.1**: Nutanix categories SHALL be converted to Kubernetes labels
**MR-5.2**: Original category names SHALL be preserved as annotations
**MR-5.3**: Category values SHALL be sanitized for Kubernetes label format
**MR-5.4**: VM description SHALL be preserved in annotations

### 7.6 Unsupported Features

**MR-6.1**: GPU/vGPU assignments SHALL generate warnings
**MR-6.2**: Volume Groups SHALL be flattened to individual disks
**MR-6.3**: Host affinity rules SHALL be documented (manual conversion to nodeSelector)
**MR-6.4**: Protection Domain membership SHALL be noted in annotations

### 7.7 Migration Modes

**MR-7.1**: System SHALL support cold migration (VM powered off)
**MR-7.2**: System SHOULD support warm migration (minimize downtime)
**MR-7.3**: Warm migration SHALL use snapshots for consistency
**MR-7.4**: Migration SHALL be resumable on failure

---

## 8. Security Requirements

### 8.1 Credential Management

**SR-1.1**: Credentials SHALL be stored in Kubernetes Secrets
**SR-1.2**: Credentials SHALL NOT be logged or exposed in API responses
**SR-1.3**: Credentials SHALL support rotation without service interruption
**SR-1.4**: Secrets SHALL be namespace-scoped

### 8.2 TLS/SSL

**SR-2.1**: TLS connections SHALL be enforced for API communication
**SR-2.2**: Custom CA certificates SHALL be supported
**SR-2.3**: Certificate validation SHALL be configurable (for test environments)
**SR-2.4**: Self-signed certificates SHALL be supported with explicit opt-in

### 8.3 RBAC

**SR-3.1**: Nutanix user SHALL have read-only permissions (minimum)
**SR-3.2**: Migration operations SHALL require write permissions (snapshot creation)
**SR-3.3**: System SHALL document required Nutanix permissions
**SR-3.4**: System SHALL validate permissions during provider setup

### 8.4 Network Security

**SR-4.1**: API communication SHALL use HTTPS (port 9440)
**SR-4.2**: Network policies SHALL restrict traffic to necessary endpoints
**SR-4.3**: Proxy support SHALL be available if needed

---

## 9. Performance Requirements

### 9.1 Inventory Collection

**PR-1.1**: Initial inventory collection SHALL complete within 5 minutes for 1000 VMs
**PR-1.2**: Incremental refresh SHALL complete within 2 minutes for 1000 VMs
**PR-1.3**: Inventory refresh interval SHALL be configurable (default: 10 minutes)
**PR-1.4**: System SHALL handle 5000+ VMs without performance degradation

### 9.2 API Performance

**PR-2.1**: REST API responses SHALL complete within 2 seconds (95th percentile)
**PR-2.2**: VM listing SHALL support pagination for large inventories
**PR-2.3**: Concurrent API requests SHALL be supported (up to 10 simultaneous)
**PR-2.4**: Watch/WebSocket connections SHALL handle 50+ concurrent clients

### 9.3 Migration Performance

**PR-3.1**: Disk transfer SHALL achieve at least 100 MB/s (network permitting)
**PR-3.2**: Multiple VMs SHALL be migrated concurrently (up to 10)
**PR-3.3**: Migration SHALL not impact Nutanix cluster performance significantly

### 9.4 Resource Usage

**PR-4.1**: Provider container SHALL use less than 512 MB memory (idle)
**PR-4.2**: Provider container SHALL use less than 2 GB memory (active migration)
**PR-4.3**: Database size SHALL be reasonable (<10 MB per 100 VMs)

---

## 10. Testing Requirements

### 10.1 Unit Testing

**TT-1.1**: Unit test coverage SHALL be at least 70%
**TT-1.2**: All API client methods SHALL have unit tests
**TT-1.3**: All data model transformations SHALL have unit tests
**TT-1.4**: Mock Nutanix API responses SHALL be used for testing
**TT-1.5**: Test data SHALL cover common and edge cases

### 10.2 Integration Testing

**TT-2.1**: Provider registration SHALL be tested end-to-end
**TT-2.2**: Inventory collection SHALL be tested with mock data
**TT-2.3**: REST API endpoints SHALL be tested
**TT-2.4**: Database operations SHALL be tested
**TT-2.5**: Error handling SHALL be tested (network failures, auth failures, etc.)

### 10.3 Migration Testing

**TT-3.1**: Simple VM migration SHALL be tested (Linux, single disk, single NIC)
**TT-3.2**: Complex VM migration SHALL be tested (Windows, multi-disk, multi-NIC)
**TT-3.3**: Different boot modes SHALL be tested (BIOS, UEFI, Secure Boot)
**TT-3.4**: Failed migration rollback SHALL be tested
**TT-3.5**: Network and storage mapping SHALL be tested

### 10.4 Compatibility Testing

**TT-4.1**: Multiple Nutanix AOS versions SHALL be tested (6.5, 6.7, 6.8+)
**TT-4.2**: Both Prism Central and Prism Element SHALL be tested
**TT-4.3**: Different cluster configurations SHALL be tested

### 10.5 Performance Testing

**TT-5.1**: Large inventory (1000+ VMs) SHALL be performance tested
**TT-5.2**: Concurrent migrations SHALL be tested
**TT-5.3**: Long-running operations SHALL be tested for stability

### 10.6 Test Environment

**TT-6.1**: Nutanix Community Edition SHALL be used for testing
**TT-6.2**: Mock data SHALL be available for development without Nutanix
**TT-6.3**: CI/CD pipeline SHALL run automated tests

---

## 11. Documentation Requirements

### 11.1 User Documentation

**DR-1.1**: Installation and setup guide SHALL be provided
**DR-1.2**: Provider configuration guide SHALL be provided
**DR-1.3**: Migration planning guide SHALL be provided
**DR-1.4**: Troubleshooting guide SHALL be provided
**DR-1.5**: Best practices document SHALL be provided

### 11.2 API Documentation

**DR-2.1**: REST API endpoints SHALL be documented
**DR-2.2**: Data models SHALL be documented
**DR-2.3**: Error codes and messages SHALL be documented

### 11.3 Operator Documentation

**DR-3.1**: Architecture diagram SHALL be provided
**DR-3.2**: Component interaction SHALL be documented
**DR-3.3**: Configuration options SHALL be documented
**DR-3.4**: Monitoring and observability SHALL be documented

### 11.4 Developer Documentation

**DR-4.1**: Development setup guide SHALL be provided
**DR-4.2**: Code organization SHALL be documented
**DR-4.3**: Testing procedures SHALL be documented
**DR-4.4**: Contribution guidelines SHALL be provided

### 11.5 Example Configurations

**DR-5.1**: Sample Provider CR SHALL be provided
**DR-5.2**: Sample Secret configuration SHALL be provided
**DR-5.3**: Sample migration plan SHALL be provided
**DR-5.4**: Network and storage mapping examples SHALL be provided

---

## 12. Success Criteria

### 12.1 Phase 1 Success (POC)

**Achieved when**:
- ✅ Nutanix provider type is registered in Forklift
- ✅ Provider CR can be created and validated
- ✅ Authentication with Prism Central/Element works
- ✅ Inventory collection completes successfully
- ✅ Clusters, hosts, VMs, networks, and storage are discovered
- ✅ REST API endpoints return data
- ✅ Watch functionality works for VMs
- ✅ Unit and integration tests pass
- ✅ Basic documentation is available

### 12.2 Phase 2 Success (Migration)

**Achieved when**:
- ✅ Migration plan can be created with Nutanix source
- ✅ Network and storage mapping UI works
- ✅ Simple Linux VM migrates successfully
- ✅ Windows VM migrates successfully
- ✅ Multi-disk VM migrates successfully
- ✅ Multi-NIC VM migrates successfully
- ✅ Different boot modes (BIOS/UEFI/Secure Boot) are preserved
- ✅ Migrated VMs boot and run in KubeVirt
- ✅ Migration validation and warnings work
- ✅ Complete documentation is available

### 12.3 Production Readiness

**Achieved when**:
- ✅ All functional requirements are met
- ✅ All test requirements are met
- ✅ Performance requirements are met
- ✅ Security requirements are met
- ✅ Documentation is complete
- ✅ Community feedback is incorporated
- ✅ Code review is complete
- ✅ Integration with Forklift UI is complete
- ✅ Release notes are prepared

---

## 13. Implementation Phases

### Phase 1: POC and Inventory (Weeks 1-4)

**Goals**:
- Prove technical feasibility
- Establish basic provider infrastructure
- Collect inventory successfully

**Deliverables**:
- Provider type registration
- Data models
- API client
- Inventory collector
- REST API handlers
- Unit tests
- Mock test data
- Basic documentation

**Success Criteria**: See section 12.1

### Phase 2: Migration Support (Weeks 5-8)

**Goals**:
- Enable VM migration
- Implement disk transfer
- Handle network and storage mapping

**Deliverables**:
- VM adapter (Nutanix → KubeVirt mapping)
- Network mapping logic
- Storage mapping logic
- Disk transfer implementation
- Migration scheduler
- Validation policies
- Integration tests
- Migration documentation

**Success Criteria**: See section 12.2

### Phase 3: Production Hardening (Weeks 9-12)

**Goals**:
- Improve reliability and performance
- Complete documentation
- Prepare for release

**Deliverables**:
- Performance optimizations
- Error handling improvements
- Comprehensive testing
- Complete documentation
- UI integration
- Community review feedback
- Release artifacts

**Success Criteria**: See section 12.3

---

## 14. Dependencies

### 14.1 External Dependencies

**Required**:
- Nutanix AOS 6.5+ with Prism Central or Prism Element
- Network connectivity to Nutanix API (HTTPS port 9440)
- Valid Nutanix credentials with appropriate permissions

**Optional**:
- Nutanix Go SDK (`github.com/nutanix-cloud-native/prism-go-client`)
- Nutanix Community Edition for testing

### 14.2 Forklift Dependencies

**Required**:
- Forklift operator 2.5+
- KubeVirt installed on target cluster
- CDI (Containerized Data Importer) for disk import
- Multus CNI for network mapping
- Appropriate storage classes for PVCs

**Build Dependencies**:
- Go 1.21+
- Make
- Docker/Podman for container builds

### 14.3 Documentation Dependencies

**Required**:
- Access to Nutanix API documentation
- Access to Nutanix test environment (CE or Test Drive)
- Sample Nutanix deployment for validation

---

## 15. Risks and Mitigation

### 15.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Nutanix API changes | High | Low | Pin to specific API version, add version checks |
| Disk transfer performance | Medium | Medium | Implement multiple transfer methods, optimize |
| Large-scale performance | Medium | Medium | Performance testing, optimization, pagination |
| Complex VM configurations | Medium | High | Comprehensive validation, clear warnings |
| Network mapping complexity | Medium | Medium | Well-designed mapping UI, validation |

### 15.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Insufficient testing resources | High | Medium | Use Nutanix CE, community testing |
| Limited Nutanix expertise | Medium | High | Documentation, community engagement |
| API rate limiting | Low | Medium | Implement backoff, respect limits |
| Authentication issues | Medium | Low | Clear documentation, validation |

### 15.3 Project Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | Medium | High | Clear phase boundaries, defer features |
| Community adoption | Low | Low | Good documentation, examples |
| Maintenance burden | Medium | Medium | Clean architecture, comprehensive tests |

---

## 16. Open Questions

### 16.1 Technical Questions

**Q1**: Should we support both Nutanix Go SDK and custom REST client?
**Status**: Open
**Owner**: Development Team
**Decision Needed By**: Week 1

**Q2**: What is the best disk transfer method (Image Service vs SSH)?
**Status**: Open
**Owner**: Development Team
**Decision Needed By**: Week 3
**Research Needed**: Test both methods with real Nutanix environment

**Q3**: How to handle Nutanix Volume Groups?
**Status**: Open
**Owner**: Development Team
**Decision**: Flatten to individual disks (simplest approach)

**Q4**: Should warm migration use snapshots or Change Block Tracking?
**Status**: Open
**Owner**: Development Team
**Decision Needed By**: Week 5
**Note**: Snapshot approach is simpler but may have longer cutover

### 16.2 Product Questions

**Q5**: What is the minimum supported Nutanix version?
**Recommendation**: AOS 6.5+ (maintains reasonable backwards compatibility)
**Owner**: Product Management

**Q6**: Should Prism Element support be equal priority to Prism Central?
**Recommendation**: Prism Central is primary, Prism Element is secondary
**Owner**: Product Management

**Q7**: What is the target release for Phase 1?
**Status**: Open
**Owner**: Product Management

### 16.3 Community Questions

**Q8**: What is the process for upstream contribution?
**Status**: Open
**Owner**: Community Lead

**Q9**: How to gather community testing and feedback?
**Status**: Open
**Owner**: Community Lead

---

## Appendix A: Nutanix-to-KubeVirt Feature Matrix

| Nutanix Feature | KubeVirt Equivalent | Support | Notes |
|-----------------|---------------------|---------|-------|
| CPU (sockets × cores) | CPU topology | ✅ Full | Direct mapping |
| Memory | Memory size | ✅ Full | Direct mapping |
| BIOS boot | BIOS firmware | ✅ Full | Direct mapping |
| UEFI boot | UEFI firmware | ✅ Full | Direct mapping |
| UEFI Secure Boot | UEFI Secure Boot | ✅ Full | Direct mapping |
| PC machine type | pc machine | ✅ Full | Direct mapping |
| Q35 machine type | q35 machine | ✅ Full | Direct mapping |
| SCSI disks | VirtIO disks | ✅ Full | Convert adapter type |
| Multiple disks | Multiple PVCs | ✅ Full | One PVC per disk |
| VIRTIO NICs | VirtIO interfaces | ✅ Full | Direct mapping |
| Multiple NICs | Multiple interfaces | ✅ Full | Via Multus |
| VLAN networks | NetworkAttachmentDef | ✅ Full | Via Multus CNI |
| Static IPs | Static IPs | ⚠️ Partial | Requires configuration |
| DHCP IPs | DHCP | ✅ Full | Via CNI |
| Storage containers | StorageClasses | ✅ Full | Manual mapping |
| QCOW2 format | QCOW2 format | ✅ Full | Native support |
| Categories (tags) | Labels | ✅ Full | Converted |
| Nutanix Guest Tools | qemu-guest-agent | ⚠️ Manual | Post-migration |
| VGA console | Console | ✅ Full | Direct mapping |
| Serial ports | Serial console | ✅ Full | Direct mapping |
| Volume Groups | N/A | ❌ Flatten | Converted to disks |
| GPU passthrough | GPU passthrough | ⚠️ Manual | Requires node config |
| Host affinity | nodeSelector | ⚠️ Manual | User must configure |
| Protection Domains | N/A | ❌ Info only | Annotation only |

**Legend**:
- ✅ Full: Complete support, automatic migration
- ⚠️ Partial: Supported with limitations or manual steps
- ⚠️ Manual: Requires manual configuration
- ❌ Flatten: Feature is decomposed/simplified
- ❌ Info only: Information preserved but not functional

---

## Appendix B: API Endpoint Reference

### Required Endpoints (Phase 1)

| Method | Endpoint | Purpose | Response Size |
|--------|----------|---------|---------------|
| POST | `/api/nutanix/v3/clusters/list` | List clusters | Small |
| POST | `/api/nutanix/v3/hosts/list` | List hosts | Small |
| POST | `/api/nutanix/v3/vms/list` | List VMs | Large |
| GET | `/api/nutanix/v3/vms/{uuid}` | Get VM details | Medium |
| POST | `/api/nutanix/v3/subnets/list` | List networks | Medium |
| POST | `/api/nutanix/v3/storage_containers/list` | List storage | Small |

### Optional Endpoints (Phase 1)

| Method | Endpoint | Purpose | Priority |
|--------|----------|---------|----------|
| POST | `/api/nutanix/v3/images/list` | List images | P1 |
| POST | `/api/nutanix/v3/categories/list` | List categories | P2 |
| GET | `/api/nutanix/v3/clusters/{uuid}` | Cluster details | P2 |

### Required Endpoints (Phase 2 - Migration)

| Method | Endpoint | Purpose | Priority |
|--------|----------|---------|----------|
| POST | `/api/nutanix/v3/snapshots` | Create snapshot | P0 |
| POST | `/api/nutanix/v3/images` | Export disk | P0 |
| GET | `/api/nutanix/v3/images/{uuid}/file` | Download disk | P0 |

---

## Appendix C: Test Data Summary

Mock test data has been created representing:

**Infrastructure**:
- 2 Nutanix clusters (prod-cluster-01, dev-cluster-01)
- 3 AHV hosts (80 cores, 640 GB RAM total)
- 4 Networks (VLAN 1, 10, 100, 200)
- 3 Storage containers (14 TB total)
- 4 Disk images (RHEL, Ubuntu, Windows, VirtIO drivers)

**Virtual Machines** (6 test VMs):
- web-server-rhel8: RHEL 8, UEFI, 4 vCPUs, 8 GB
- db-server-rhel9: RHEL 9, UEFI, 8 vCPUs, 16 GB, 2 disks
- win2022-app-server: Windows 2022, UEFI, 8 vCPUs, 32 GB, 2 NICs
- ubuntu-test-vm: Ubuntu 22.04, BIOS, 2 vCPUs, 4 GB
- powered-off-vm: Generic, UEFI, OFF state
- secure-boot-vm: Generic, Secure Boot, 4 vCPUs, 8 GB

**Location**: `pkg/controller/provider/container/nutanix/testdata/`

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-12 | Platform Team | Initial draft for community review |

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | TBD | | |
| Technical Lead | TBD | | |
| Security Review | TBD | | |
| Documentation | TBD | | |

---

**Next Steps**:
1. Community review and feedback (2 weeks)
2. Finalize requirements based on feedback
3. Begin Phase 1 implementation
4. Regular status updates to community

**Feedback**: Please provide feedback via GitHub issues or community forums.
