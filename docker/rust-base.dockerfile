FROM rust:1.39
WORKDIR /build
COPY . .
RUN apt update
RUN apt install -y clang libkmod-dev
RUN cargo build --release