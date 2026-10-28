package nutanix

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/kubev2v/forklift/pkg/lib/logging"
)

func TestNormalizePath(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"list endpoint unchanged", "/api/nutanix/v3/vms/list", "/api/nutanix/v3/vms/list"},
		{"uuid segment", "/api/nutanix/v3/vms/6c3d1b7e-1a2b-4c3d-9e8f-0a1b2c3d4e5f", "/api/nutanix/v3/vms/{id}"},
		{"uuid with trailing route", "/api/nutanix/v3/images/6c3d1b7e-1a2b-4c3d-9e8f-0a1b2c3d4e5f/file", "/api/nutanix/v3/images/{id}/file"},
		{"numeric segment", "/PrismGateway/services/rest/v2.0/vms/12345/set_power_state", "/PrismGateway/services/rest/v2.0/vms/{id}/set_power_state"},
		{"version segment kept", "/api/vmm/v4.0/content/images", "/api/vmm/v4.0/content/images"},
		{"prism_central kept", "/api/nutanix/v3/prism_central", "/api/nutanix/v3/prism_central"},
		{"multiple ids", "/a/11111111-2222-3333-4444-555555555555/b/42", "/a/{id}/b/{id}"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := normalizePath(c.in); got != c.want {
				t.Fatalf("normalizePath(%q) = %q, want %q", c.in, got, c.want)
			}
		})
	}
}

// TestMeteredRoundTripperRecords verifies the hook fires once per attempt with
// the expected labels, and that Retry-After is reported only on 429/503.
func TestMeteredRoundTripperRecords(t *testing.T) {
	type sample struct {
		subsystem, method, endpoint, code string
		retryAfter                        float64
	}
	var got []sample

	orig := RecordRequest
	RecordRequest = func(subsystem, method, endpoint, code string, _, retryAfter float64) {
		got = append(got, sample{subsystem, method, endpoint, code, retryAfter})
	}
	defer func() { RecordRequest = orig }()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/limited" {
			w.Header().Set("Retry-After", "7")
			w.WriteHeader(http.StatusTooManyRequests)
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	rt := &meteredRoundTripper{
		next:      http.DefaultTransport,
		subsystem: "adapter",
		log:       logging.WithName("test"),
	}
	client := &http.Client{Transport: rt}

	// 200 OK: no Retry-After (negative sentinel).
	resp, err := client.Get(server.URL + "/api/nutanix/v3/vms/6c3d1b7e-1a2b-4c3d-9e8f-0a1b2c3d4e5f")
	if err != nil {
		t.Fatalf("GET failed: %v", err)
	}
	_ = resp.Body.Close()

	// 429: Retry-After=7 reported.
	resp, err = client.Get(server.URL + "/limited")
	if err != nil {
		t.Fatalf("GET failed: %v", err)
	}
	_ = resp.Body.Close()

	if len(got) != 2 {
		t.Fatalf("expected 2 recorded attempts, got %d: %+v", len(got), got)
	}
	ok := got[0]
	if ok.subsystem != "adapter" || ok.method != http.MethodGet ||
		ok.endpoint != "/api/nutanix/v3/vms/{id}" || ok.code != "200" || ok.retryAfter != -1 {
		t.Fatalf("unexpected 200 sample: %+v", ok)
	}
	limited := got[1]
	if limited.endpoint != "/limited" || limited.code != "429" || limited.retryAfter != 7 {
		t.Fatalf("unexpected 429 sample: %+v", limited)
	}
}
