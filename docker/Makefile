override SHELL = bash
override .SHELLFLAGS = -eux -o pipefail -c

COMPOSE_IMAGES := $(shell docker-compose config 2>/dev/null | awk '{if ($$1 == "image:") print $$2;}')

.PHONY: clean build save

clean:
	docker system prune -f --all --volumes
	rm -rf iml-images.tgz

build: clean
	DOCKER_CLI_EXPERIMENTAL=enabled docker buildx bake -f compose-deps.hcl
	DOCKER_CLI_EXPERIMENTAL=enabled docker buildx bake -f docker-compose.yml
	COMPOSE_DOCKER_CLI_BUILD=1 docker-compose pull postgres update-handler

save: build
	docker save $(COMPOSE_IMAGES) | gzip -9 > iml-images.tgz
