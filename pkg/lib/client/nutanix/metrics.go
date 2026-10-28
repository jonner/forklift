package nutanix

import (
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/kubev2v/forklift/pkg/lib/logging"
)

// RecordRequest, when non-nil, is invoked once per physical HTTP attempt to
// Prism -- including each 429/503 retry, since the retry loops in send() and
// GetNoRedirect() sit above the transport this hook lives in. Arguments are
// bounded-cardinality metric data: subsystem (collector|adapter|builder),
// method, a normalized endpoint template (see normalizePath), and the status
// code as a string ("error" on transport failure). retryAfterSeconds is the
// parsed Retry-After value for 429/503 responses, or a negative value when
// there is nothing to record.
//
// cmd/forklift-controller wires this to the Prometheus recorder. It is left
// nil in unit tests and standalone tools so this package keeps no dependency
// on the monitoring/controller tree.
var RecordRequest func(subsystem, method, endpoint, code string, durationSeconds, retryAfterSeconds float64)

// httpTrace reports whether per-request HTTP tracing is enabled. Toggled by
// the NUTANIX_HTTP_TRACE env var (e.g. "1"/"true"), parsed once at init so a
// production diagnosis can turn on detailed per-request logging without
// raising the global LOG_LEVEL. Overridable in tests (same package).
var httpTrace = func() bool {
	v, _ := strconv.ParseBool(os.Getenv("NUTANIX_HTTP_TRACE"))
	return v
}()

// uuidSegment matches a canonical UUID path segment (e.g. a VM or image id).
var uuidSegment = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

// numericSegment matches an all-numeric path segment.
var numericSegment = regexp.MustCompile(`^[0-9]+$`)

// normalizePath reduces a request path to a bounded-cardinality template
// suitable for a Prometheus label: the query string is dropped and any UUID
// or all-numeric segment is replaced with "{id}". Literal route words and
// version segments (v3, v4.0, list, file, prism_central, ...) are kept, so
// e.g. /api/nutanix/v3/vms/<uuid> -> /api/nutanix/v3/vms/{id}.
func normalizePath(path string) string {
	segments := strings.Split(path, "/")
	for i, seg := range segments {
		if uuidSegment.MatchString(seg) || numericSegment.MatchString(seg) {
			segments[i] = "{id}"
		}
	}
	return strings.Join(segments, "/")
}

// meteredRoundTripper wraps the Nutanix HTTP transport to record one metric
// sample (and optional trace log) per physical request attempt. It does not
// read or close the response body -- callers in send()/GetNoRedirect() still
// own decoding.
type meteredRoundTripper struct {
	next      http.RoundTripper
	subsystem string
	log       logging.LevelLogger
}

func (rt *meteredRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
	start := time.Now()
	endpoint := normalizePath(req.URL.Path)

	resp, err := rt.next.RoundTrip(req)
	dur := time.Since(start).Seconds()

	code := "error"
	retryAfter := -1.0
	var rawRetryAfter string
	if resp != nil {
		code = strconv.Itoa(resp.StatusCode)
		if retryableStatus(resp.StatusCode) {
			rawRetryAfter = resp.Header.Get("Retry-After")
			if secs, convErr := strconv.Atoi(rawRetryAfter); convErr == nil && secs >= 0 {
				retryAfter = float64(secs)
			}
		}
	}

	if RecordRequest != nil {
		RecordRequest(rt.subsystem, req.Method, endpoint, code, dur, retryAfter)
	}

	rt.trace(req, endpoint, code, dur, rawRetryAfter, resp)

	return resp, err
}

// trace emits a per-request log line. 429/503 responses are always logged so
// rate-limit events surface without full tracing; every other request is
// logged only when NUTANIX_HTTP_TRACE is enabled.
func (rt *meteredRoundTripper) trace(req *http.Request, endpoint, code string, dur float64, rawRetryAfter string, resp *http.Response) {
	if rt.log == nil {
		return
	}
	rateLimited := resp != nil && retryableStatus(resp.StatusCode)
	if !httpTrace && !rateLimited {
		return
	}
	rt.log.Info("Nutanix HTTP request",
		"subsystem", rt.subsystem,
		"method", req.Method,
		"endpoint", endpoint,
		"path", req.URL.Path,
		"status", code,
		"durationMs", dur*1000,
		"retryAfter", rawRetryAfter,
	)
}
