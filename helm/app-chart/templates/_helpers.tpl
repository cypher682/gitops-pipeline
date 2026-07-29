{{- define "app-chart.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "app-chart.fullname" -}}
{{- printf "%s-%s" .Chart.Name .Values.environment | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "app-chart.labels" -}}
app.kubernetes.io/name: {{ include "app-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
environment: {{ .Values.environment }}
{{- end -}}

{{- define "app-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "app-chart.name" . }}
environment: {{ .Values.environment }}
{{- end -}}

{{- define "app-chart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{ .Values.serviceAccount.name | default (include "app-chart.fullname" .) }}
{{- else -}}
{{ .Values.serviceAccount.name | default "default" }}
{{- end -}}
{{- end -}}
