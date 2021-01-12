FROM rust as rust-remover
WORKDIR /build
RUN apt-get update -y \
  && apt-get install jq -y
COPY . .
RUN cargo metadata --no-deps --offline --format-version 1 | jq '.workspace_members | .[]' | awk -F'[()]' '{gsub(/path\+file\:\/\//, ""); print $2}' | xargs rm -rf \
  && rm -rf Cargo.{toml,lock} emf-gui/ device-scanner/

FROM centos:8 as builder
WORKDIR /build
RUN dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm rpmdevtools make git \
  && dnf module disable -y postgresql \
  && dnf install -y python2 python2-pip python2-devel postgresql96 openssl gcc-c++
RUN python2 -m pip install --upgrade pip==20.3.3 setuptools wheel
COPY --from=rust-remover /build/ .
RUN make base.repo
COPY --from=rust-remover /build/requirements.txt .
RUN pip install --user -r requirements.txt

FROM centos:8
WORKDIR /usr/share/chroma-manager/
ENV HTTPS_FRONTEND_PORT 7443
ENV DB_HOST postgres
ENV DB_PORT 5432
ENV AMQP_BROKER_HOST rabbit
ENV SERVER_FQDN nginx
ENV LOG_PATH .
ENV EMF_API_HOST emf-api
ENV PATH=/root/.local/bin:$PATH
RUN dnf update -y \
  && dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
  && dnf module disable -y postgresql \
  && dnf install -y python2 postgresql96 openssl \
  && dnf clean all
COPY --from=builder /root/.local/ /root/.local
COPY --from=rust-remover /build/ .
COPY --from=builder /build/base.repo .
COPY docker/wait-for-dependencies-postgres.sh /usr/local/bin/
ENTRYPOINT [ "wait-for-dependencies-postgres.sh" ]
