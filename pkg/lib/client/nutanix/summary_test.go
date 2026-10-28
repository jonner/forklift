package nutanix

import "testing"

func TestRecordAPIStatClassifies(t *testing.T) {
	// isolate from any other test / process state
	apiAggMu.Lock()
	apiAgg = map[apiStatKey]*apiStat{}
	apiAggMu.Unlock()

	rec := func(code string, ra float64) {
		recordAPIStat("adapter", "GET", "/api/vmm/v4.0/content/images", code, 0.1, ra)
	}
	rec("200", -1)
	rec("200", -1)
	rec("429", 2)
	rec("503", 5)
	rec("404", -1)
	rec("error", -1)

	apiAggMu.Lock()
	s := apiAgg[apiStatKey{"adapter", "GET", "/api/vmm/v4.0/content/images"}]
	apiAggMu.Unlock()
	if s == nil {
		t.Fatal("no stat recorded")
	}
	if s.count != 6 || s.c2xx != 2 || s.c429 != 1 || s.c503 != 1 || s.c4xx != 1 || s.cErr != 1 {
		t.Fatalf("unexpected counts: %+v", *s)
	}
	if s.retryAfterCount != 2 || s.retryAfterMax != 5 {
		t.Fatalf("unexpected retry-after: count=%d max=%v", s.retryAfterCount, s.retryAfterMax)
	}
}
