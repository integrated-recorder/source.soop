package soop

import (
	"fmt"
	"net/url"
	"regexp"
	"strconv"
	"strings"
)

var loginIDPattern = regexp.MustCompile(`^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$`)
var broadcastNumberPattern = regexp.MustCompile(`^[0-9]{1,20}$`)

type ChannelInput struct {
	LoginID        string
	BroadcastNo    string
	StreamPassword string
}

func ParseChannelInput(raw string) (ChannelInput, error) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return ChannelInput{}, fmt.Errorf("channel is required")
	}
	if strings.Contains(value, "://") {
		parsed, err := url.Parse(value)
		if err != nil || parsed == nil || parsed.Host == "" {
			return ChannelInput{}, fmt.Errorf("invalid channel URL")
		}
		if parsed.Scheme != "http" && parsed.Scheme != "https" {
			return ChannelInput{}, fmt.Errorf("unsupported channel URL")
		}
		if parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" || parsed.Port() != "" {
			return ChannelInput{}, fmt.Errorf("unsupported channel URL")
		}
		host := strings.ToLower(parsed.Hostname())
		if host != "play.sooplive.com" && host != "play.sooplive.co.kr" && host != "play.afreecatv.com" {
			return ChannelInput{}, fmt.Errorf("unsupported channel URL")
		}
		segments := strings.Split(strings.Trim(parsed.EscapedPath(), "/"), "/")
		if len(segments) < 1 || len(segments) > 2 || segments[0] == "" {
			return ChannelInput{}, fmt.Errorf("invalid channel URL path")
		}
		loginID, err := url.PathUnescape(segments[0])
		if err != nil || !validLoginID(loginID) {
			return ChannelInput{}, fmt.Errorf("invalid channel identifier")
		}
		channel := ChannelInput{LoginID: loginID}
		if len(segments) == 2 {
			bno, err := url.PathUnescape(segments[1])
			if err != nil || !validBroadcastNumber(bno) {
				return ChannelInput{}, fmt.Errorf("invalid broadcast number")
			}
			channel.BroadcastNo = normalizeBroadcastNumber(bno)
		}
		return channel, nil
	}
	if strings.ContainsAny(value, "/?#@:\\") || !validLoginID(value) {
		return ChannelInput{}, fmt.Errorf("invalid channel identifier")
	}
	return ChannelInput{LoginID: value}, nil
}

func validLoginID(value string) bool { return loginIDPattern.MatchString(value) }

func validBroadcastNumber(value string) bool {
	if !broadcastNumberPattern.MatchString(value) {
		return false
	}
	n, err := strconv.ParseUint(value, 10, 64)
	return err == nil && n > 0
}

func normalizeBroadcastNumber(value string) string {
	n, _ := strconv.ParseUint(value, 10, 64)
	return strconv.FormatUint(n, 10)
}
