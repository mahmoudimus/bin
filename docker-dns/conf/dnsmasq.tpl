domain-needed
bogus-priv
server=8.8.8.8
server=8.8.4.4
{{ define "host" }}
    {{ $host := .Host }}
    {{ $tld := .Tld }}
    {{ if eq $tld "" }}
        {{ range $index, $network := .Container.Networks }}
            {{ if ne $network.IP "" }}
address=/{{ $host }}/{{ $network.IP }}
            {{ end }}
        {{ end }}
    {{ else }}
        {{ range $index, $network := .Container.Networks }}
            {{ if ne $network.IP "" }}
address=/{{ $host }}.{{ $tld }}/{{ $network.IP }}
address=/{{ $host }}.{{ or ($.Env.HOSTNAME) "localhost" }}.{{ $tld }}/{{ $network.IP }}
            {{ end }}
        {{ end }}
    {{ end }}
{{ end }}

{{ $tld := or ($.Env.TOP_LEVEL_DOMAIN) "docker" }}
address=/host.{{ $tld }}/{{ $.Env.HOST_IP }}
address=/{{ $.Env.HOSTNAME }}.{{ $tld }}/{{ $.Env.HOST_IP }}
{{ range $index, $container := $ }}
    {{ $hosts := coalesce $container.Name (print "*." $container.Name) }}
    {{ $host_part := split $container.Name "_" }}
    {{ $host_part_len := len $host_part }}
    {{ if eq $host_part_len 3 }}
        {{ template "host" (dict "Container" $container "Host" (print (index $host_part 0)) "Tld" $tld) }}
        {{ template "host" (dict "Container" $container "Host" (print (index $host_part 1) "." (index $host_part 0)) "Tld" $tld) }}
    {{ end }}
    {{ if eq $host_part_len 4 }}
        {{ template "host" (dict "Container" $container "Host" (print (index $host_part 0)) "Tld" $tld) }}
        {{ template "host" (dict "Container" $container "Host" (print (index $host_part 1) "." (index $host_part 0)) "Tld" $tld) }}
        {{ template "host" (dict "Container" $container "Host" (print (index $host_part 2) "." (index $host_part 1) "." (index $host_part 0)) "Tld" $tld) }}
    {{ end }}
    {{ template "host" (dict "Container" $container "Host" $container.Name "Tld" $tld) }}
{{ end }}

{{ range $host, $containers := groupByMulti $ "Env.TOP_LEVEL_DOMAIN" "," }}
    {{ range $index, $container := $containers }}
        {{ template "host" (dict "Container" $container "Host" (print $host) "Tld" "") }}
    {{ end }}
{{ end }}
