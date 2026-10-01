package main

import (
	"fmt"
	"os"

	"github.com/dltkddnr04/integrated-recorder-adapter-sdk-go/adapter"
	soopadapter "github.com/dltkddnr04/integrated-recorder-adapter-soop/internal/soop"
)

func main() {
	if err := adapter.Serve(soopadapter.NewAdapter()); err != nil {
		_, _ = fmt.Fprintln(os.Stderr, "SOOP adapter stopped")
		os.Exit(1)
	}
}
