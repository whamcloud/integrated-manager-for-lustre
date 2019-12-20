FROM rust:1.40
WORKDIR /build
COPY . .
RUN cargo build --release