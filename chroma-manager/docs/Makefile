DIRS = rest-api storage-plugin-api internals packaging scheduler-plugin-api

all: $(DIRS)

dist:
	mkdir -p dist

.PHONY: $(DIRS)
$(DIRS): dist
	make -C $@ html
	rm -rf dist/*-doc-$@
	cp -r $@/_build/html dist/manager-doc-$@
	tar -C dist -czf dist/manager-doc-$@.tar.gz manager-doc-$@
