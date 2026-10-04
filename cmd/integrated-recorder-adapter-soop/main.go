package main

import (
	"fmt"
	"os"

	"github.com/integrated-recorder/adapter-sdk-go/adapter"
	soopadapter "github.com/integrated-recorder/source.soop/internal/soop"
)

func main() {
	if err := adapter.Serve(soopadapter.NewAdapter()); err != nil {
		_, _ = fmt.Fprintln(os.Stderr, "SOOP adapter stopped")
		os.Exit(1)
	}
}
