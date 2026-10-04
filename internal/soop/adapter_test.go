package soop

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"net/url"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/integrated-recorder/adapter-sdk-go/adaptertest"
	"github.com/integrated-recorder/adapter-sdk-go/protocol"
)

func TestDescriptorAndSDKProtocol(t *testing.T) {
	adapter := NewAdapter()
	if err := adaptertest.ValidateAdapter(adapter); err != nil {
		t.Fatalf("SDK rejected adapter descriptor: %v", err)
	}
	responses, err := adaptertest.ServeRoundTrip(context.Background(), adapter,
		protocol.Request{ProtocolVersion: protocol.Version, ID: "describe", Method: protocol.MethodDescribe},
		protocol.Request{ProtocolVersion: protocol.Version, ID: "unknown", Method: "not_a_method"},
	)
	if err != nil {
		t.Fatalf("SDK protocol round trip failed: %v", err)
	}
	if len(responses) != 3 || responses[0].Error != nil || responses[1].Error == nil {
		t.Fatal("SDK protocol responses did not include describe, structured unknown-method error, and shutdown")
	}
	var descriptor protocol.Descriptor
	if err := json.Unmarshal(responses[0].Result, &descriptor); err != nil {
		t.Fatalf("could not decode descriptor: %v", err)
	}
	want := []string{"resolve", "watch", "metadata", "refresh"}
	if strings.Join(descriptor.Capabilities, ",") != strings.Join(want, ",") || strings.Join(descriptor.MediaTypes, ",") != "hls" {
		t.Fatal("descriptor capabilities or media types were not exact")
	}
}

func TestWatchExplicitLegacyAndOfflineResults(t *testing.T) {
	tests := []struct {
		name    string
		channel func(string) map[string]any
		want    string
	}{
		{name: "explicit live result", channel: func(host string) map[string]any { return liveChannel(host, 1, true, false) }, want: "live"},
		{name: "legacy live markers without result", channel: func(host string) map[string]any {
			value := liveChannel(host, 1, true, false)
			delete(value, "RESULT")
			return value
		}, want: "live"},
		{name: "explicit offline result", channel: func(_ string) map[string]any { return map[string]any{"RESULT": 0} }, want: "offline"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
				switch r.URL.Path {
				case "/api":
					_ = r.ParseForm()
					if r.Form.Get("type") == "aid" {
						writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 1, "AID": "watch-aid"}})
						return
					}
					writeJSON(w, map[string]any{"CHANNEL": test.channel(serverURLFromRequest(r))})
				case "/broad_stream_assign.html":
					writeJSON(w, map[string]any{"view_url": serverURLFromRequest(r) + "/manifest.m3u8"})
				default:
					http.NotFound(w, r)
				}
			})
			defer server.Close()
			result, err := adapter.WatchCheck(context.Background(), protocol.WatchCheckParams{Input: raw(`{"channel":"streamer"}`)})
			if err != nil {
				t.Fatalf("watch returned an error: %v", err)
			}
			if result.State != test.want {
				t.Fatalf("watch state was not %q", test.want)
			}
			if result.State == "live" && (result.SessionRef != "soop:streamer:24680" || result.Media == nil) {
				t.Fatal("live watch result lacked stable broadcast identity or media")
			}
		})
	}
}

func TestLiveWithoutBroadcastNumberUsesCanonicalPageFallback(t *testing.T) {
	var liveCalls int
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api":
			_ = r.ParseForm()
			if r.Form.Get("type") != "live" {
				t.Error("BNO fallback should only request live info")
				return
			}
			liveCalls++
			if liveCalls == 1 {
				if r.Form.Get("bno") != "" {
					t.Error("initial live lookup unexpectedly had a broadcast number")
				}
				channel := liveChannel(serverURLFromRequest(r), 1, true, false)
				delete(channel, "BNO")
				writeJSON(w, map[string]any{"CHANNEL": channel})
				return
			}
			if r.Form.Get("bno") != "77777" {
				t.Error("page-derived broadcast number was not used on the second API request")
			}
			channel := liveChannel(serverURLFromRequest(r), 1, true, false)
			channel["BNO"] = "77777"
			writeJSON(w, map[string]any{"CHANNEL": channel})
		case "/play/streamer":
			_, _ = w.Write([]byte(`<script>window.nBroadNo = "77777";</script>`))
		default:
			http.NotFound(w, r)
		}
	})
	defer server.Close()
	info, offline, err := adapter.client.lookupLive(context.Background(), ChannelInput{LoginID: "streamer"}, accountCredentials{})
	if err != nil || offline || info.BroadcastNo != "77777" || liveCalls != 2 {
		t.Fatal("live-info lookup did not use the canonical page BNO fallback")
	}
}

