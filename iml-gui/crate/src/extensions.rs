use crate::auth::csrf_token;
use iml_wire_types::{GroupType, Session};
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
pub(crate) trait RequestExt {
    fn api_call(url: impl ToString) -> Self;
    fn with_auth(self: Self) -> Self;
}

impl RequestExt for fetch::Request {
    fn api_call(url: impl ToString) -> Self {
        Self::new(format!("/api/{}/", url.to_string()))
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
