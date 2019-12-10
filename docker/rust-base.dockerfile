FROM rust:1.39
WORKDIR /build
COPY . .
RUN cargo build --release