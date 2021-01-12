// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::auth::csrf_token;
use emf_wire_types::{GroupType, Session};
use seed::{fetch, prelude::*, *};

/// Extension methods for the Session API object.
pub(crate) trait SessionExt {
    /// Does the user need to login?
    fn needs_login(&self) -> bool;
    /// Does a logged in user exist?
    fn has_user(&self) -> bool;
    /// Does the user fall within the group?
    fn group_allowed(&self, group: GroupType) -> bool;
}

impl SessionExt for Session {
    fn needs_login(&self) -> bool {
        self.user.is_none() && !self.read_enabled
    }
    fn has_user(&self) -> bool {
        self.user.is_some()
    }
    fn group_allowed(&self, group: GroupType) -> bool {
        self.user
            .as_ref()
            .and_then(|x| x.groups.as_ref())
            .and_then(|xs| {
                xs.iter().find(|y| {
                    //Superusers can do everything.
                    if y.name == GroupType::Superusers {
                        return true;
                    }

                    //Filesystem administrators can do everything a filesystem user can do.
                    if y.name == GroupType::FilesystemAdministrators && group == GroupType::FilesystemUsers {
                        return true;
                    }

                    // Fallback to matching on names.
                    y.name == group
                })
            })
            .is_some()
    }
}

/// Extension methods for`fetch::Request`
pub(crate) trait RequestExt: Sized {
    fn api_call(path: impl ToString) -> Self;
    fn api_query(path: impl ToString, args: impl serde::Serialize) -> Result<Self, serde_urlencoded::ser::Error>;
    fn api_item(path: impl ToString, item: impl ToString) -> Self;
    fn graphql_query<T: serde::Serialize>(x: &T) -> Self;
    fn with_auth(self: Self) -> Self;
}

impl RequestExt for fetch::Request {
    fn api_call(path: impl ToString) -> Self {
        Self::new(format!("/api/{}/", path.to_string()))
    }
    fn api_query(path: impl ToString, args: impl serde::Serialize) -> Result<Self, serde_urlencoded::ser::Error> {
        let qs = format!("?{}", serde_urlencoded::to_string(args)?);

        Ok(Self::new(format!("/api/{}/{}", path.to_string(), qs)))
    }
    fn api_item(path: impl ToString, item: impl ToString) -> Self {
        Self::api_call(format!("{}/{}", path.to_string(), item.to_string()))
    }
    fn graphql_query<T: serde::Serialize>(x: &T) -> Self {
        Self::new("/graphql")
            .with_auth()
            .method(fetch::Method::Post)
            .send_json(x)
    }
    fn with_auth(self) -> Self {
        match csrf_token() {
            Some(csrf) => self.header("X-CSRFToken", &csrf),
            None => self,
        }
    }
}

/// Allows for merging attributes onto an existing item
pub(crate) trait MergeAttrs {
    fn merge_attrs(self, attrs: Attrs) -> Self;
}

impl MergeAttrs for Attrs {
    fn merge_attrs(mut self, attrs: Attrs) -> Self {
        self.merge(attrs);

        self
    }
}

impl<T> MergeAttrs for Node<T> {
    fn merge_attrs(self, attrs: Attrs) -> Self {
        if let Self::Element(mut el) = self {
            el.attrs.merge(attrs);

            Self::Element(el)
        } else {
            self
        }
    }
}

pub(crate) trait NodeExt<T> {
    fn with_listener(self, event_handler: EventHandler<T>) -> Self;
    fn with_style(self, key: impl Into<St>, val: impl Into<CSSValue>) -> Self;
}

impl<T> NodeExt<T> for Node<T> {
    fn with_listener(mut self, event_handler: EventHandler<T>) -> Self {
        self.add_listener(event_handler);

        self
    }
    fn with_style(mut self, key: impl Into<St>, val: impl Into<CSSValue>) -> Self {
        self.add_style(key, val);

        self
    }
}

/// Extension methods for`fetch::Request`
pub(crate) trait FailReasonExt {
    fn message(&self) -> String;
}

impl<T> FailReasonExt for fetch::FailReason<T> {
    fn message(&self) -> String {
        match self {
            Self::RequestError(err, _) => match err {
                fetch::RequestError::DomException(e) => e.message(),
            },
            Self::Status(status, _) => format!("Status: {}", status.code),
            Self::DataError(err, _) => match err {
                fetch::DataError::DomException(e) => e.message(),
                fetch::DataError::SerdeError(e, _) => format!("Serde error: {}", e),
            },
        }
    }
}

/// Extension methods for`seed::browser::url::Url`
pub(crate) trait UrlExt {
    /// Returns the path of the `Url`.
    /// This fn will account for
    /// the base (via the `base`) tag
    /// and remove it from the path
    fn get_path(&self) -> Vec<String>;
}

impl UrlExt for Url {
    fn get_path(&self) -> Vec<String> {
        let mut path = self.path.clone();

        let base = match crate::UI_BASE.as_ref() {
            Some(x) => x,
            None => return path,
        };

        let has_base = path.get(0).filter(|x| x == &base).is_some();

        if has_base {
            path.remove(0);
        }

        path
    }
}
