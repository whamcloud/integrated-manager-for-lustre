COMPOSE_IMAGES := $(shell docker-compose config 2>/dev/null | awk '{if ($$1 == "image:") print $$2;}')

.PHONY: clean build save 

clean:
	docker system prune -f --all --volumes
	rm -rf emf-images.tar.gz

build: clean
	DOCKER_CLI_EXPERIMENTAL=enabled docker buildx bake -f compose-deps.hcl
	DOCKER_CLI_EXPERIMENTAL=enabled docker buildx bake -f docker-compose.yml

save: build
	docker save -o emf-images.tar $(COMPOSE_IMAGES)
	gzip -9 < emf-images.tar > emf-images.tgz
