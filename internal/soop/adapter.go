package soop

import (
	"context"
	"encoding/json"
	"errors"
	"strings"

	"github.com/integrated-recorder/adapter-sdk-go/adapter"
	"github.com/integrated-recorder/adapter-sdk-go/protocol"
)

type Adapter struct {
	client *platformClient
}

type sourceMetadata struct {
	Channel string `json:"channel"`
	BNO     string `json:"bno"`
	Quality string `json:"quality"`
}

type inputFields struct {
	Channel        string `json:"channel"`
	StreamPassword string `json:"stream_password"`
}

func NewAdapter() *Adapter { return &Adapter{client: newPlatformClient()} }

func newAdapterForTest(client *platformClient) *Adapter { return &Adapter{client: client} }

func (*Adapter) Descriptor() protocol.Descriptor {
	return protocol.Descriptor{
		ID:              "soop",
		Name:            "SOOP Live",
		Version:         "0.1.0",
		ProtocolVersion: protocol.Version,
		Capabilities: []string{
			protocol.CapabilityResolve,
			protocol.CapabilityWatch,
			protocol.CapabilityMetadata,
			protocol.CapabilityRefresh,
		},
		InputSchema: protocol.Schema{Fields: []protocol.Field{
			{Key: "channel", Control: "text", Label: "Channel", Description: "SOOP channel login ID or supported play URL", Required: true},
			{Key: "stream_password", Control: "secret", Label: "Stream password", Description: "Password for a password-protected broadcast"},
		}},
		ConfigurationSchema: protocol.Schema{Fields: []protocol.Field{
			{Key: "quality", Control: "text", Label: "Quality", Description: "best, worst, or an exact SOOP preset name or label", Default: json.RawMessage(`"best"`)},
			{Key: "account_username", Control: "secret", Label: "SOOP account username", Description: "Optional account used when SOOP requires login"},
			{Key: "account_password", Control: "secret", Label: "SOOP account password", Description: "Optional account password used when SOOP requires login"},
		}},
		MediaTypes: []string{"hls"},
	}
}

func (a *Adapter) Resolve(ctx context.Context, p protocol.ResolveParams) (protocol.ResolveResult, error) {
	input, err := parseInput(p.Input)
	if err != nil {
		return protocol.ResolveResult{}, err
	}
	credentials, quality, err := resolveOptions(p.Configuration, p.Secrets)
	if err != nil {
		return protocol.ResolveResult{}, err
	}
	info, offline, err := a.client.lookupLive(ctx, input, credentials)
	if err != nil {
		return protocol.ResolveResult{}, err
	}
	if offline {
		return protocol.ResolveResult{}, adapter.Error("channel_offline", "SOOP channel is offline")
	}
	media, _, err := a.mediaFor(ctx, info, quality, input.StreamPassword, credentials)
	if err != nil {
		return protocol.ResolveResult{}, err
	}
	return protocol.ResolveResult{Media: media, State: secretStateMutation(info, input.StreamPassword, credentials)}, nil
}

func (a *Adapter) WatchCheck(ctx context.Context, p protocol.WatchCheckParams) (protocol.WatchCheckResult, error) {
	input, err := parseInput(p.Input)
	if err != nil {
		return protocol.WatchCheckResult{}, err
	}
	credentials, quality, err := resolveOptions(p.Configuration, p.Secrets)
	if err != nil {
		return protocol.WatchCheckResult{}, err
	}
	info, offline, err := a.client.lookupLive(ctx, input, credentials)
	if err != nil {
		return protocol.WatchCheckResult{}, err
	}
	if offline {
		return protocol.WatchCheckResult{State: "offline"}, nil
	}
	media, _, err := a.mediaFor(ctx, info, quality, input.StreamPassword, credentials)
	if err != nil {
		return protocol.WatchCheckResult{}, err
	}
	result := protocol.WatchCheckResult{
		State:      "live",
		SessionRef: sessionRef(info.LoginID, info.BroadcastNo),
		Media:      &media,
	}
	if info.Title != "" {
		result.Title = info.Title
	}
	result.StateMutations = secretStateMutation(info, input.StreamPassword, credentials)
	return result, nil
}

