use iml_wire_types::Conf;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::Filter;

#[tokio::main]
async fn main() {
    let addr = iml_manager_env::get_iml_api_addr();

    let conf = Conf {
        allow_anonymous_read: iml_manager_env::get_allow_anonymous_read(),
        build: iml_manager_env::get_build(),
        version: iml_manager_env::get_version(),
        is_release: iml_manager_env::get_is_release(),
    };

    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let routes = warp::path("conf").map(move || warp::reply::json(&conf));

    tracing::info!("Starting on {:?}", addr);

    warp::serve(routes.with(warp::log("iml-api")))
        .run(addr)
        .await;
}