func TestWatchErrorsAreNotOffline(t *testing.T) {
	tests := []struct {
		name     string
		handler  func(http.ResponseWriter, *http.Request)
		deadline bool
	}{
		{name: "malformed JSON", handler: func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("not-json")) }},
		{name: "unexpected result", handler: func(w http.ResponseWriter, _ *http.Request) {
			writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 7}})
		}},
		{name: "server error", handler: func(w http.ResponseWriter, _ *http.Request) {
			http.Error(w, "private upstream response", http.StatusBadGateway)
		}},
		{name: "request timeout", deadline: true, handler: func(w http.ResponseWriter, _ *http.Request) {
			time.Sleep(80 * time.Millisecond)
			writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 0}})
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path == "/api" {
					test.handler(w, r)
					return
				}
				http.NotFound(w, r)
			})
			defer server.Close()
			ctx := context.Background()
			cancel := func() {}
			if test.deadline {
				ctx, cancel = context.WithTimeout(ctx, 10*time.Millisecond)
			}
			defer cancel()
			result, err := adapter.WatchCheck(ctx, protocol.WatchCheckParams{Input: raw(`{"channel":"streamer"}`)})
			if err == nil || result.State == "offline" {
				t.Fatal("platform failure was incorrectly treated as offline")
			}
		})
	}
}

func TestLoginCookieAndRequestForms(t *testing.T) {
	var liveCalls, loginCalls, aidCalls int
	var sawCookie bool
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api":
			if r.Method != http.MethodPost || !strings.HasPrefix(r.Header.Get("Content-Type"), "application/x-www-form-urlencoded") || r.Header.Get("Referer") != playerReferer || r.Header.Get("Origin") == "" || r.Header.Get("User-Agent") != stableUserAgent {
				t.Error("player API request headers or method were incorrect")
			}
			if err := r.ParseForm(); err != nil {
				t.Error("player API form was malformed")
			}
			for key, value := range map[string]string{"from_api": "0", "mode": "landing", "player_type": "html5", "stream_type": "common", "bid": "streamer"} {
				if r.Form.Get(key) != value {
					t.Errorf("live request omitted required field %s", key)
				}
			}
			switch r.Form.Get("type") {
			case "live":
				liveCalls++
				if r.Form.Get("pwd") != "" {
					t.Error("stream password was sent to the live-info request")
				}
				if liveCalls == 1 {
					writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": -6}})
					return
				}
				for _, cookie := range r.Cookies() {
					if cookie.Name == "soop_login" && cookie.Value == "yes" {
						sawCookie = true
					}
				}
				if !sawCookie {
					t.Error("login cookie was not reused for API retry")
				}
				writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, true)})
			case "aid":
				aidCalls++
				if r.Form.Get("bno") != "24680" || r.Form.Get("quality") != "hd" || r.Form.Get("pwd") != "password-marker" {
					t.Error("AID form did not contain the requested broadcast, preset, and password")
				}
				writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 1, "AID": "aid-value"}})
			default:
				t.Error("unexpected player API request type")
				writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 1}})
			}
		case "/login":
			loginCalls++
			if err := r.ParseForm(); err != nil {
				t.Error("login form was malformed")
			}
			want := map[string]string{"szWork": "login", "szType": "json", "szUid": "account", "szPassword": "account-secret", "isSaveId": "true", "isSavePw": "false", "isSaveJoin": "false", "isLoginRetain": "Y"}
			for key, value := range want {
				if r.Form.Get(key) != value {
					t.Errorf("login request omitted required field %s", key)
				}
			}
			http.SetCookie(w, &http.Cookie{Name: "soop_login", Value: "yes", Path: "/"})
			writeJSON(w, map[string]any{"RESULT": 1})
		case "/broad_stream_assign.html":
			if r.URL.Query().Get("return_type") != "gs_cdn_pc_web" || r.URL.Query().Get("broad_key") != "24680-common-hd-hls" {
				t.Error("CDN assignment query did not use mapped return type and broadcast key")
			}
			writeJSON(w, map[string]any{"view_url": serverURLFromRequest(r) + "/manifest.m3u8?token=keep&aid=old"})
		default:
			http.NotFound(w, r)
		}
	})
	defer server.Close()
	result, err := adapter.Resolve(context.Background(), protocol.ResolveParams{
		Input:         raw(`{"channel":"streamer","stream_password":"password-marker"}`),
		Configuration: map[string]json.RawMessage{"quality": raw(`"hd"`)},
		Secrets:       map[string]string{"account_username": "account", "account_password": "account-secret"},
	})
	if err != nil {
		t.Fatalf("resolve failed: %v", err)
	}
	if liveCalls != 2 || loginCalls != 1 || aidCalls != 1 || !sawCookie {
		t.Fatal("login or API retry counts were incorrect")
	}
	manifest, err := url.Parse(result.Media.ManifestURL)
	if err != nil || manifest.Query().Get("aid") != "aid-value" || manifest.Query().Get("token") != "keep" || manifest.Query().Get("aaid") != "" {
		t.Fatal("resolved manifest did not preserve URL query and replace the AID parameter")
	}
	if len(result.State) != 1 || result.State[0].Secrets["soop:streamer:24680:stream_password"] != "password-marker" || result.State[0].Secrets["soop:streamer:24680:account_username"] != "account" {
		t.Fatal("refresh secret state was not scoped to the SOOP broadcast")
	}
	if strings.Contains(string(result.Media.Metadata), "password-marker") || strings.Contains(string(result.Media.Metadata), "account-secret") || strings.Contains(string(result.Media.Metadata), "aid-value") {
		t.Fatal("source metadata contained a secret or signed AID")
	}
	if result.Media.SessionRef != "soop:streamer:24680" || result.Media.ArchivePolicy == nil || result.Media.ArchivePolicy.SourceURI != "sensitive" || result.Media.RefreshPolicy == nil || strings.Join(intsToStrings(result.Media.RefreshPolicy.OnHTTPStatus), ",") != "401,403" {
		t.Fatal("resolved media policy or stable session reference was incorrect")
	}
}

