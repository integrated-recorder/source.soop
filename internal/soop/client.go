package soop

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/integrated-recorder/adapter-sdk-go/adapter"
)

const (
	defaultAPIURL   = "https://live.sooplive.com/afreeca/player_live_api.php"
	defaultLoginURL = "https://login.sooplive.com/app/LoginAction.php"
	defaultPlayURL  = "https://play.sooplive.com"
	playerReferer   = "https://play.sooplive.com/"
	stableUserAgent = "IntegratedRecorder-SOOP-Adapter/0.1.0"
	maxResponseSize = 2 << 20
)

type endpoints struct {
	apiURL        string
	loginURL      string
	playBaseURL   string
	testHosts     map[string]bool
	allowTestHTTP bool
}

type platformClient struct {
	http      *http.Client
	endpoints endpoints
}

type accountCredentials struct {
	username string
	password string
}

type apiReply struct {
	channel map[string]json.RawMessage
	result  *int
}

type liveInfo struct {
	LoginID        string
	BroadcastNo    string
	Title          string
	RMD            string
	CDN            string
	Presets        []preset
	PasswordNeeded bool
}

type preset struct {
	Name  string
	Label string
}

var broadNoInPage = regexp.MustCompile(`(?i)window\s*\.\s*nBroadNo\s*=\s*["']?([0-9]{1,20})`)

func newPlatformClient() *platformClient {
	jar, _ := cookiejar.New(nil)
	hc := &http.Client{
		Timeout: 12 * time.Second,
		Jar:     jar,
		CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
			// Never forward login credentials or cookies through an unexpected redirect.
			return http.ErrUseLastResponse
		},
	}
	return &platformClient{http: hc, endpoints: endpoints{
		apiURL:      defaultAPIURL,
		loginURL:    defaultLoginURL,
		playBaseURL: defaultPlayURL,
	}}
}

func newPlatformClientForTest(httpClient *http.Client, e endpoints) *platformClient {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: time.Second}
	}
	if httpClient.CheckRedirect == nil {
		httpClient.CheckRedirect = func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }
	}
	return &platformClient{http: httpClient, endpoints: e}
}

func (c *platformClient) lookupLive(ctx context.Context, channel ChannelInput, credentials accountCredentials) (liveInfo, bool, error) {
	form := commonForm()
	form.Set("type", "live")
	form.Set("bid", channel.LoginID)
	if channel.BroadcastNo != "" {
		form.Set("bno", channel.BroadcastNo)
	}
	reply, err := c.playerCall(ctx, form, credentials)
	if err != nil {
		return liveInfo{}, false, err
	}
	state, err := classifyLiveReply(reply)
	if err != nil {
		return liveInfo{}, false, err
	}
	if state == "offline" {
		return liveInfo{}, true, nil
	}

	info := liveInfo{LoginID: channel.LoginID}
	info.BroadcastNo = stringField(reply.channel, "BNO", "bno")
	if info.BroadcastNo == "" {
		info.BroadcastNo = channel.BroadcastNo
	}
	info.Title = stringField(reply.channel, "TITLE", "title")
	if !validTitle(info.Title) {
		return liveInfo{}, false, invalidPlatformResponse()
	}
	info.RMD = stringField(reply.channel, "RMD", "rmd")
	info.CDN = stringField(reply.channel, "CDN", "cdn")
	info.Presets = extractPresets(reply.channel)
	info.PasswordNeeded = truthyField(reply.channel, "BPWD", "bpwd")
	if info.BroadcastNo != "" && validBroadcastNumber(info.BroadcastNo) {
		info.BroadcastNo = normalizeBroadcastNumber(info.BroadcastNo)
	} else {
		info.BroadcastNo = ""
	}
	if info.BroadcastNo == "" {
		bno, pageErr := c.lookupBroadcastNo(ctx, channel.LoginID)
		if pageErr != nil {
			return liveInfo{}, false, pageErr
		}
		channel.BroadcastNo = bno
		form.Set("bno", bno)
		reply, err = c.playerCall(ctx, form, credentials)
		if err != nil {
			return liveInfo{}, false, err
		}
		state, err = classifyLiveReply(reply)
		if err != nil {
			return liveInfo{}, false, err
		}
		if state == "offline" {
			return liveInfo{}, true, nil
		}
		info.BroadcastNo = stringField(reply.channel, "BNO", "bno")
		if info.BroadcastNo == "" {
			info.BroadcastNo = bno
		}
		info.Title = stringField(reply.channel, "TITLE", "title")
		if !validTitle(info.Title) {
			return liveInfo{}, false, invalidPlatformResponse()
		}
		info.RMD = stringField(reply.channel, "RMD", "rmd")
		info.CDN = stringField(reply.channel, "CDN", "cdn")
		info.Presets = extractPresets(reply.channel)
		info.PasswordNeeded = truthyField(reply.channel, "BPWD", "bpwd")
	}
	if !validBroadcastNumber(info.BroadcastNo) {
		return liveInfo{}, false, invalidPlatformResponse()
	}
	info.BroadcastNo = normalizeBroadcastNumber(info.BroadcastNo)
	return info, false, nil
}

