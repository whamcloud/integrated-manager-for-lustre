DIRS = rest-api storage-plugin-api internals packaging scheduler-plugin-api

all: $(DIRS)

dist:
	mkdir -p dist

.PHONY: $(DIRS)
$(DIRS): dist
	make -C $@ html
	rm -rf dist/chroma-doc-$@
	cp -r $@/_build/html dist/chroma-doc-$@
	tar -C dist -czf dist/chroma-doc-$@.tar.gz chroma-doc-$@
