module docker_manager

go 1.19

require (
	github.com/docker/docker v24.0.7+incompatible
	github.com/gin-gonic/gin v1.9.1
)

require (
	github.com/Microsoft/go-winio v0.6.1 // indirect
	github.com/distribution/reference v0.5.0 // indirect
	github.com/docker/distribution v2.8.3+incompatible // indirect
	github.com/docker/go-connections v0.4.0 // indirect
	github.com/docker/go-units v0.5.0 // indirect
	github.com/gogo/protobuf v1.3.2 // indirect
	github.com/opencontainers/go-digest v1.0.0 // indirect
	github.com/opencontainers/image-spec v1.0.2 // indirect
	github.com/pkg/errors v0.9.1 // indirect
	golang.org/x/mod v0.8.0 // indirect
	golang.org/x/net v0.10.0 // indirect
	golang.org/x/sys v0.8.0 // indirect
	golang.org/x/tools v0.6.0 // indirect
)

replace github.com/docker/distribution => github.com/docker/distribution v2.8.2-beta.1+incompatible 