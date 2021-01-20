FROM centos:8 as base-rust
WORKDIR /build
ARG toolchain=stable
RUN dnf update -y \
  && dnf install -y gcc openssl openssl-devel epel-release file diffutils pkgconfig \
  && dnf install -y libsodium libsodium-devel \
  && dnf clean all \
  && cd /root \
  && curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain $toolchain
ENV PATH $PATH:/root/.cargo/bin
ENV CARGO_HOME /root/.cargo
ENV RUSTUP_HOME /root/.rustup
ENV SODIUM_USE_PKG_CONFIG 1

FROM base-rust as mover
WORKDIR /build
RUN dnf install jq rsync -y
COPY . .
RUN cargo metadata --no-deps --offline --format-version 1 | jq '.workspace_members | .[]' | awk -F'[()]' '{gsub(/path\+file\:\/\/\/build\//, ""); print $2}' | xargs -I '{}' rsync -Raxuv '{}' rust-only/ \
  && mv Cargo.toml Cargo.lock sqlx-data.json migrations device-scanner/ rust-only/ 


FROM base-rust as planner
RUN cargo install cargo-chef --version 0.1.11
COPY --from=mover /build/rust-only/ .
RUN cargo chef prepare --recipe-path recipe.json

FROM base-rust as cacher
RUN cargo install cargo-chef --version 0.1.11
COPY --from=planner /build/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json

FROM base-rust as builder
COPY --from=mover /build/rust-only/ .
# Copy over the cached dependencies
COPY --from=cacher /build/target target
COPY --from=cacher $CARGO_HOME $CARGO_HOME
RUN cargo build --release