func (a *Adapter) Metadata(ctx context.Context, p protocol.MetadataParams) (protocol.MetadataResult, error) {
	if p.Current.Type != "hls" {
		return protocol.MetadataResult{}, adapter.Error("unsupported_media", "metadata is available for HLS media")
	}
	metadata, err := decodeSourceMetadata(p.Current.Metadata)
	if err != nil {
		return protocol.MetadataResult{}, err
	}
	credentials, _, err := resolveOptions(p.Configuration, p.Secrets)
	if err != nil {
		return protocol.MetadataResult{}, err
	}
	info, offline, err := a.client.lookupLive(ctx, ChannelInput{LoginID: metadata.Channel, BroadcastNo: metadata.BNO}, credentials)
	if err != nil {
		return protocol.MetadataResult{}, err
	}
	if offline {
		return protocol.MetadataResult{}, platformFailure()
	}
	if info.BroadcastNo != metadata.BNO {
		return protocol.MetadataResult{}, adapter.Error("broadcast_changed", "SOOP broadcast identity changed")
	}
	if info.Title == "" {
		return protocol.MetadataResult{}, platformFailure()
	}
	title := info.Title
	return protocol.MetadataResult{Metadata: protocol.StreamMetadata{Title: &title}}, nil
}

func (a *Adapter) Refresh(ctx context.Context, p protocol.RefreshParams) (protocol.RefreshResult, error) {
	if p.Current.Type != "hls" {
		return protocol.RefreshResult{}, adapter.Error("unsupported_media", "refresh is available for HLS media")
	}
	metadata, err := decodeSourceMetadata(p.Current.Metadata)
	if err != nil {
		return protocol.RefreshResult{}, err
	}
	if p.Current.SessionRef != "" && p.Current.SessionRef != sessionRef(metadata.Channel, metadata.BNO) {
		return protocol.RefreshResult{}, adapter.Error("invalid_media_metadata", "SOOP source identity does not match its session")
	}
	streamPassword, credentials, err := recoverRefreshSecrets(p.State, metadata)
	if err != nil {
		return protocol.RefreshResult{}, err
	}
	info, offline, err := a.client.lookupLive(ctx, ChannelInput{LoginID: metadata.Channel, BroadcastNo: metadata.BNO}, credentials)
	if err != nil {
		if hasErrorCode(err, "authentication_required") && credentials.username == "" {
			return protocol.RefreshResult{}, missingRefreshState()
		}
		return protocol.RefreshResult{}, err
	}
	if offline {
		return protocol.RefreshResult{}, platformFailure()
	}
	if info.BroadcastNo != metadata.BNO {
		return protocol.RefreshResult{}, adapter.Error("broadcast_changed", "SOOP broadcast identity changed")
	}
	if info.PasswordNeeded && streamPassword == "" {
		return protocol.RefreshResult{}, missingRefreshState()
	}
	media, _, err := a.mediaFor(ctx, info, metadata.Quality, streamPassword, credentials)
	if err != nil {
		if hasErrorCode(err, "stream_password_required") {
			return protocol.RefreshResult{}, missingRefreshState()
		}
		return protocol.RefreshResult{}, err
	}
	media.SessionRef = p.Current.SessionRef
	media.RefreshPolicy = p.Current.RefreshPolicy
	return protocol.RefreshResult{Media: media}, nil
}

func (a *Adapter) mediaFor(ctx context.Context, info liveInfo, quality, streamPassword string, credentials accountCredentials) (protocol.MediaSource, string, error) {
	manifestURL, chosenLabel, err := a.client.resolveManifest(ctx, info, quality, streamPassword, credentials)
	if err != nil {
		return protocol.MediaSource{}, "", err
	}
	metadata, err := json.Marshal(sourceMetadata{Channel: info.LoginID, BNO: info.BroadcastNo, Quality: chosenLabel})
	if err != nil {
		return protocol.MediaSource{}, "", adapter.Error("internal_error", "SOOP media could not be prepared")
	}
	media := protocol.MediaSource{
		Type:        "hls",
		ManifestURL: manifestURL,
		Headers: map[string]string{
			"Referer":    playerReferer,
			"Origin":     "https://play.sooplive.com",
			"User-Agent": stableUserAgent,
		},
		RequestPolicy: &protocol.RequestPolicy{HeaderForwarding: &protocol.HeaderForwardingPolicy{Mode: protocol.HeaderForwardingSameOrigin}},
		SessionRef:    sessionRef(info.LoginID, info.BroadcastNo),
		Metadata:      metadata,
		ArchivePolicy: &protocol.ArchivePolicy{SourceURI: "sensitive"},
		RefreshPolicy: &protocol.RefreshPolicy{OnHTTPStatus: []int{401, 403}},
	}
	return media, chosenLabel, nil
}

