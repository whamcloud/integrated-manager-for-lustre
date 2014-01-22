
all: api storage_plugin internals packaging scheduler-plugin-api

dist:
	mkdir -p dist

.PHONY: api
api: dist/
	pushd rest-api &&\
	rm -rf _build &&\
	make html &&\
	popd
	rm -rf dist/chroma-doc-rest-api
	cp -r rest-api/_build/html dist/chroma-doc-rest-api
	pushd dist ;\
	tar czf chroma-doc-rest-api.tar.gz chroma-doc-rest-api

.PHONY: storage_plugin
storage_plugin: dist/
	pushd storage-plugin-api &&\
	rm -rf _build &&\
	make html &&\
	popd
	rm -rf dist/storage-plugin-api
	cp -r storage-plugin-api/_build/html dist/chroma-doc-storage-plugin-api
	pushd dist ;\
	tar czf chroma-doc-storage-plugin-api.tar.gz chroma-doc-storage-plugin-api

.PHONY: internals
internals: dist/
	pushd internals &&\
	rm -rf _build &&\
	make html &&\
	popd
	rm -rf dist/internals
	cp -r internals/_build/html dist/chroma-doc-internals
	pushd dist ;\
	tar czf chroma-doc-internals.tar.gz chroma-doc-internals

.PHONY: packaging
packaging: dist/
	pushd packaging &&\
	rm -rf _build &&\
	make html &&\
	popd
	rm -rf dist/packaging
	cp -r packaging/_build/html dist/chroma-doc-packaging
	pushd dist ;\
	tar czf chroma-doc-packaging.tar.gz chroma-doc-packaging

.PHONY: scheduler-plugin-api
scheduler-plugin-api: dist
	make -C $@ html
	rm -rf dist/chroma-doc-$@
	cp -r $@/_build/html dist/chroma-doc-$@
	tar -C dist -czf dist/chroma-doc-$@.tar.gz chroma-doc-$@
