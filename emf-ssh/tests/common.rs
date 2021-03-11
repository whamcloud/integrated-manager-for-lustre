use emf_ssh::Client;
use futures::{
    future::{abortable, AbortHandle},
    Future, FutureExt,
};
use std::collections::hash_map::HashMap;
use std::{net::ToSocketAddrs, pin::Pin, sync::Arc};
use thrussh::*;
use thrussh::{
    client::Handle,
    server::{self, Auth, Config, Session},
    ChannelId, CryptoVec,
};
use thrussh_keys::*;
use tokio::{
    io::{AsyncReadExt, BufReader, DuplexStream},
    net::TcpListener,
    process::Command,
    sync::oneshot::{Receiver, Sender},
};

const PKCS8_ENCRYPTED: &'static str = r#"-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACCmVb6tBlMo6SdejfzD7tKef+cd9ffpqH0qUcsj0JdwFQAAAJgvS+h6L0vo
egAAAAtzc2gtZWQyNTUxOQAAACCmVb6tBlMo6SdejfzD7tKef+cd9ffpqH0qUcsj0JdwFQ
AAAECX2qbiNLy1bWr6ju5C0k7hX+pLcPU2yzFtDczxiaJsi6ZVvq0GUyjpJ16N/MPu0p5/
5x319+mofSpRyyPQl3AVAAAAFXNvbWVvbmVAc29tZXBsYWNlLmNvbQ==
-----END OPENSSH PRIVATE KEY-----"#;

pub fn start_server() -> Receiver<()> {
    let (server, server_rx) = setup_server();

    tokio::spawn(async move {
        let _ = server.await;
    });

    server_rx
}

pub async fn connect() -> Result<Handle<Client>, emf_ssh::Error> {
    emf_ssh::connect(
        "127.0.0.1",
        2222,
        "root",
        emf_ssh::Auth::Password("abc123".into()),
    )
    .await
}

pub async fn read_into_buffer(
    reader: &mut BufReader<DuplexStream>,
    mut buffer: String,
    tx: Sender<String>,
) {
    reader.read_to_string(&mut buffer).await.unwrap();
    tx.send(buffer).unwrap();
}

fn setup_server() -> (
    impl Future<Output = Result<(), std::io::Error>>,
    Receiver<()>,
) {
    let key = decode_secret_key(PKCS8_ENCRYPTED, None).unwrap();

    let mut config = thrussh::server::Config::default();
    config.connection_timeout = Some(std::time::Duration::from_secs(30));
    config.auth_rejection_time = std::time::Duration::from_secs(3);
    config.methods = MethodSet::PASSWORD;
    config.keys.push(key);
    let config = Arc::new(config);
    let sh = Server {
        handles: HashMap::new(),
    };
    let (tx, rx) = tokio::sync::oneshot::channel::<()>();

    (run(config, "0.0.0.0:2222", sh, tx), rx)
}

/// Run a server.
/// Create a new `Connection` from the server's configuration. This is a modification
/// of the crate's version of `run` since it does not indicate when the server has
/// been bound to an address.
async fn run<H: thrussh::server::Server + Send + 'static>(
    config: Arc<Config>,
    addr: &str,
    mut server: H,
    tx: Sender<()>,
) -> Result<(), std::io::Error> {
    let addr = addr.to_socket_addrs().unwrap().next().unwrap();
    let socket = TcpListener::bind(&addr).await?;
    tx.send(()).unwrap();

    if config.maximum_packet_size > 65535 {
        panic!(
            "Maximum packet size ({:?}) should not larger than a TCP packet (65535)",
            config.maximum_packet_size
        );
    }

    while let Ok((socket, _)) = socket.accept().await {
        let config = config.clone();
        let server = server.new(socket.peer_addr().ok());
        tokio::spawn(thrussh::server::run_stream(config, socket, server));
    }

    Ok(())
}

#[derive(Clone)]
struct Server {
    handles: HashMap<ChannelId, AbortHandle>,
}

impl server::Server for Server {
    type Handler = Self;
    fn new(&mut self, _: Option<std::net::SocketAddr>) -> Self {
        let s = self.clone();

        self.handles = HashMap::new();
        s
    }
}

impl server::Handler for Server {
    type Error = anyhow::Error;
    type FutureAuth = futures::future::Ready<Result<(Self, server::Auth), anyhow::Error>>;
    type FutureUnit = Pin<Box<dyn Future<Output = Result<(Self, Session), Self::Error>> + Send>>;
    type FutureBool = futures::future::Ready<Result<(Self, Session, bool), anyhow::Error>>;

    fn finished_auth(self, auth: Auth) -> Self::FutureAuth {
        futures::future::ready(Ok((self, auth)))
    }
    fn finished_bool(self, b: bool, s: Session) -> Self::FutureBool {
        futures::future::ready(Ok((self, s, b)))
    }
    fn finished(self, s: Session) -> Self::FutureUnit {
        async { Ok((self, s)) }.boxed()
    }
    fn signal(
        mut self,
        channel: ChannelId,
        signal_name: Sig,
        mut session: Session,
    ) -> Self::FutureUnit {
        match signal_name {
            Sig::KILL => {
                if let Some(handle) = self.handles.remove(&channel) {
                    handle.abort();
                }

                session.exit_status_request(channel, 2)
            }
            _ => {}
        }

        self.finished(session)
    }
    fn exec_request(
        mut self,
        channel: ChannelId,
        data: &[u8],
        mut session: Session,
    ) -> Self::FutureUnit {
        let cmd = std::str::from_utf8(&data).unwrap().to_string();

        async move {
            let allowed_commands = vec!["echo", "ls", "sleep"];
            let cmd_name = cmd.split(" ").take(1).next().unwrap().trim();

            if allowed_commands.iter().find(|x| x == &&cmd_name).is_some() {
                let cmd_args = cmd.split(" ").skip(1).collect::<Vec<&str>>();

                let mut c = Command::new(cmd_name);
                c.args(cmd_args);

                let mut h = session.handle();
                let mut h2 = h.clone();
                let (abortable, handle) = abortable(async move {
                    let out = c.output().await.unwrap();

                    let stdout = std::str::from_utf8(&out.stdout).unwrap().trim().to_string();
                    let stderr = std::str::from_utf8(&out.stderr).unwrap().trim().to_string();

                    if !stdout.is_empty() {
                        let v = CryptoVec::from_slice(&format!("stdout: {}", stdout).as_bytes());
                        h.data(channel, v).await.unwrap();
                    } else if !stderr.is_empty() {
                        let v = CryptoVec::from_slice(&format!("stderr: {}", stderr).as_bytes());
                        h.extended_data(channel, 1, v).await.unwrap();
                    }

                    h.exit_status_request(channel, out.status.code().unwrap() as u32)
                        .await
                        .unwrap();
                });

                tokio::spawn(async move {
                    if abortable.await.is_err() {
                        h2.exit_status_request(channel, 2).await.unwrap();
                    };
                });

                self.handles.insert(channel, handle);
            }

            Ok::<(Self, Session), Self::Error>((self, session))
        }
        .boxed()
    }
    fn auth_password(self, _: &str, password: &str) -> Self::FutureAuth {
        if password == "abc123" {
            self.finished_auth(server::Auth::Accept)
        } else {
            self.finished_auth(server::Auth::Reject)
        }
    }
}