func TestQualitySelectionAndCDNMapping(t *testing.T) {
	presets := []preset{{Name: "sd", Label: "SD"}, {Name: "hd", Label: "HD"}, {Name: "hd4k", Label: "4K"}, {Name: "original", Label: "Original"}, {Name: "auto", Label: "Auto"}}
	for _, test := range []struct{ quality, want string }{{"best", "original"}, {"worst", "sd"}, {"HD", "hd"}, {"4k", "hd4k"}} {
		got, err := choosePreset(presets, test.quality)
		if err != nil || got.Name != test.want {
			t.Fatalf("quality %q did not select its expected preset", test.quality)
		}
	}
	if _, err := choosePreset([]preset{{Name: "auto", Label: "auto"}}, "best"); err == nil {
		t.Fatal("auto was accepted as a selectable preset")
	}
	for _, test := range []struct{ cdn, want string }{{"gs_cdn", "gs_cdn_pc_web"}, {"lg_cdn", "lg_cdn_pc_web"}} {
		adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path == "/broad_stream_assign.html" {
				if r.URL.Query().Get("return_type") != test.want || r.URL.Query().Get("broad_key") != "24680-common-hd-hls" {
					t.Error("CDN type mapping or HLS broad key was incorrect")
				}
				writeJSON(w, map[string]any{"view_url": serverURLFromRequest(r) + "/manifest.m3u8"})
				return
			}
			http.NotFound(w, r)
		})
		defer server.Close()
		info := liveInfo{LoginID: "streamer", BroadcastNo: "24680", RMD: server.URL, CDN: test.cdn, Presets: presets}
		if _, err := adapter.client.assignViewURL(context.Background(), info, "hd", "AID"); err != nil {
			t.Fatalf("CDN assignment failed for %s", test.cdn)
		}
	}
}

