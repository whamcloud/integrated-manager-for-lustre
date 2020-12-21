use crate::{error::ImlApiError, graphql::Context};
use casbin::{prelude::Enforcer, CoreApi};
use iml_manager_client::{
    get_client, get_retry,
    header::{HeaderMap, HeaderValue},
    Client, ImlManagerClientError,
};
use iml_wire_types::Session;
use std::{str::from_utf8, sync::Arc};
use tokio::sync::Mutex;
use warp::reject::Reject;

#[derive(Debug, thiserror::Error)]
pub enum AuthorizationError {
    #[error(transparent)]
    Enforcer(#[from] casbin::Error),
    #[error("User is not authenticated")]
    Unauthenticated,
    #[error("User has no groups")]
    NoGroups,
    #[error("No active session present")]
    NoSession,
    #[error("Couldn't retrieve session id from cookies")]
    NoSessionId,
    #[error("No session cookie supplied")]
    NoSessionCookie,
    #[error("No credentials supplied")]
    NoCredentials,
    #[error(transparent)]
    Utf8Error(#[from] std::str::Utf8Error),
}

impl Reject for AuthorizationError {}

pub enum Credentials {
    SessionId(String),
    AuthorizationBearer(String),
}

pub(crate) fn get_session_id(
    cookies: &Option<String>,
) -> Result<Option<String>, AuthorizationError> {
    if let Some(cookies) = cookies {
        let string = from_utf8(cookies.as_bytes()).map_err(AuthorizationError::Utf8Error)?;
        tracing::debug!("Cookie: {}", string);
        let maybe_session_id = {
            string.split(';').map(|cookie| {
                let mut split = cookie.split_terminator('=');
                let key = split.next().map(|s| s.trim_start().trim_end());
                let value = split.next().map(|s| s.trim_start().trim_end());
                tracing::debug!("key: {:?}, value: {:?}", key, value);

                match (key, value) {
                    (Some("sessionid"), value) => {
                        return value;
                    }
                    (_, _) => {
                        return None;
                    }
                }
            })
        }
        .filter(|x| x.is_some())
        .next()
        .flatten()
        .map(Into::into);
        tracing::debug!("Session ID: {:?}", maybe_session_id);

        Ok(maybe_session_id)
    } else {
        Ok(None)
    }
}

pub(crate) async fn store_session(
    ctx: Arc<Mutex<Context>>,
    credentials: Credentials,
) -> Result<(), ImlApiError> {
    if (*ctx.lock().await).session.is_none() {
        match credentials {
            Credentials::SessionId(i) => {
                tracing::debug!("Session id: {:?}", i);

                let mut headers = HeaderMap::new();
                headers.insert(
                    "Cookie",
                    HeaderValue::from_str(format!("sessionid={}", i).as_ref()).map_err(|e| {
                        ImlApiError::ImlManagerClientError(
                            ImlManagerClientError::InvalidHeaderValue(e),
                        )
                    })?,
                );

                let client: Client = get_client().map_err(ImlApiError::ImlManagerClientError)?;
                let response: Session = get_retry(
                    client.clone(),
                    "session",
                    vec![("limit", "0")],
                    Some(&headers),
                )
                .await
                .map_err(ImlApiError::ImlManagerClientError)?;
                tracing::debug!("Session: {:?}", response);
                (*ctx.lock().await).session = Some(response.clone());
                Ok(())
            }
            Credentials::AuthorizationBearer(a) => {
                tracing::debug!("Authorization bearer: {:?}", a);

                let mut headers = HeaderMap::new();
                headers.insert(
                    "Authorization",
                    HeaderValue::from_str(a.as_ref()).map_err(|e| {
                        ImlApiError::ImlManagerClientError(
                            ImlManagerClientError::InvalidHeaderValue(e),
                        )
                    })?,
                );

                let client: Client = get_client().map_err(ImlApiError::ImlManagerClientError)?;
                let response: Session = get_retry(
                    client.clone(),
                    "session",
                    vec![("limit", "0")],
                    Some(&headers),
                )
                .await
                .map_err(ImlApiError::ImlManagerClientError)?;
                tracing::debug!("Session: {:?}", response);
                (*ctx.lock().await).session = Some(response.clone());
                Ok(())
            }
        }
    } else {
        Ok(())
    }
}

pub(crate) fn authorize(
    enforcer: &Enforcer,
    session: &Option<Session>,
    operation_name: &str,
) -> Result<bool, AuthorizationError> {
    if let Some(session) = session {
        let user = &session.user;

        if let Some(user) = user {
            let groups = &user.groups;

            if let Some(groups) = groups {
                let (authorizations, errors): (Vec<_>, Vec<_>) = groups
                    .iter()
                    .map(|g| {
                        let group_string = format!("{}", g.name);

                        tracing::debug!(
                            "User {} with group {} is authorizing for operation name {}",
                            user.id,
                            group_string,
                            operation_name,
                        );

                        match enforcer.enforce(vec![group_string.clone(), operation_name.into()]) {
                            Ok(authorized) => {
                                if authorized {
                                    tracing::debug!(
                                        "User {} with group {} is authorized for operation name {}",
                                        user.id,
                                        group_string,
                                        operation_name,
                                    );
                                    Ok(true)
                                } else {
                                    tracing::debug!(
                                        "User {} with group {} is NOT authorized for operation name {}",
                                        user.id,
                                        group_string,
                                        operation_name,
                                    );
                                    Ok(false)
                                }
                            }
                            Err(e) => {
                                tracing::error!("Error during authorization: {}", e);
                                Err(AuthorizationError::Enforcer(e))
                            }
                        }
                    })
                    .partition(Result::is_ok);

                if !errors.is_empty() {
                    let mut errors: Vec<_> = errors.into_iter().map(Result::unwrap_err).collect();
                    // We only return one error
                    Err(errors.pop().unwrap())
                } else {
                    let authorizations: Vec<_> =
                        authorizations.into_iter().map(Result::unwrap).collect();
                    // We collect authorizations for all groups the user is in.
                    // If the user is denied permission per one group, we deny access.
                    let final_authorization =
                        authorizations
                            .iter()
                            .fold(true, |acc, x| if !acc { acc } else { *x });
                    Ok(final_authorization)
                }
            } else {
                // User having no groups is most likely an error in our setup
                tracing::error!("No groups");
                Err(AuthorizationError::NoGroups)
            }
        } else {
            tracing::debug!("Unauthenticated");
            Err(AuthorizationError::Unauthenticated)
        }
    } else {
        tracing::debug!("No session");
        Err(AuthorizationError::NoSession)
    }
}