func (c *platformClient) resolveManifest(ctx context.Context, info liveInfo, quality, streamPassword string, credentials accountCredentials) (string, string, error) {
	if info.RMD == "" || info.CDN == "" || len(info.Presets) == 0 {
		return "", "", invalidPlatformResponse()
	}
	chosen, err := choosePreset(info.Presets, quality)
	if err != nil {
		return "", "", err
	}
	if info.PasswordNeeded && streamPassword == "" {
		return "", "", adapter.Error("stream_password_required", "this broadcast requires its stream password")
	}

	form := commonForm()
	form.Set("type", "aid")
	form.Set("bid", info.LoginID)
	form.Set("bno", info.BroadcastNo)
	form.Set("quality", chosen.Name)
	if streamPassword != "" {
		form.Set("pwd", streamPassword)
	}
	reply, err := c.playerCall(ctx, form, credentials)
	if err != nil {
		return "", "", err
	}
	if reply.result != nil && *reply.result != 1 {
		if *reply.result == -5 && streamPassword == "" {
			return "", "", adapter.Error("stream_password_required", "this broadcast requires its stream password")
		}
		if *reply.result == -5 {
			return "", "", adapter.Error("invalid_stream_password", "SOOP rejected the stream password")
		}
		return "", "", platformFailure()
	}
	aid := stringField(reply.channel, "AID", "aid")
	if aid == "" {
		return "", "", invalidPlatformResponse()
	}
	manifest, err := c.assignViewURL(ctx, info, chosen.Name, aid)
	if err != nil {
		return "", "", err
	}
	return manifest, chosen.Label, nil
}

func (c *platformClient) playerCall(ctx context.Context, form url.Values, credentials accountCredentials) (apiReply, error) {
	reply, err := c.postPlayer(ctx, form)
	if err != nil {
		return apiReply{}, err
	}
	if reply.result == nil || *reply.result != -6 {
		return reply, nil
	}
	if credentials.username == "" || credentials.password == "" {
		return apiReply{}, adapter.Error("authentication_required", "SOOP account authentication is required")
	}
	if err := c.login(ctx, credentials); err != nil {
		return apiReply{}, err
	}
	retry, err := c.postPlayer(ctx, form)
	if err != nil {
		return apiReply{}, err
	}
	if retry.result != nil && *retry.result == -6 {
		return apiReply{}, adapter.Error("authentication_required", "SOOP account authentication failed")
	}
	return retry, nil
}

func (c *platformClient) postPlayer(ctx context.Context, form url.Values) (apiReply, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoints.apiURL, strings.NewReader(form.Encode()))
	if err != nil {
		return apiReply{}, platformFailure()
	}
	request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	request.Header.Set("Accept", "application/json, text/plain, */*")
	request.Header.Set("Origin", playerOrigin(c.endpoints.playBaseURL))
	request.Header.Set("Referer", playerReferer)
	request.Header.Set("User-Agent", stableUserAgent)
	response, err := c.http.Do(request)
	if err != nil {
		return apiReply{}, platformFailure()
	}
	defer response.Body.Close()
	body, err := readBounded(response.Body)
	if err != nil {
		return apiReply{}, invalidPlatformResponse()
	}
	if response.StatusCode < 200 || response.StatusCode > 299 {
		return apiReply{}, platformFailure()
	}
	reply, err := decodeAPIReply(body)
	if err != nil {
		return apiReply{}, invalidPlatformResponse()
	}
	return reply, nil
}