func TestRefreshRegeneratesManifestAndMetadataOnlyReturnsKnownTitle(t *testing.T) {
	var aidSequence int
	var seenRefreshPassword string
	var liveCalls int
	var loginCalls int
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api":
			_ = r.ParseForm()
			switch r.Form.Get("type") {
			case "live":
				liveCalls++
				if liveCalls == 2 && len(r.Cookies()) == 0 {
					writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": -6}})
					return
				}
				writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, true)})
			case "aid":
				aidSequence++
				if r.Form.Get("pwd") != "refresh-password" {
					t.Error("refresh did not recover the protected stream password from state")
				}
				seenRefreshPassword = r.Form.Get("pwd")
				writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 1, "AID": "aid-" + strconvItoa(aidSequence)}})
			}
		case "/broad_stream_assign.html":
			writeJSON(w, map[string]any{"view_url": serverURLFromRequest(r) + "/manifest.m3u8?aid=previous"})
		case "/login":
			loginCalls++
			_ = r.ParseForm()
			if r.Form.Get("szUid") != "stored-account" || r.Form.Get("szPassword") != "stored-account-password" {
				t.Error("refresh did not recover account credentials from secret state")
			}
			http.SetCookie(w, &http.Cookie{Name: "soop_login", Value: "yes", Path: "/"})
			writeJSON(w, map[string]any{"RESULT": 1})
		default:
			http.NotFound(w, r)
		}
	})
	defer server.Close()
	resolved, err := adapter.Resolve(context.Background(), protocol.ResolveParams{
		Input:   raw(`{"channel":"streamer","stream_password":"refresh-password"}`),
		Secrets: map[string]string{"account_username": "stored-account", "account_password": "stored-account-password"},
	})
	if err != nil {
		t.Fatalf("initial resolve failed: %v", err)
	}
	originalMetadata := append(json.RawMessage(nil), resolved.Media.Metadata...)
	state := []protocol.StateDocument{{Secrets: resolved.State[0].Secrets}}
	// Simulate a process restart: cookies are process-local, while secret state persists.
	jar, _ := cookiejar.New(nil)
	adapter.client.http.Jar = jar
	refreshed, err := adapter.Refresh(context.Background(), protocol.RefreshParams{Current: resolved.Media, State: state})
	if err != nil {
		t.Fatalf("refresh failed: %v", err)
	}
	if refreshed.Media.ManifestURL == resolved.Media.ManifestURL || !strings.Contains(refreshed.Media.ManifestURL, "aid-2") || seenRefreshPassword != "refresh-password" {
		t.Fatal("refresh did not produce a fresh manifest using the recovered stream password")
	}
	if refreshed.Media.SessionRef != resolved.Media.SessionRef || string(refreshed.Media.Metadata) != string(originalMetadata) || refreshed.Media.RefreshPolicy == nil || strings.Join(intsToStrings(refreshed.Media.RefreshPolicy.OnHTTPStatus), ",") != "401,403" {
		t.Fatal("refresh changed broadcast identity or stable source metadata")
	}
	if strings.Contains(string(refreshed.Media.Metadata), "refresh-password") || strings.Contains(string(refreshed.Media.Metadata), "aid-2") {
		t.Fatal("refreshed source metadata included secret data")
	}
	metadata, err := adapter.Metadata(context.Background(), protocol.MetadataParams{Current: refreshed.Media})
	if err != nil {
		t.Fatalf("metadata lookup failed: %v", err)
	}
	if metadata.Metadata.Title == nil || *metadata.Metadata.Title != "SOOP title" || metadata.Metadata.Description != nil || liveCalls != 4 || loginCalls != 1 {
		t.Fatal("metadata did not return only the currently known title")
	}
}

func TestRefreshWithoutRequiredSecretStateReturnsActionableError(t *testing.T) {
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api" {
			writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, true)})
			return
		}
		http.NotFound(w, r)
	})
	defer server.Close()
	current := protocol.MediaSource{Type: "hls", SessionRef: "soop:streamer:24680", Metadata: raw(`{"channel":"streamer","bno":"24680","quality":"hd"}`)}
	if _, err := adapter.Refresh(context.Background(), protocol.RefreshParams{Current: current}); err == nil || !hasErrorCode(err, "refresh_state_missing") {
		t.Fatal("refresh without protected-stream secret state did not return an actionable error")
	}
}

func TestMetadataRejectsChangedBroadcastIdentity(t *testing.T) {
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api" {
			writeJSON(w, map[string]any{"CHANNEL": map[string]any{
				"RESULT":     1,
				"BNO":        "99999",
				"TITLE":      "A different broadcast",
				"RMD":        serverURLFromRequest(r),
				"CDN":        "gs_cdn",
				"VIEWPRESET": []string{"hd"},
			}})
			return
		}
		http.NotFound(w, r)
	})
	defer server.Close()
	current := protocol.MediaSource{Type: "hls", SessionRef: "soop:streamer:24680", Metadata: raw(`{"channel":"streamer","bno":"24680","quality":"hd"}`)}
	if _, err := adapter.Metadata(context.Background(), protocol.MetadataParams{Current: current}); err == nil || !hasErrorCode(err, "broadcast_changed") {
		t.Fatal("metadata from a different SOOP broadcast was accepted")
	}
}

