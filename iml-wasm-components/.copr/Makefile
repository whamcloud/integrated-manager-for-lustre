 /build/.cargo/bin/rustup:
	cd /tmp; \
	wget https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init; \
	chmod +x rustup-init; \
	./rustup-init -y; \
	/build/.cargo/bin/cargo install wasm-bindgen-cli;

srpm: /build/.cargo/bin/rustup
	mkdir -p /tmp/_topdir/SOURCES
	mkdir -p /tmp/scratch
	cp -r /build/Cargo.toml /build/Cargo.lock /build/iml-action-dropdown /build/iml-wasm-components.spec /tmp/scratch
	cd /tmp/scratch; \
	/build/.cargo/bin/rustup default stable; \
	/build/.cargo/bin/rustup target add wasm32-unknown-unknown; \
	/build/.cargo/bin/cargo build --target wasm32-unknown-unknown --release; \
	mkdir -p /tmp/package; \
	/build/.cargo/bin/wasm-bindgen /tmp/scratch/target/wasm32-unknown-unknown/release/iml_action_dropdown.wasm --no-modules --out-dir /tmp/package --out-name package; \
	cd /tmp; \
	tar cvf /tmp/_topdir/SOURCES/iml-wasm-components.tar package

	rpmbuild -bs --define "_topdir /tmp/_topdir" /tmp/scratch/iml-wasm-components.spec

	cp -r /tmp/_topdir/SRPMS/* $(outdir)

.PHONY: srpm