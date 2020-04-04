COMPOSE_IMAGES := $(shell docker-compose config 2>/dev/null | awk '{if ($$1 == "image:") print $$2;}')

.PHONY: clean build save 

clean:
	docker system prune -f --all --volumes
	rm -rf iml-images.tar.gz

build: clean
	DOCKER_BUILDKIT=1 docker build -t imlteam/python-service-base:6.1.0-dev -f python-service-base.dockerfile ../
	DOCKER_BUILDKIT=1 docker build -t imlteam/systemd-base:6.1.0-dev -f systemd-base.dockerfile ../
	DOCKER_BUILDKIT=1 docker build -t rust-iml-base -f rust-base.dockerfile ../
	DOCKER_BUILDKIT=1 docker build -t rust-iml-gui -f iml-gui.dockerfile ../
	DOCKER_BUILDKIT=1 docker build -t imlteam/rust-service-base:6.1.0-dev -f rust-service-base.dockerfile ../
	COMPOSE_DOCKER_CLI_BUILD=1 docker-compose build

save: build
	COMPOSE_DOCKER_CLI_BUILD=1 docker-compose pull postgres rabbit update-handler
	docker save -o iml-images.tar $(COMPOSE_IMAGES)
	gzip -9 < iml-images.tar > iml-images.tgz