func (c *platformClient) login(ctx context.Context, credentials accountCredentials) error {
	form := url.Values{}
	form.Set("szWork", "login")
	form.Set("szType", "json")
	form.Set("szUid", credentials.username)
	form.Set("szPassword", credentials.password)
	form.Set("isSaveId", "true")
	form.Set("isSavePw", "false")
	form.Set("isSaveJoin", "false")
	form.Set("isLoginRetain", "Y")
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoints.loginURL, strings.NewReader(form.Encode()))
	if err != nil {
		return platformFailure()
	}
	request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	request.Header.Set("Accept", "application/json, text/plain, */*")
	request.Header.Set("Origin", playerOrigin(c.endpoints.playBaseURL))
	request.Header.Set("Referer", playerReferer)
	request.Header.Set("User-Agent", stableUserAgent)
	response, err := c.http.Do(request)
	if err != nil {
		return platformFailure()
	}
	defer response.Body.Close()
	body, err := readBounded(response.Body)
	if err != nil || response.StatusCode < 200 || response.StatusCode > 299 {
		return adapter.Error("authentication_required", "SOOP account authentication failed")
	}
	var resultObj map[string]json.RawMessage
	if err := json.Unmarshal(body, &resultObj); err != nil || resultObj == nil {
		return adapter.Error("authentication_required", "SOOP account authentication failed")
	}
	result, ok := integerValue(resultObj["RESULT"])
	if !ok || result != 1 {
		return adapter.Error("authentication_required", "SOOP account authentication failed")
	}
	return nil
}

func (c *platformClient) lookupBroadcastNo(ctx context.Context, loginID string) (string, error) {
	base, err := url.Parse(c.endpoints.playBaseURL)
	if err != nil || base.Host == "" {
		return "", platformFailure()
	}
	base.Path = strings.TrimRight(base.Path, "/") + "/" + url.PathEscape(loginID)
	base.RawQuery = ""
	base.Fragment = ""
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, base.String(), nil)
	if err != nil {
		return "", platformFailure()
	}
	request.Header.Set("Accept", "text/html,application/xhtml+xml")
	request.Header.Set("User-Agent", stableUserAgent)
	response, err := c.http.Do(request)
	if err != nil {
		return "", platformFailure()
	}
	defer response.Body.Close()
	body, err := readBounded(response.Body)
	if err != nil || response.StatusCode < 200 || response.StatusCode > 299 {
		return "", platformFailure()
	}
	match := broadNoInPage.FindSubmatch(body)
	if len(match) != 2 || !validBroadcastNumber(string(match[1])) {
		return "", invalidPlatformResponse()
	}
	return normalizeBroadcastNumber(string(match[1])), nil
}

func (c *platformClient) assignViewURL(ctx context.Context, info liveInfo, quality, aid string) (string, error) {
	rmd, err := url.Parse(strings.TrimSpace(info.RMD))
	if err != nil || !c.validDynamicURL(rmd) || rmd.User != nil || rmd.RawQuery != "" || rmd.Fragment != "" {
		return "", invalidPlatformResponse()
	}
	rmd.Path = strings.TrimRight(rmd.Path, "/") + "/broad_stream_assign.html"
	rmd.RawPath = ""
	query := url.Values{}
	returnType := strings.TrimSpace(info.CDN)
	switch strings.ToLower(returnType) {
	case "gs_cdn":
		returnType = "gs_cdn_pc_web"
	case "lg_cdn":
		returnType = "lg_cdn_pc_web"
	}
	query.Set("return_type", returnType)
	query.Set("broad_key", info.BroadcastNo+"-common-"+quality+"-hls")
	rmd.RawQuery = query.Encode()
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, rmd.String(), nil)
	if err != nil {
		return "", platformFailure()
	}
	request.Header.Set("Accept", "application/json, text/plain, */*")
	request.Header.Set("Referer", playerReferer)
	request.Header.Set("User-Agent", stableUserAgent)
	response, err := c.http.Do(request)
	if err != nil {
		return "", platformFailure()
	}
	defer response.Body.Close()
	body, err := readBounded(response.Body)
	if err != nil || response.StatusCode < 200 || response.StatusCode > 299 {
		return "", platformFailure()
	}
	var assign map[string]json.RawMessage
	if err := json.Unmarshal(body, &assign); err != nil || assign == nil {
		return "", invalidPlatformResponse()
	}
	viewURL := stringField(assign, "view_url", "VIEW_URL", "viewUrl")
	if viewURL == "" {
		return "", invalidPlatformResponse()
	}
	view, err := url.Parse(strings.TrimSpace(viewURL))
	if err != nil || !c.validDynamicURL(view) || view.User != nil || view.Fragment != "" {
		return "", invalidPlatformResponse()
	}
	values := view.Query()
	values.Set("aid", aid)
	view.RawQuery = values.Encode()
	return view.String(), nil
}