func TestInputAndConfigurationErrorsAreStructured(t *testing.T) {
	adapter := NewAdapter()
	_, err := adapter.Resolve(context.Background(), protocol.ResolveParams{Input: raw(`{"channel":"https://evil.test/a"}`)})
	if err == nil || !hasErrorCode(err, "invalid_input") {
		t.Fatal("invalid input was not rejected with a safe structured error")
	}
	_, err = adapter.Resolve(context.Background(), protocol.ResolveParams{Input: raw(`{"channel":"streamer"}`), Configuration: map[string]json.RawMessage{"quality": raw(`12`)}})
	if err == nil || !hasErrorCode(err, "invalid_configuration") {
		t.Fatal("invalid quality configuration was not rejected safely")
	}
}

func TestLoginRequiredWithoutCredentialsAndFailedLogin(t *testing.T) {
	for _, test := range []struct {
		name            string
		withCredentials bool
	}{
		{name: "no credentials"},
		{name: "failed login", withCredentials: true},
	} {
		t.Run(test.name, func(t *testing.T) {
			adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path == "/api" {
					writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": -6}})
					return
				}
				if r.URL.Path == "/login" {
					writeJSON(w, map[string]any{"RESULT": 0, "message": "private login failure"})
					return
				}
				http.NotFound(w, r)
			})
			defer server.Close()
			params := protocol.ResolveParams{Input: raw(`{"channel":"streamer"}`)}
			if test.withCredentials {
				params.Secrets = map[string]string{"account_username": "user-marker", "account_password": "password-marker"}
			}
			_, err := adapter.Resolve(context.Background(), params)
			if err == nil || !hasErrorCode(err, "authentication_required") {
				t.Fatal("login failure was not reported as a safe authentication error")
			}
		})
	}
}

func TestLoginRedirectIsNotFollowedAndDynamicHostsAreValidated(t *testing.T) {
	stealRequests := 0
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api":
			writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": -6}})
		case "/login":
			http.Redirect(w, r, "http://attacker.invalid/steal", http.StatusFound)
		case "/steal":
			stealRequests++
		default:
			http.NotFound(w, r)
		}
	})
	defer server.Close()
	_, err := adapter.Resolve(context.Background(), protocol.ResolveParams{
		Input:   raw(`{"channel":"streamer"}`),
		Secrets: map[string]string{"account_username": "account", "account_password": "password"},
	})
	if err == nil || !hasErrorCode(err, "authentication_required") || stealRequests != 0 {
		t.Fatal("login redirect was followed or not reported safely")
	}
	production := newPlatformClient()
	for _, test := range []struct {
		url  string
		want bool
	}{
		{url: "https://rmd.sooplive.com", want: true},
		{url: "https://cdn.afreecatv.com/path", want: true},
		{url: "http://rmd.sooplive.com", want: false},
		{url: "https://attacker.invalid", want: false},
	} {
		parsed, parseErr := url.Parse(test.url)
		if parseErr != nil || production.validDynamicURL(parsed) != test.want {
			t.Fatal("dynamic platform URL host validation did not match expected policy")
		}
	}
}

func TestPasswordProtectedBroadcastBehavior(t *testing.T) {
	for _, test := range []struct {
		name     string
		password string
		wantCode string
	}{
		{name: "missing password", wantCode: "stream_password_required"},
		{name: "rejected password", password: "wrong-password", wantCode: "invalid_stream_password"},
	} {
		t.Run(test.name, func(t *testing.T) {
			aidCalls := 0
			adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/api" {
					http.NotFound(w, r)
					return
				}
				_ = r.ParseForm()
				if r.Form.Get("type") == "aid" {
					aidCalls++
					if r.Form.Get("pwd") != test.password {
						t.Error("AID request did not include the supplied stream password")
					}
					writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": -5}})
					return
				}
				writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, true)})
			})
			defer server.Close()
			input := `{"channel":"streamer"}`
			if test.password != "" {
				input = `{"channel":"streamer","stream_password":"wrong-password"}`
			}
			_, err := adapter.Resolve(context.Background(), protocol.ResolveParams{Input: raw(input)})
			if err == nil || !hasErrorCode(err, test.wantCode) {
				t.Fatal("protected broadcast did not return its safe structured error")
			}
			if test.password == "" && aidCalls != 0 || test.password != "" && aidCalls != 1 {
				t.Fatal("AID request count did not match password protection behavior")
			}
		})
	}
}