func parseInput(raw json.RawMessage) (ChannelInput, error) {
	var fields inputFields
	if err := protocol.DecodeObject(raw, &fields); err != nil {
		return ChannelInput{}, adapter.Error("invalid_input", "input must contain a valid SOOP channel")
	}
	channel, err := ParseChannelInput(fields.Channel)
	if err != nil {
		return ChannelInput{}, adapter.Error("invalid_input", "input must contain a valid SOOP channel")
	}
	channel.StreamPassword = fields.StreamPassword
	return channel, nil
}

func resolveOptions(configuration map[string]json.RawMessage, secrets map[string]string) (accountCredentials, string, error) {
	quality := "best"
	if raw, ok := configuration["quality"]; ok {
		var value string
		if err := json.Unmarshal(raw, &value); err != nil {
			return accountCredentials{}, "", adapter.Error("invalid_configuration", "quality must be text")
		}
		quality = strings.TrimSpace(value)
		if quality == "" {
			return accountCredentials{}, "", adapter.Error("invalid_configuration", "quality must be best, worst, or a SOOP preset")
		}
	}
	credentials := accountCredentials{username: strings.TrimSpace(secrets["account_username"]), password: secrets["account_password"]}
	if (credentials.username == "") != (credentials.password == "") {
		return accountCredentials{}, "", adapter.Error("invalid_configuration", "provide both SOOP account credentials or leave both empty")
	}
	return credentials, quality, nil
}

func decodeSourceMetadata(raw json.RawMessage) (sourceMetadata, error) {
	var metadata sourceMetadata
	if err := protocol.DecodeObject(raw, &metadata); err != nil || !validLoginID(metadata.Channel) || !validBroadcastNumber(metadata.BNO) || strings.TrimSpace(metadata.Quality) == "" {
		return sourceMetadata{}, adapter.Error("invalid_media_metadata", "SOOP source metadata is invalid")
	}
	metadata.BNO = normalizeBroadcastNumber(metadata.BNO)
	return metadata, nil
}

func sessionRef(channel, bno string) string { return "soop:" + channel + ":" + bno }

func secretStateMutation(info liveInfo, streamPassword string, credentials accountCredentials) []protocol.StateMutation {
	secrets := make(map[string]string, 3)
	keyPrefix := "soop:" + info.LoginID + ":" + info.BroadcastNo + ":"
	if streamPassword != "" {
		secrets[keyPrefix+"stream_password"] = streamPassword
	}
	if credentials.username != "" && credentials.password != "" {
		secrets[keyPrefix+"account_username"] = credentials.username
		secrets[keyPrefix+"account_password"] = credentials.password
	}
	if len(secrets) == 0 {
		return nil
	}
	return []protocol.StateMutation{{Secrets: secrets}}
}

func recoverRefreshSecrets(state []protocol.StateDocument, metadata sourceMetadata) (string, accountCredentials, error) {
	prefix := "soop:" + metadata.Channel + ":" + metadata.BNO + ":"
	var password string
	var credentials accountCredentials
	for _, document := range state {
		if document.Resource != nil {
			continue
		}
		if value := document.Secrets[prefix+"stream_password"]; value != "" {
			password = value
		}
		if value := document.Secrets[prefix+"account_username"]; value != "" {
			credentials.username = value
		}
		if value := document.Secrets[prefix+"account_password"]; value != "" {
			credentials.password = value
		}
	}
	if (credentials.username == "") != (credentials.password == "") {
		return "", accountCredentials{}, missingRefreshState()
	}
	return password, credentials, nil
}

func missingRefreshState() error {
	return adapter.Error("refresh_state_missing", "SOOP refresh credentials are unavailable; resolve the channel again with its current credentials")
}

func hasErrorCode(err error, code string) bool {
	var operation *adapter.OperationError
	return errors.As(err, &operation) && operation.Code == code
}
