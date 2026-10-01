package soop

import "testing"

func TestParseChannelInput(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		login   string
		bno     string
		wantErr bool
	}{
		{name: "login ID", input: "ysy5116", login: "ysy5116"},
		{name: "current SOOP URL", input: "https://play.sooplive.com/ysy5116", login: "ysy5116"},
		{name: "current URL with BNO", input: "https://play.sooplive.com/ysy5116/12345", login: "ysy5116", bno: "12345"},
		{name: "Korean SOOP URL", input: "https://play.sooplive.co.kr/creator_1/987", login: "creator_1", bno: "987"},
		{name: "historical URL", input: "http://play.afreecatv.com/creator_2", login: "creator_2"},
		{name: "historical URL with BNO", input: "https://play.afreecatv.com/creator_2/00042", login: "creator_2", bno: "42"},
		{name: "unsupported lookalike host", input: "https://play.sooplive.com.attacker.test/creator", wantErr: true},
		{name: "unsupported host", input: "https://www.sooplive.com/creator", wantErr: true},
		{name: "unsupported scheme", input: "ftp://play.sooplive.com/creator", wantErr: true},
		{name: "userinfo", input: "https://name@play.sooplive.com/creator", wantErr: true},
		{name: "query", input: "https://play.sooplive.com/creator?bno=123", wantErr: true},
		{name: "extra path", input: "https://play.sooplive.com/creator/123/456", wantErr: true},
		{name: "invalid broadcast number", input: "https://play.sooplive.com/creator/live", wantErr: true},
		{name: "malformed login ID", input: "../creator", wantErr: true},
		{name: "empty", input: "  ", wantErr: true},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got, err := ParseChannelInput(test.input)
			if test.wantErr {
				if err == nil {
					t.Fatal("expected input to be rejected")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected parser error: %v", err)
			}
			if got.LoginID != test.login || got.BroadcastNo != test.bno {
				t.Fatalf("parsed channel did not match expected identifiers")
			}
		})
	}
}
