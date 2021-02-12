// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_tracing::tracing;
use futures::{future::BoxFuture, stream, FutureExt, TryStreamExt};
use std::{io, path::PathBuf, string::FromUtf8Error, sync::Arc, time::Duration};
use thrussh::client;
pub use thrussh::client::{Channel, Handle};

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error(transparent)]
    Anyhow(#[from] anyhow::Error),
    #[error(transparent)]
    ClientError(#[from] ClientError),
    #[error(transparent)]
    Io(#[from] io::Error),
    #[error(transparent)]
    FromUtf8(#[from] FromUtf8Error),
    #[error(transparent)]
    SshError(#[from] thrussh::Error),
    #[error(transparent)]
    SshKeyError(#[from] thrussh_keys::Error),
    #[error("SSH Authentication Failed")]
    AuthenticationFailed,
    #[error("No home directory found")]
    NoHomeDir,
    #[error("No .ssh directory found")]
    NoSshDir,
    #[error("Command Failed. Exit Code: {0}. Message: {1}")]
    FailedCmd(u32, String),
}

/// Various ways to Authenticate the SSH client
#[derive(Debug, Clone)]
pub enum Auth {
    /// Use the ssh-agent if one is available.
    Agent,
    /// Use password based authentication
    Password(String),
    /// Use a given private key with optional passphrase
    Key {
        key_path: String,
        password: Option<String>,
    },
    /// Read and try keys out of the `~/.ssh.` directory.
    /// Currently only reads id_rsa
    Auto,
}

/// Connect to the given `host` on the given `port` with the given `user` and selected `auth`.
/// A successful connection will return a session that can be used to obtain a channel.
pub async fn connect(
    host: impl ToString,
    port: impl Into<Option<u16>>,
    user: impl ToString,
    auth: Auth,
) -> Result<client::Handle<Client>, Error> {
    let cfg = client::Config {
        connection_timeout: Some(Duration::from_secs(60)),
        ..Default::default()
    };
    let cfg = Arc::new(cfg);

    let port = port.into();

    let host = host.to_string();

    let user = user.to_string();

    let address = format!("{}:{}", &host, port.unwrap_or(22));

    let sh = Client { host, port };

    let mut session: Handle<Client> = client::connect(cfg, address, sh).await?;

    let (session, authed) = match auth {
        Auth::Password(password) => {
            let x = session.authenticate_password(&user, password).await?;

            (session, x)
        }
        Auth::Key { key_path, password } => {
            let password = password.map(Vec::from);
            let password = password.as_deref();

            let keypair = thrussh_keys::load_secret_key(key_path, password)?;

            let x = session
                .authenticate_publickey(&user, Arc::new(keypair))
                .await?;

            (session, x)
        }
        Auth::Agent => {
            let mut agent = thrussh_keys::agent::client::AgentClient::connect_env().await?;

            let identities = agent.request_identities().await?;

            let (_, session, x) = stream::iter(identities.into_iter().map(Ok::<_, Error>))
                .try_fold(
                    (agent, session, false),
                    |(agent, mut session, authed), x| {
                        let user = &user;

                        async move {
                            if authed {
                                return Ok((agent, session, authed));
                            }

                            let (agent, authed) = session.authenticate_future(user, x, agent).await;
                            let authed = authed.map_err(|_| Error::AuthenticationFailed)?;

                            Ok((agent, session, authed))
                        }
                    },
                )
                .await?;

            (session, x)
        }
        Auth::Auto => {
            let dir = if let Some(mut ssh_dir) = dirs::home_dir() {
                ssh_dir.push(".ssh");

                ssh_dir
            } else {
                return Err(Error::NoHomeDir);
            };

            if !emf_fs::dir_exists(&dir).await {
                return Err(Error::NoSshDir);
            }

            let mut authed = false;

            for k in &["id_rsa"] {
                let k = dir.join(k);

                if !emf_fs::file_exists(&k).await {
                    continue;
                }

                let keypair = thrussh_keys::load_secret_key(k, None)?;

                authed = session
                    .authenticate_publickey(&user, Arc::new(keypair))
                    .await?;

                if authed {
                    break;
                }
            }

            (session, authed)
        }
    };

    if authed {
        Ok(session)
    } else {
        Err(Error::AuthenticationFailed)
    }
}

#[derive(Debug)]
pub struct Output {
    pub exit_status: Option<u32>,
    pub stdout: String,
    pub stderr: String,
}

impl Output {
    pub fn success(&self) -> bool {
        self.exit_status == Some(0)
    }
}

pub trait SshHandleExt<Client> {
    fn create_channel(&mut self) -> BoxFuture<Result<Channel, Error>>;
    /// Send a file to the remote path using this session
    fn push_file(
        &mut self,
        from: impl Into<PathBuf> + std::marker::Send,
        to: impl Into<PathBuf> + std::marker::Send,
    ) -> BoxFuture<Result<(), Error>>;
    /// Send the `AsyncRead` item to the remote path using this session
    fn stream_file<'a, R: 'a + tokio::io::AsyncReadExt + std::marker::Unpin + std::marker::Send>(
        &'a mut self,
        data: R,
        to: impl Into<PathBuf>,
    ) -> BoxFuture<'a, Result<(), Error>>;
}

impl SshHandleExt<Client> for Handle<Client> {
    fn create_channel(&mut self) -> BoxFuture<Result<Channel, Error>> {
        let fut = self.channel_open_session();

        Box::pin(async move {
            let ch = fut.await?;

            Ok(ch)
        })
    }
    fn push_file(
        &mut self,
        from: impl Into<PathBuf>,
        to: impl Into<PathBuf>,
    ) -> BoxFuture<Result<(), Error>> {
        let from = from.into();
        let to = to.into();

        async move {
            let mut ch = self.create_channel().await?;

            ch.push_file(from, to).await
        }
        .boxed()
    }
    fn stream_file<'a, R: 'a + tokio::io::AsyncReadExt + std::marker::Unpin + std::marker::Send>(
        &'a mut self,
        data: R,
        to: impl Into<PathBuf>,
    ) -> BoxFuture<'a, Result<(), Error>> {
        let to = to.into();

        async move {
            let mut ch = self.create_channel().await?;

            ch.stream_file(data, to).await
        }
        .boxed()
    }
}

pub trait SshChannelExt {
    /// Execute a remote command. Stdout and stderr will be buffered and returned
    /// As well as any exit code.
    fn exec_cmd(
        &mut self,
        cmd: impl ToString + std::fmt::Debug,
    ) -> BoxFuture<Result<Output, Error>>;
    /// Send a file to the remote path using this channel
    fn push_file(
        &mut self,
        from: impl Into<PathBuf> + std::fmt::Debug,
        to: impl Into<PathBuf> + std::fmt::Debug,
    ) -> BoxFuture<Result<(), Error>>;
    /// Send the `AsyncRead` item to the remote path using this channel
    fn stream_file<'a, R: 'a + tokio::io::AsyncReadExt + std::marker::Unpin + std::marker::Send>(
        &'a mut self,
        data: R,
        to: impl Into<PathBuf> + std::fmt::Debug,
    ) -> BoxFuture<'a, Result<(), Error>>;
}

impl SshChannelExt for Channel {
    #[tracing::instrument(skip(self))]
    fn push_file(
        &mut self,
        from: impl Into<PathBuf> + std::fmt::Debug,
        to: impl Into<PathBuf> + std::fmt::Debug,
    ) -> BoxFuture<Result<(), Error>> {
        let from = from.into();
        let to = to.into();

        async move {
            let f = tokio::fs::File::open(from).await?;

            self.stream_file(f, to).await
        }
        .boxed()
    }
    #[tracing::instrument(skip(self, data))]
    fn stream_file<'a, R: 'a + tokio::io::AsyncReadExt + std::marker::Unpin + std::marker::Send>(
        &'a mut self,
        data: R,
        to: impl Into<PathBuf> + std::fmt::Debug,
    ) -> BoxFuture<'a, Result<(), Error>> {
        let to = to.into();

        async move {
            let fut = self.exec(true, format!("cat - > {}", to.to_string_lossy()));

            fut.await?;

            self.data(data).await?;

            self.eof().await?;

            let mut exit_status = 1;
            let mut err_buf = vec![];

            while let Some(msg) = self.wait().await {
                match msg {
                    thrussh::ChannelMsg::ExitStatus { exit_status: x } => {
                        exit_status = x;
                    }
                    thrussh::ChannelMsg::ExtendedData { ref data, ext } => {
                        if ext == 1 {
                            data.write_all_from(0, &mut err_buf)?;
                        }
                    }
                    x => {
                        tracing::debug!("Got ssh ChannelMsg {:?}", x);
                    }
                }
            }

            if exit_status != 0 {
                Err(Error::FailedCmd(
                    exit_status,
                    format!(
                        "Could not stream data to {}. Error: {}",
                        to.to_string_lossy(),
                        String::from_utf8_lossy(&err_buf)
                    ),
                ))
            } else {
                Ok(())
            }
        }
        .boxed()
    }
    #[tracing::instrument(skip(self))]
    fn exec_cmd(
        &mut self,
        cmd: impl ToString + std::fmt::Debug,
    ) -> BoxFuture<Result<Output, Error>> {
        let cmd = cmd.to_string();

        async move {
            let fut = self.exec(true, cmd);
            fut.await?;

            let mut out_buf = vec![];
            let mut err_buf = vec![];

            let mut exit_status = None;

            while let Some(msg) = self.wait().await {
                match msg {
                    thrussh::ChannelMsg::Data { ref data } => {
                        data.write_all_from(0, &mut out_buf)?;
                    }
                    thrussh::ChannelMsg::ExtendedData { ref data, ext } => {
                        if ext == 1 {
                            data.write_all_from(0, &mut err_buf)?;
                        }
                    }
                    thrussh::ChannelMsg::ExitStatus { exit_status: x } => {
                        exit_status.replace(x);
                    }
                    x => {
                        tracing::debug!("Got ssh ChannelMsg {:?}", x);
                    }
                }
            }

            let out = Output {
                exit_status,
                stdout: String::from_utf8(out_buf)?,
                stderr: String::from_utf8(err_buf)?,
            };

            Ok(out)
        }
        .boxed()
    }
}

pub struct Client {
    pub host: String,
    pub port: Option<u16>,
}

#[derive(Debug, thiserror::Error)]
pub enum ClientError {
    #[error(transparent)]
    Anyhow(#[from] anyhow::Error),
    #[error(transparent)]
    SshError(#[from] thrussh::Error),
    #[error(transparent)]
    FromUtf8(#[from] FromUtf8Error),
}

impl client::Handler for Client {
    type Error = ClientError;
    type FutureUnit = futures::future::Ready<Result<(Self, client::Session), Self::Error>>;
    type FutureBool = futures::future::Ready<Result<(Self, bool), Self::Error>>;

    fn finished_bool(self, b: bool) -> Self::FutureBool {
        futures::future::ready(Ok((self, b)))
    }
    fn finished(self, session: client::Session) -> Self::FutureUnit {
        futures::future::ready(Ok((self, session)))
    }
    fn check_server_key(
        self,
        server_public_key: &thrussh_keys::key::PublicKey,
    ) -> Self::FutureBool {
        let r =
            thrussh_keys::check_known_hosts(&self.host, self.port.unwrap_or(22), server_public_key);

        match r {
            Ok(x) => {
                if !x {
                    tracing::warn!("Server key not found in known_hosts file");
                }

                self.finished_bool(true)
            }
            Err(thrussh_keys::Error::KeyChanged { line: x }) => {
                tracing::error!(
                    "Server Key for host: {} has changed on line {} of known_hosts file",
                    &self.host,
                    x
                );

                self.finished_bool(false)
            }
            _ => {
                tracing::warn!("Unknown error for host: {}, {:?}", &self.host, r);

                self.finished_bool(true)
            }
        }
    }
}
