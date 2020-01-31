FROM rust:1.41
WORKDIR /build
COPY . .
RUN cargo build --release