func (c *platformClient) validDynamicURL(u *url.URL) bool {
	if u == nil || u.Hostname() == "" {
		return false
	}
	if port := u.Port(); port != "" && port != "443" {
		return false
	}
	if c.endpoints.testHosts[strings.ToLower(u.Hostname())] {
		return (u.Scheme == "https" || (c.endpoints.allowTestHTTP && u.Scheme == "http"))
	}
	if u.Scheme != "https" {
		return false
	}
	host := strings.ToLower(u.Hostname())
	for _, suffix := range []string{"sooplive.com", "sooplive.co.kr", "afreecatv.com", "afreecatv.co.kr"} {
		if host == suffix || strings.HasSuffix(host, "."+suffix) {
			return true
		}
	}
	return false
}

func commonForm() url.Values {
	form := url.Values{}
	form.Set("from_api", "0")
	form.Set("mode", "landing")
	form.Set("player_type", "html5")
	form.Set("stream_type", "common")
	return form
}

func playerOrigin(playBaseURL string) string {
	u, err := url.Parse(playBaseURL)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return "https://play.sooplive.com"
	}
	return u.Scheme + "://" + u.Host
}

func decodeAPIReply(body []byte) (apiReply, error) {
	var root map[string]json.RawMessage
	if err := json.Unmarshal(body, &root); err != nil || root == nil {
		return apiReply{}, errMalformedJSON
	}
	var channel map[string]json.RawMessage
	if raw, ok := root["CHANNEL"]; ok {
		if err := json.Unmarshal(raw, &channel); err != nil || channel == nil {
			return apiReply{}, errMalformedJSON
		}
	}
	resultRaw, ok := root["RESULT"]
	if channelResult, channelHas := lookupRaw(channel, "RESULT", "result"); channelHas {
		resultRaw, ok = channelResult, true
	}
	var resultPtr *int
	if ok {
		value, valid := integerValue(resultRaw)
		if !valid {
			return apiReply{}, errMalformedJSON
		}
		resultPtr = &value
	}
	if channel == nil && (resultPtr == nil || *resultPtr != 0) {
		return apiReply{}, errMalformedJSON
	}
	return apiReply{channel: channel, result: resultPtr}, nil
}

func classifyLiveReply(reply apiReply) (string, error) {
	if reply.result != nil {
		switch *reply.result {
		case 0:
			return "offline", nil
		case 1:
			if reply.channel == nil {
				return "", invalidPlatformResponse()
			}
			return "live", nil
		case -6:
			return "", adapter.Error("authentication_required", "SOOP account authentication is required")
		default:
			return "", platformFailure()
		}
	}
	if reply.channel != nil {
		if _, ok := lookupRaw(reply.channel, "RESOLUTION", "resolution"); ok {
			return "live", nil
		}
		if _, ok := lookupRaw(reply.channel, "VIEWPRESET", "viewpreset"); ok {
			return "live", nil
		}
	}
	return "", invalidPlatformResponse()
}

