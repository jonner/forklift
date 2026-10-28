package nutanix

import (
	"fmt"
	"os"
	"sort"
	"strconv"
	"sync"
	"time"
)

// In-process request aggregation + periodic summary output. This is the
// low-ceremony alternative to scraping Prometheus: the controller prints a
// human-readable per-endpoint load/429 table to its log, so a single migration
// can be profiled from `kubectl logs` alone (deploy image, run one migration,
// collect the controller log). Aggregates are cumulative since process start,
// so restart the controller before the run (deploying the image does that) to
// scope the numbers to the test migration.
//
// On this diagnostic build it defaults ON to minimize operator steps; set
// NUTANIX_API_SUMMARY=false to disable. (When promoted upstream this should
// flip back to opt-in.)

// summaryEnabled toggles aggregation + periodic logging. Default on; disable
// with NUTANIX_API_SUMMARY=false.
var summaryEnabled = func() bool {
	v, ok := os.LookupEnv("NUTANIX_API_SUMMARY")
	if !ok {
		return true
	}
	enabled, err := strconv.ParseBool(v)
	if err != nil {
		return true
	}
	return enabled
}()

// summaryInterval is how often the summary is written (env
// NUTANIX_API_SUMMARY_INTERVAL, Go duration; default 60s).
var summaryInterval = func() time.Duration {
	if d, err := time.ParseDuration(os.Getenv("NUTANIX_API_SUMMARY_INTERVAL")); err == nil && d > 0 {
		return d
	}
	return 60 * time.Second
}()

type apiStatKey struct{ subsystem, method, endpoint string }

type apiStat struct {
	count, c2xx, c3xx, c4xx, c429, c503, c5xx, cErr int64
	maxMs                                           float64
	durs                                            []float64 // capped latency sample (ms)
	retryAfterCount                                 int64
	retryAfterMax                                   float64
}

// maxDurSamples caps per-endpoint latency samples kept for percentiles.
const maxDurSamples = 4096

var (
	apiAggMu    sync.Mutex
	apiAgg      = map[apiStatKey]*apiStat{}
	apiAggStart = time.Now()
)

// recordAPIStat accumulates one physical request attempt. retryAfterSeconds < 0
// means none to record.
func recordAPIStat(subsystem, method, endpoint, code string, durSeconds, retryAfterSeconds float64) {
	ms := durSeconds * 1000
	apiAggMu.Lock()
	defer apiAggMu.Unlock()
	k := apiStatKey{subsystem, method, endpoint}
	s := apiAgg[k]
	if s == nil {
		s = &apiStat{}
		apiAgg[k] = s
	}
	s.count++
	if ms > s.maxMs {
		s.maxMs = ms
	}
	if len(s.durs) < maxDurSamples {
		s.durs = append(s.durs, ms)
	}
	n, _ := strconv.Atoi(code)
	switch {
	case code == "error":
		s.cErr++
	case n >= 200 && n < 300:
		s.c2xx++
	case n >= 300 && n < 400:
		s.c3xx++
	case n == 429:
		s.c429++
	case n == 503:
		s.c503++
	case n >= 400 && n < 500:
		s.c4xx++
	case n >= 500:
		s.c5xx++
	}
	if retryAfterSeconds >= 0 {
		s.retryAfterCount++
		if retryAfterSeconds > s.retryAfterMax {
			s.retryAfterMax = retryAfterSeconds
		}
	}
}

func percentileMs(samples []float64, p float64) float64 {
	if len(samples) == 0 {
		return 0
	}
	cp := append([]float64(nil), samples...)
	sort.Float64s(cp)
	return cp[int(p/100*float64(len(cp)-1))]
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "~"
}

// writeAPISummary prints the aggregate as a bracketed, human-readable table,
// written directly (not through the structured logger) so it stays legible in
// `kubectl logs` under any log encoder.
func writeAPISummary(w *os.File) {
	type row struct {
		k        apiStatKey
		s        apiStat
		p50, p95 float64
	}
	apiAggMu.Lock()
	rows := make([]row, 0, len(apiAgg))
	var total, total429, total503, totalErr int64
	var maxRA float64
	for k, s := range apiAgg {
		rows = append(rows, row{k, *s, percentileMs(s.durs, 50), percentileMs(s.durs, 95)})
		total += s.count
		total429 += s.c429
		total503 += s.c503
		totalErr += s.cErr
		if s.retryAfterMax > maxRA {
			maxRA = s.retryAfterMax
		}
	}
	elapsed := time.Since(apiAggStart)
	apiAggMu.Unlock()

	sort.Slice(rows, func(i, j int) bool { return rows[i].s.count > rows[j].s.count })

	fmt.Fprintf(w, "=== Nutanix API summary (elapsed %s) ===\n", elapsed.Round(time.Second))
	fmt.Fprintf(w, "%-10s %-6s %-40s %7s %5s %5s %5s %5s %5s %5s %5s %7s %7s %7s\n",
		"subsystem", "method", "endpoint", "count", "2xx", "3xx", "429", "503", "4xx", "5xx", "err",
		"p50ms", "p95ms", "maxms")
	for _, r := range rows {
		fmt.Fprintf(w, "%-10s %-6s %-40s %7d %5d %5d %5d %5d %5d %5d %5d %7.0f %7.0f %7.0f\n",
			r.k.subsystem, r.k.method, truncate(r.k.endpoint, 40),
			r.s.count, r.s.c2xx, r.s.c3xx, r.s.c429, r.s.c503, r.s.c4xx, r.s.c5xx, r.s.cErr,
			r.p50, r.p95, r.s.maxMs)
	}
	pct429 := 0.0
	if total > 0 {
		pct429 = 100 * float64(total429) / float64(total)
	}
	fmt.Fprintf(w, "totals: %d requests, %d x 429 (%.1f%%), %d x 503, %d transport-errors, max Retry-After %.0fs\n",
		total, total429, pct429, total503, totalErr, maxRA)
	fmt.Fprintln(w, "=== end Nutanix API summary ===")
}

// StartSummaryLogger starts periodic summary output when NUTANIX_API_SUMMARY is
// enabled; otherwise it is a no-op. Call once at startup.
func StartSummaryLogger() {
	if !summaryEnabled {
		return
	}
	go func() {
		t := time.NewTicker(summaryInterval)
		defer t.Stop()
		for range t.C {
			writeAPISummary(os.Stderr)
		}
	}()
}
