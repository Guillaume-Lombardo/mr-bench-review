package middleware

import (
	"strings"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"

	"gofr.dev/pkg/gofr/config"
)

type MiddlewareConfig struct {
	CorsHeaders      map[string]string
	LogDisableProbes string
}

func GetConfigs(c config.Config) MiddlewareConfig {
	middlewareConfigs := MiddlewareConfig{
		CorsHeaders: make(map[string]string),
	}

	allowedCORSHeaders := []string{
		"ACCESS_CONTROL_ALLOW_ORIGIN",
		"ACCESS_CONTROL_ALLOW_HEADERS",
		"ACCESS_CONTROL_ALLOW_CREDENTIALS",
		"ACCESS_CONTROL_EXPOSE_HEADERS",
		"ACCESS_CONTROL_MAX_AGE",
	}

	for _, v := range allowedCORSHeaders {
		if val := c.Get(v); val != "" {
			middlewareConfigs.CorsHeaders[convertHeaderNames(v)] = val
		}
	}

	middlewareConfigs.LogDisableProbes = c.GetOrDefault("LOG_DISABLE_PROBES", "false")
	return middlewareConfigs
}

func convertHeaderNames(header string) string {
	words := strings.Split(header, "_")
	titleCaser := cases.Title(language.Und)

	for i, v := range words {
		words[i] = titleCaser.String(strings.ToLower(v))
	}

	return strings.Join(words, "-")
}