func extractPresets(channel map[string]json.RawMessage) []preset {
	raw, ok := lookupRaw(channel, "VIEWPRESET", "viewpreset", "PRESETS", "presets")
	if !ok {
		return nil
	}
	var stringsList []string
	if json.Unmarshal(raw, &stringsList) == nil {
		out := make([]preset, 0, len(stringsList))
		for _, item := range stringsList {
			item = strings.TrimSpace(item)
			if item != "" {
				out = append(out, newPreset(item, item))
			}
		}
		return out
	}
	var rows []map[string]json.RawMessage
	if json.Unmarshal(raw, &rows) == nil {
		out := make([]preset, 0, len(rows))
		for _, row := range rows {
			name := stringField(row, "name", "NAME", "quality", "QUALITY", "value", "VALUE")
			label := stringField(row, "label", "LABEL", "display_name", "DISPLAY_NAME")
			if name == "" {
				name = label
			}
			if label == "" {
				label = name
			}
			if name != "" {
				out = append(out, newPreset(name, label))
			}
		}
		return out
	}
	var object map[string]json.RawMessage
	if json.Unmarshal(raw, &object) == nil && object != nil {
		out := make([]preset, 0, len(object))
		keys := make([]string, 0, len(object))
		for key := range object {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		for _, key := range keys {
			value := object[key]
			label, _ := stringValue(value)
			if label == "" {
				label = key
			}
			out = append(out, newPreset(key, label))
		}
		return out
	}
	return nil
}

func validTitle(value string) bool {
	return len(value) <= 4096 && utf8.ValidString(value) && !strings.ContainsRune(value, '\x00')
}

func newPreset(name, label string) preset {
	return preset{Name: strings.TrimSpace(name), Label: strings.TrimSpace(label)}
}

func choosePreset(presets []preset, quality string) (preset, error) {
	filtered := make([]preset, 0, len(presets))
	for _, item := range presets {
		if item.Name != "" && !strings.EqualFold(item.Name, "auto") && !strings.EqualFold(item.Label, "auto") {
			filtered = append(filtered, item)
		}
	}
	if len(filtered) == 0 {
		return preset{}, invalidPlatformResponse()
	}
	quality = strings.TrimSpace(quality)
	if quality == "" || strings.EqualFold(quality, "best") {
		return filtered[len(filtered)-1], nil
	}
	if strings.EqualFold(quality, "worst") {
		return filtered[0], nil
	}
	for _, item := range filtered {
		if strings.EqualFold(item.Name, quality) || strings.EqualFold(item.Label, quality) {
			return item, nil
		}
	}
	return preset{}, adapter.Error("invalid_configuration", "quality must be best, worst, or a SOOP preset")
}

func stringField(object map[string]json.RawMessage, keys ...string) string {
	raw, ok := lookupRaw(object, keys...)
	if !ok {
		return ""
	}
	value, _ := stringValue(raw)
	return strings.TrimSpace(value)
}

func stringValue(raw json.RawMessage) (string, bool) {
	var value string
	if json.Unmarshal(raw, &value) == nil {
		return value, true
	}
	var number json.Number
	decoder := json.NewDecoder(strings.NewReader(string(raw)))
	decoder.UseNumber()
	if decoder.Decode(&number) == nil {
		return number.String(), true
	}
	return "", false
}

func truthyField(object map[string]json.RawMessage, keys ...string) bool {
	raw, ok := lookupRaw(object, keys...)
	if !ok {
		return false
	}
	var value bool
	if json.Unmarshal(raw, &value) == nil {
		return value
	}
	text, _ := stringValue(raw)
	return text == "1" || strings.EqualFold(text, "true") || strings.EqualFold(text, "y")
}

func lookupRaw(object map[string]json.RawMessage, keys ...string) (json.RawMessage, bool) {
	for _, key := range keys {
		if raw, ok := object[key]; ok {
			return raw, true
		}
		for candidate, raw := range object {
			if strings.EqualFold(candidate, key) {
				return raw, true
			}
		}
	}
	return nil, false
}

func integerValue(raw json.RawMessage) (int, bool) {
	text, ok := stringValue(raw)
	if !ok {
		return 0, false
	}
	value, err := strconv.Atoi(text)
	return value, err == nil
}

func readBounded(reader io.Reader) ([]byte, error) {
	body, err := io.ReadAll(io.LimitReader(reader, maxResponseSize+1))
	if err != nil || len(body) > maxResponseSize {
		return nil, errMalformedJSON
	}
	return body, nil
}

func invalidPlatformResponse() error {
	return adapter.Error("invalid_platform_response", "SOOP returned an invalid response")
}

func platformFailure() error {
	return adapter.Error("platform_unavailable", "SOOP could not complete the request")
}

var errMalformedJSON = errors.New("malformed platform response")