func TestAIDErrorResultsDoNotMisclassifyPasswords(t *testing.T) {
	for _, test := range []struct {
		name           string
		aidResult      int
		password       string
		passwordNeeded bool
		wantCode       string
	}{
		{name: "password result without BPWD or password", aidResult: -5, wantCode: "stream_password_required"},
		{name: "unrelated error with password protected stream", aidResult: -8, password: "valid-password", passwordNeeded: true, wantCode: "platform_unavailable"},
	} {
		t.Run(test.name, func(t *testing.T) {
			aidCalls := 0
			adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/api" {
					http.NotFound(w, r)
					return
				}
				_ = r.ParseForm()
				if r.Form.Get("type") == "aid" {
					aidCalls++
					writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": test.aidResult}})
					return
				}
				writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, test.passwordNeeded)})
			})
			defer server.Close()
			input := `{"channel":"streamer"}`
			if test.password != "" {
				input = `{"channel":"streamer","stream_password":"valid-password"}`
			}
			_, err := adapter.Resolve(context.Background(), protocol.ResolveParams{Input: raw(input)})
			if err == nil || !hasErrorCode(err, test.wantCode) || aidCalls != 1 {
				t.Fatal("AID result was not classified according to its result code and supplied password")
			}
		})
	}
}

func TestSecretsAndSignedAIDDoNotLeakToProtocolOrStderr(t *testing.T) {
	var liveCalls int
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api":
			_ = r.ParseForm()
			switch r.Form.Get("type") {
			case "live":
				liveCalls++
				if liveCalls == 1 {
					writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": -6}, "private": "account-marker password-marker aid-marker"})
					return
				}
				writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, true)})
			case "aid":
				writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 1, "AID": "aid-marker"}})
			}
		case "/login":
			http.SetCookie(w, &http.Cookie{Name: "soop_login", Value: "yes", Path: "/"})
			writeJSON(w, map[string]any{"RESULT": 1})
		case "/broad_stream_assign.html":
			w.WriteHeader(http.StatusBadGateway)
			_, _ = w.Write([]byte("account-marker password-marker aid-marker"))
		default:
			http.NotFound(w, r)
		}
	})
	defer server.Close()
	oldStderr := os.Stderr
	readEnd, writeEnd, err := os.Pipe()
	if err != nil {
		t.Fatal("could not capture adapter stderr")
	}
	os.Stderr = writeEnd
	defer func() {
		os.Stderr = oldStderr
		_ = writeEnd.Close()
		_ = readEnd.Close()
	}()
	responses, err := adaptertest.ServeRoundTrip(context.Background(), adapter,
		protocol.Request{ProtocolVersion: protocol.Version, ID: "resolve-secret", Method: protocol.MethodResolve, Params: raw(`{"input":{"channel":"streamer","stream_password":"password-marker"},"secrets":{"account_username":"account-marker","account_password":"account-secret-marker"}}`)},
	)
	if err != nil {
		t.Fatalf("protocol round trip failed: %v", err)
	}
	_ = writeEnd.Close()
	os.Stderr = oldStderr
	stderr, _ := io.ReadAll(readEnd)
	_ = readEnd.Close()
	if len(responses) < 1 || responses[0].Error == nil {
		t.Fatal("failed resolve did not return a structured protocol error")
	}
	protocolOutput, err := json.Marshal(responses[0].Error)
	if err != nil {
		t.Fatal("could not inspect adapter protocol output")
	}
	for _, marker := range []string{"account-marker", "account-secret-marker", "password-marker", "aid-marker"} {
		if bytes.Contains(protocolOutput, []byte(marker)) || bytes.Contains(stderr, []byte(marker)) {
			t.Fatal("a secret marker appeared in adapter protocol or stderr output")
		}
	}
}

