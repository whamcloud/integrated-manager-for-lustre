FROM ubuntu:20.04

RUN echo 'APT:Install-Recommends "false";' > /etc/apt/apt.conf.d/00no-recommends.conf
RUN echo 'APT::Get::Assume-Yes "true";'  > /etc/apt/apt.conf.d/00yes.conf

ENV DEBIAN_FRONTEND noninteractive
RUN apt update && apt install devscripts reprepro debhelper build-essential curl

ENV HOME /home/build
RUN useradd --home-dir $HOME --create-home --shell /bin/bash build
USER build
WORKDIR $HOME

ENV CARGO_HOME $HOME/.cargo
ENV PATH $PATH:$HOME/.cargo/bin
ENV RUSTUP_HOME $HOME/.rustup

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable

CMD sleep infinity
