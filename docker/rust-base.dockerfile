FROM rust:1.39
WORKDIR /build
COPY . .
RUN sudo apt install libkmod-dev
RUN cargo build --release