func TestProtocolResolveCarriesSecretsOnlyInSecretState(t *testing.T) {
	adapter, server := makeFixtureAdapter(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api":
			_ = r.ParseForm()
			if r.Form.Get("type") == "aid" {
				writeJSON(w, map[string]any{"CHANNEL": map[string]any{"RESULT": 1, "AID": "aid-wire-test"}})
				return
			}
			writeJSON(w, map[string]any{"CHANNEL": liveChannel(serverURLFromRequest(r), 1, true, true)})
		case "/broad_stream_assign.html":
			writeJSON(w, map[string]any{"view_url": serverURLFromRequest(r) + "/manifest.m3u8"})
		default:
			http.NotFound(w, r)
		}
	})
	defer server.Close()
	responses, err := adaptertest.ServeRoundTrip(context.Background(), adapter,
		protocol.Request{ProtocolVersion: protocol.Version, ID: "state-result", Method: protocol.MethodResolve, Params: raw(`{"input":{"channel":"streamer","stream_password":"password-wire-test"},"configuration":{"quality":"hd"},"secrets":{"account_username":"account-wire-test","account_password":"account-password-wire-test"}}`)},
	)
	if err != nil {
		t.Fatalf("protocol round trip failed: %v", err)
	}
	if len(responses) < 1 || responses[0].Error != nil {
		t.Fatal("protocol resolve did not return media")
	}
	var result protocol.ResolveResult
	if err := json.Unmarshal(responses[0].Result, &result); err != nil {
		t.Fatal("protocol resolve result was invalid")
	}
	if len(result.State) != 1 || result.State[0].Secrets["soop:streamer:24680:stream_password"] != "password-wire-test" || result.State[0].Secrets["soop:streamer:24680:account_username"] != "account-wire-test" {
		t.Fatal("protocol did not place refresh credentials in the channel-scoped secret state")
	}
	manifest, err := url.Parse(result.Media.ManifestURL)
	if err != nil || manifest.Query().Get("aid") != "aid-wire-test" || manifest.Query().Get("stream_password") != "" || strings.Contains(result.Media.ManifestURL, "password-wire-test") || strings.Contains(result.Media.ManifestURL, "account-wire-test") {
		t.Fatal("media URL did not isolate the signed AID from account and stream passwords")
	}
	if strings.Contains(string(result.Media.Metadata), "password-wire-test") || strings.Contains(string(result.Media.Metadata), "account-wire-test") || strings.Contains(string(result.Media.Metadata), "aid-wire-test") {
		t.Fatal("media metadata contained a secret or AID")
	}
}

func intsToStrings(values []int) []string {
	result := make([]string, len(values))
	for i, value := range values {
		result[i] = strconvItoa(value)
	}
	return result
}

func strconvItoa(value int) string { return strconv.Itoa(value) }

func raw(value string) json.RawMessage { return json.RawMessage(value) }

func makeFixtureAdapter(t *testing.T, handler http.HandlerFunc) (*Adapter, *fixtureServer) {
	t.Helper()
	const fixtureURL = "http://fixture.invalid"
	jar, _ := cookiejar.New(nil)
	httpClient := &http.Client{Transport: handlerTransport{handler: handler}, Timeout: time.Second, Jar: jar}
	client := newPlatformClientForTest(httpClient, endpoints{
		apiURL:        fixtureURL + "/api",
		loginURL:      fixtureURL + "/login",
		playBaseURL:   fixtureURL + "/play",
		testHosts:     map[string]bool{"fixture.invalid": true},
		allowTestHTTP: true,
	})
	return newAdapterForTest(client), &fixtureServer{URL: fixtureURL}
}

type fixtureServer struct{ URL string }

func (*fixtureServer) Close() {}

type handlerTransport struct{ handler http.Handler }

func (transport handlerTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	type responseResult struct {
		response *http.Response
	}
	results := make(chan responseResult, 1)
	go func() {
		recorder := httptest.NewRecorder()
		transport.handler.ServeHTTP(recorder, request)
		response := recorder.Result()
		response.Request = request
		results <- responseResult{response: response}
	}()
	select {
	case result := <-results:
		return result.response, nil
	case <-request.Context().Done():
		return nil, request.Context().Err()
	}
}

func liveChannel(host string, result int, includePresets, protected bool) map[string]any {
	channel := map[string]any{"BNO": "24680", "TITLE": "SOOP title", "RMD": host, "CDN": "gs_cdn"}
	if result >= 0 {
		channel["RESULT"] = result
	}
	if includePresets {
		channel["VIEWPRESET"] = []string{"sd", "hd", "hd4k", "original", "auto"}
	}
	if protected {
		channel["BPWD"] = "Y"
	}
	return channel
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(value)
}

func serverURLFromRequest(r *http.Request) string {
	return "http://" + r.Host
}
