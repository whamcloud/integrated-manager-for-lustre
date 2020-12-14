use casbin::prelude::*;
use iml_manager_client::header::{HeaderMap, HeaderValue, AUTHORIZATION};
use std::{collections::HashMap, convert::Infallible, str::from_utf8, sync::Arc};
use tokio::sync::RwLock;
use warp::{
    header::headers_cloned,
    hyper::Method,
    method,
    path::{full, FullPath},
    Filter, Rejection,
};

const BEARER_PREFIX: &str = "Bearer ";

pub const MODEL_PATH: &str = "./auth_model.conf";
pub const POLICY_PATH: &str = "./policy.csv";

pub type UserMap = Arc<RwLock<HashMap<String, User>>>;
pub type Sessions = Arc<RwLock<HashMap<String, String>>>;
pub type WebResult<T> = std::result::Result<T, Rejection>;
pub type MyResult<T> = std::result::Result<T, Error>;
pub type SharedEnforcer = Arc<Enforcer>;

#[derive(Clone)]
pub struct UserCtx {
    pub user_id: String,
    pub token: String,
}

#[derive(Clone)]
pub struct User {
    pub user_id: String,
    pub name: String,
    pub role: String,
}

#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error("error")]
    SomeError(),
    #[error("no authorization header found")]
    NoAuthHeaderFoundError,
    #[error("wrong authorization header format")]
    InvalidAuthHeaderFormatError,
    #[error("no user found for this token")]
    InvalidTokenError,
    #[error("error during authorization")]
    AuthorizationError,
    #[error("user is not unauthorized")]
    UnauthorizedError,
    #[error("no user found with this name")]
    UserNotFoundError,
}

impl warp::reject::Reject for Error {}

pub fn create_user_map() -> HashMap<String, User> {
    let mut map = HashMap::new();
    map.insert(
        String::from("21"),
        User {
            user_id: String::from("21"),
            name: String::from("herbert"),
            role: String::from("member"),
        },
    );
    map.insert(
        String::from("100"),
        User {
            user_id: String::from("100"),
            name: String::from("sibylle"),
            role: String::from("admin"),
        },
    );
    map.insert(
        String::from("1"),
        User {
            user_id: String::from("1"),
            name: String::from("gordon"),
            role: String::from("anonymous"),
        },
    );
    map
}

pub fn with_auth(
    enforcer: SharedEnforcer,
    user_map: UserMap,
    sessions: Sessions,
) -> impl Filter<Extract = (UserCtx,), Error = Rejection> + Clone {
    full()
        .and(headers_cloned())
        .and(method())
        .map(
            move |path: FullPath, headers: HeaderMap<HeaderValue>, method: Method| {
                (
                    path,
                    enforcer.clone(),
                    headers,
                    method,
                    user_map.clone(),
                    sessions.clone(),
                )
            },
        )
        .and_then(user_authentication)
}

pub async fn user_authentication(
    args: (
        FullPath,
        SharedEnforcer,
        HeaderMap<HeaderValue>,
        Method,
        UserMap,
        Sessions,
    ),
) -> WebResult<UserCtx> {
    let (path, enforcer, headers, method, user_map, sessions) = args;

    let token = token_from_header(&headers).map_err(|e| warp::reject::custom(e))?;
    let user_id = match sessions.read().await.get(&token) {
        Some(v) => v.clone(),
        None => return Err(warp::reject::custom(Error::InvalidTokenError)),
    };
    let user = match user_map.read().await.get(&user_id) {
        Some(v) => v.clone(),
        None => return Err(warp::reject::custom(Error::InvalidTokenError)),
    };
    match enforcer.enforce((&user.role.as_str(), &path.as_str(), &method.as_str())) {
        Ok(authorized) => {
            if authorized {
                Ok(UserCtx {
                    user_id: user.user_id,
                    token,
                })
            } else {
                Err(warp::reject::custom(Error::UnauthorizedError))
            }
        }
        Err(e) => {
            eprintln!("error during authorization: {}", e);
            Err(warp::reject::custom(Error::AuthorizationError))
        }
    }
}

pub fn token_from_header(headers: &HeaderMap<HeaderValue>) -> MyResult<String> {
    let header = match headers.get(AUTHORIZATION) {
        Some(v) => v,
        None => return Err(Error::NoAuthHeaderFoundError),
    };
    let auth_header = match from_utf8(header.as_bytes()) {
        Ok(v) => v,
        Err(_) => return Err(Error::NoAuthHeaderFoundError),
    };
    if !auth_header.starts_with(BEARER_PREFIX) {
        return Err(Error::InvalidAuthHeaderFormatError);
    }
    let without_prefix = auth_header.trim_start_matches(BEARER_PREFIX);
    Ok(without_prefix.to_owned())
}

pub fn with_user_map(
    user_map: UserMap,
) -> impl Filter<Extract = (UserMap,), Error = Infallible> + Clone {
    warp::any().map(move || user_map.clone())
}

pub fn with_sessions(
    sessions: Sessions,
) -> impl Filter<Extract = (Sessions,), Error = Infallible> + Clone {
    warp::any().map(move || sessions.clone())
}
