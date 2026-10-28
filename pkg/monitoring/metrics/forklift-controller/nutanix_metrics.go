package forklift_controller

import (
	"sync"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Nutanix Prism API instrumentation. These metrics quantify the HTTP traffic
// forklift directs at Prism during migrations so 429 (rate-limit) pressure can
// be attributed to a subsystem and endpoint. Labels are deliberately
// low-cardinality; per-request detail (VM/phase/UUID) is left to the gated
// NUTANIX_HTTP_TRACE logs, not labels.
var (
	// 'subsystem' - [ collector, adapter, builder, unknown ]
	// 'method'    - [ GET, POST, PUT, DELETE ]
	// 'endpoint'  - normalized path template (UUIDs/numeric ids -> {id})
	// 'code'      - HTTP status as string, or "error" on transport failure
	nutanixRequestsCounter = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "mtv_nutanix_requests_total",
		Help: "Nutanix Prism HTTP request attempts (incl. each 429/503 retry) by subsystem, method, endpoint and status code",
	},
		[]string{"subsystem", "method", "endpoint", "code"},
	)

	// Time to response headers per request attempt.
	nutanixRequestDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "mtv_nutanix_request_duration_seconds",
		Help:    "Nutanix Prism HTTP request latency (time to response headers) by subsystem, method and endpoint",
		Buckets: prometheus.DefBuckets,
	},
		[]string{"subsystem", "method", "endpoint"},
	)

	// Distribution of Retry-After values Prism returns on 429/503.
	nutanixRetryAfter = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "mtv_nutanix_retry_after_seconds",
		Help:    "Retry-After value (seconds) returned by Prism on 429/503, by subsystem and endpoint",
		Buckets: []float64{0, 1, 2, 5, 10, 30, 60, 120},
	},
		[]string{"subsystem", "endpoint"},
	)

	// CDI import accounting (controller-visible): the bulk disk pull is done by
	// CDI importer pods, which forklift cannot instrument directly; these count
	// what the controller initiates toward Prism. See the instrumentation
	// runbook for out-of-band observation of the importer pods themselves.

	// Approximate number of CDI DataVolumes (≈ importer pods, one per disk)
	// forklift has ensured for Nutanix sources. Counts ensure passes, so it
	// may slightly over-count when a reconcile retries before advancing phase.
	nutanixImporterDataVolumes = promauto.NewCounter(prometheus.CounterOpts{
		Name: "mtv_nutanix_importer_datavolumes_total",
		Help: "CDI DataVolumes ensured for Nutanix sources (approximate importer-pod / Prism-pull initiations)",
	})

	// Successful download-credential (Prism Central cookie) refresh + importer
	// restart events. Each re-runs the v4 redirect/cookie handshake against PC.
	nutanixImportCredentialRefresh = promauto.NewCounter(prometheus.CounterOpts{
		Name: "mtv_nutanix_import_credential_refresh_total",
		Help: "CDI importer download-credential refreshes for Nutanix (each re-runs the Prism Central redirect handshake)",
	})

	// Terminal CDI importer failures classified by cause, deduplicated per
	// importer pod. 'cause' = rate_limit (HTTP 429/503) | auth (401) | other.
	// Note: 'rate_limit' only captures failures whose message matches the
	// rate-limit detector; nbdkit-phase 429s may fall into 'other' (see the
	// MTV-7141 instrumentation runbook).
	nutanixImporterFailures = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "mtv_nutanix_importer_failures_total",
		Help: "Terminal CDI importer failures for Nutanix by classified cause, deduplicated per importer pod",
	},
		[]string{"cause"},
	)
)

// nutanixSeenFailedImporters deduplicates importer-failure counting: the
// failure block runs every reconcile while a pod stays failed, so count each
// pod UID once.
var nutanixSeenFailedImporters sync.Map

// RecordNutanixRequest records one Prism HTTP request attempt. It matches the
// pkg/lib/client/nutanix RecordRequest hook signature and is wired up from
// cmd/forklift-controller. retryAfterSeconds < 0 means there is nothing to
// record (no Retry-After / not a 429/503).
func RecordNutanixRequest(subsystem, method, endpoint, code string, durationSeconds, retryAfterSeconds float64) {
	nutanixRequestsCounter.With(prometheus.Labels{
		"subsystem": subsystem, "method": method, "endpoint": endpoint, "code": code,
	}).Inc()
	nutanixRequestDuration.With(prometheus.Labels{
		"subsystem": subsystem, "method": method, "endpoint": endpoint,
	}).Observe(durationSeconds)
	if retryAfterSeconds >= 0 {
		nutanixRetryAfter.With(prometheus.Labels{
			"subsystem": subsystem, "endpoint": endpoint,
		}).Observe(retryAfterSeconds)
	}
}

// RecordNutanixImporterDataVolumes adds n ensured DataVolumes to the counter.
func RecordNutanixImporterDataVolumes(n int) {
	if n > 0 {
		nutanixImporterDataVolumes.Add(float64(n))
	}
}

// RecordNutanixImportCredentialRefresh records one successful importer
// credential refresh + restart.
func RecordNutanixImportCredentialRefresh() {
	nutanixImportCredentialRefresh.Inc()
}

// RecordNutanixImporterFailure records one terminal importer failure, counting
// each importer pod once (keyed by podUID). cause is rate_limit|auth|other.
func RecordNutanixImporterFailure(podUID, cause string) {
	if podUID != "" {
		if _, seen := nutanixSeenFailedImporters.LoadOrStore(podUID, struct{}{}); seen {
			return
		}
	}
	nutanixImporterFailures.With(prometheus.Labels{"cause": cause}).Inc()
}
