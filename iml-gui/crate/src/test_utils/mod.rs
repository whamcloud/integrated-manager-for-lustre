pub mod fixtures;

use seed::{
    app::{
        builder::{BeforeMount, MountType},
        types::{UpdateFn, ViewFn},
    },
    browser::{url::Url, util},
    virtual_dom::View,
};

#[cfg(test)]
fn before_mount(_: Url) -> BeforeMount {
    BeforeMount::new()
        .mount_point(util::body())
        .mount_type(MountType::Append)
}

#[cfg(test)]
/// Create a new app for test purposes.
///
/// The view is appended directly to the `body`.
///
/// This fn has the additional restriction that `Model` implements `Default`,
/// which may or may not be what you need.
pub(crate) fn create_app_simple<Ms, Mdl: Default, ElC: View<Ms> + 'static, GMs: 'static>(
    update: UpdateFn<Ms, Mdl, ElC, GMs>,
    view: ViewFn<Mdl, ElC>,
) -> seed::App<Ms, Mdl, ElC, GMs> {
    seed::App::builder(update, view)
        .before_mount(before_mount)
        .build_and_start()
}
