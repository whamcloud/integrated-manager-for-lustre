// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{alert_indicator, attrs, font_awesome, paging, tooltip, Placement},
    generated::css_classes::C,
    get_target_from_managed_target,
    route::RouteId,
    GMsg, Route,
};
use iml_wire_types::{
    db::{Id, ManagedTargetRecord, OstPoolRecord, TargetKind, VolumeNodeRecord},
    warp_drive::{ArcCache, ArcValuesExt, RecordId},
    Filesystem, Host, Label,
};
use seed::{prelude::*, *};
use std::{
    borrow::Borrow,
    collections::{BTreeSet, HashMap},
    iter::{once, FromIterator},
    ops::{Deref, DerefMut},
    sync::Arc,
};

fn sort_by_label(xs: &mut Vec<impl Label>) {
    xs.sort_by(|a, b| natord::compare(a.label(), b.label()));
}

pub fn slice_page<'a>(paging: &paging::Model, xs: &'a BTreeSet<i32>) -> impl Iterator<Item = &'a i32> {
    xs.iter().skip(paging.offset()).take(paging.end())
}

fn sorted_cache<'a>(x: &'a im::HashMap<i32, Arc<impl Label + Id>>) -> impl Iterator<Item = i32> + 'a {
    let mut xs: Vec<_> = x.values().collect();

    xs.sort_by(|a, b| natord::compare(a.label(), b.label()));

    xs.into_iter().map(|x| x.id())
}

fn get_volume_nodes_by_host_id(xs: &im::HashMap<i32, Arc<VolumeNodeRecord>>, host_id: i32) -> Vec<&VolumeNodeRecord> {
    xs.arc_values().filter(|v| v.host_id == host_id).collect()
}

fn get_ost_pools_by_fs_id(xs: &im::HashMap<i32, Arc<OstPoolRecord>>, fs_id: i32) -> Vec<&OstPoolRecord> {
    xs.arc_values().filter(|v| v.filesystem_id == fs_id).collect()
}

fn get_targets_by_parent_resource(
    cache: &ArcCache,
    parent_resource_id: RecordId,
    kind: TargetKind,
) -> Vec<&ManagedTargetRecord> {
    match parent_resource_id {
        RecordId::OstPool(x) => get_targets_by_pool_id(cache, x),
        RecordId::Filesystem(x) => get_targets_by_fs_id(cache, x, kind),
        _ => vec![],
    }
}

fn get_targets_by_pool_id(cache: &ArcCache, ostpool_id: i32) -> Vec<&ManagedTargetRecord> {
    let target_ids: Vec<_> = cache
        .ost_pool_osts
        .arc_values()
        .filter(|x| x.ostpool_id == ostpool_id)
        .map(|x| x.managedost_id)
        .collect();

    cache
        .target
        .arc_values()
        .filter(|x| target_ids.contains(&x.id))
        .collect()
}

fn get_targets_by_fs_id(cache: &ArcCache, fs_id: i32, kind: TargetKind) -> Vec<&ManagedTargetRecord> {
    let fs = cache.filesystem.get(&fs_id);

    cache
        .target
        .arc_values()
        .filter(|t| t.get_kind() == kind)
        .filter_map(|x| {
            let t = get_target_from_managed_target(cache, x)?;

            if t.filesystems.contains(fs?.name.borrow()) {
                Some(x)
            } else {
                None
            }
        })
        .collect()
}

fn get_target_fs_ids(cache: &ArcCache, x: &ManagedTargetRecord) -> Vec<i32> {
    get_target_from_managed_target(cache, x)
        .map(|x| -> Vec<_> { x.filesystems.iter().map(|x| x.as_str()).collect() })
        .iter()
        .flatten()
        .filter_map(|x| cache.filesystem.values().find(|y| &y.name == x))
        .map(|x| x.id)
        .collect()
}

// Model

#[derive(Debug, Eq, PartialEq, Hash, PartialOrd, Ord, Clone, Copy)]
pub enum Step {
    HostCollection,
    Host(i32),
    VolumeCollection,
    FsCollection,
    Fs(i32),
    MgtCollection,
    MdtCollection,
    OstPoolCollection,
    OstPool(i32),
    OstCollection,
}

impl From<TargetKind> for Step {
    fn from(target_kind: TargetKind) -> Self {
        match target_kind {
            TargetKind::Mgt => Self::MgtCollection,
            TargetKind::Mdt => Self::MdtCollection,
            TargetKind::Ost => Self::OstCollection,
        }
    }
}

#[derive(Debug, Default, Eq, PartialEq, PartialOrd, Ord, Hash, Clone)]
pub struct Address(BTreeSet<Step>);

impl Address {
    fn new(path: impl IntoIterator<Item = Step>) -> Self {
        Self(BTreeSet::from_iter(path))
    }
    fn extend(&self, step: impl Into<Step>) -> Self {
        Self::new(self.iter().copied().chain(once(step.into())))
    }
    fn as_vec(&self) -> Vec<Step> {
        self.iter().copied().collect()
    }
}

impl Deref for Address {
    type Target = BTreeSet<Step>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl From<Vec<Step>> for Address {
    fn from(xs: Vec<Step>) -> Self {
        Self::new(xs)
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct TreeNode {
    open: bool,
    items: BTreeSet<i32>,
    paging: paging::Model,
}

impl TreeNode {
    fn from_items(xs: impl IntoIterator<Item = i32>) -> Self {
        let items = BTreeSet::from_iter(xs);

        Self {
            open: false,
            paging: paging::Model::new(items.len()),
            items,
        }
    }
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Model(HashMap<Address, TreeNode>);

impl Deref for Model {
    type Target = HashMap<Address, TreeNode>;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl DerefMut for Model {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.0
    }
}

impl Model {
    fn reset(&mut self) {
        self.0 = HashMap::new();
    }
    fn remove_item(&mut self, addr: &Address, id: i32) {
        if let Some(tree_node) = self.get_mut(addr) {
            tree_node.items.remove(&id);
            tree_node.paging.total -= 1;
        }
    }
}

// Update

fn add_item(
    record_id: RecordId,
    cache: &ArcCache,
    model: &mut Model,
    orders: &mut impl Orders<Msg, GMsg>,
) -> Option<()> {
    match record_id {
        RecordId::Host(id) => {
            let addr: Address = vec![Step::HostCollection].into();

            let tree_node = model.get_mut(&addr)?;

            tree_node.items = sorted_cache(&cache.host).collect();
            tree_node.paging.total = tree_node.items.len();

            orders.send_msg(Msg::AddEmptyNode(addr.extend(Step::Host(id))));
        }
        RecordId::Filesystem(id) => {
            let addr: Address = vec![Step::FsCollection].into();

            let tree_node = model.get_mut(&addr)?;

            tree_node.items = sorted_cache(&cache.filesystem).collect();
            tree_node.paging.total = tree_node.items.len();

            orders.send_msg(Msg::AddEmptyNode(addr.extend(Step::Fs(id))));
        }
        RecordId::VolumeNode(id) => {
            let vn = cache.volume_node.get(&id)?;

            let tree_node =
                model.get_mut(&vec![Step::HostCollection, Step::Host(vn.host_id), Step::VolumeCollection].into())?;

            tree_node.items.insert(id);

            let mut xs = cache
                .volume_node
                .arc_values()
                .filter(|y| tree_node.items.contains(&y.id))
                .collect();

            sort_by_label(&mut xs);

            tree_node.items = xs.into_iter().map(|x| x.id).collect();
            tree_node.paging.total = tree_node.items.len();
        }
        RecordId::OstPoolOsts(id) => {
            let ost_pool_ost = cache.ost_pool_osts.get(&id)?;
            let ost_pool = cache.ost_pool.get(&ost_pool_ost.ostpool_id)?;

            let tree_node = model.get_mut(
                &vec![
                    Step::FsCollection,
                    Step::Fs(ost_pool.filesystem_id),
                    Step::OstPoolCollection,
                    Step::OstPool(ost_pool.id),
                ]
                .into(),
            )?;

            tree_node.items.insert(id);

            let mut xs = cache
                .ost_pool
                .arc_values()
                .filter(|y| tree_node.items.contains(&y.id))
                .collect();

            sort_by_label(&mut xs);

            tree_node.items = xs.into_iter().map(|x| x.id).collect();
            tree_node.paging.total = tree_node.items.len();
        }
        RecordId::Target(id) => {
            let target = cache.target.get(&id)?;

            let ids = get_target_fs_ids(cache, target);

            let sort_fn = |cache: &ArcCache, model: &TreeNode| {
                let mut xs = cache
                    .target
                    .arc_values()
                    .filter(|y| model.items.contains(&y.id))
                    .collect();

                sort_by_label(&mut xs);

                xs.into_iter().map(|x| x.id).collect()
            };

            for fs_id in ids {
                let base_addr: Address = vec![Step::FsCollection, Step::Fs(fs_id)].into();

                let target_tree_node = model.get_mut(&base_addr.extend(target.get_kind()))?;

                target_tree_node.items.insert(id);

                target_tree_node.items = sort_fn(cache, target_tree_node);
                target_tree_node.paging.total = target_tree_node.items.len();

                let ostcolletion_node =
                    model.get_mut(&base_addr.extend(Step::OstPoolCollection).extend(Step::OstCollection))?;

                ostcolletion_node.items.insert(id);

                ostcolletion_node.items = sort_fn(cache, ostcolletion_node);
                ostcolletion_node.paging.total = ostcolletion_node.items.len();
            }
        }
        _ => {}
    };

    Some(())
}

fn remove_item(
    record_id: RecordId,
    cache: &ArcCache,
    model: &mut Model,
    orders: &mut impl Orders<Msg, GMsg>,
) -> Option<()> {
    match record_id {
        RecordId::Host(id) => {
            let addr: Address = vec![Step::HostCollection].into();

            model.remove_item(&addr, id);

            orders.send_msg(Msg::RemoveNode(addr.extend(Step::Host(id))));
        }
        RecordId::Filesystem(id) => {
            let addr: Address = vec![Step::FsCollection].into();

            model.remove_item(&addr, id);

            orders.send_msg(Msg::RemoveNode(addr.extend(Step::Fs(id))));
        }
        RecordId::VolumeNode(id) => {
            let vn = cache.volume_node.get(&id)?;

            model.remove_item(
                &vec![Step::HostCollection, Step::Host(vn.host_id), Step::VolumeCollection].into(),
                id,
            );
        }
        RecordId::OstPoolOsts(id) => {
            let ost_pool_ost = cache.ost_pool_osts.get(&id)?;
            let ost_pool = cache.ost_pool.get(&ost_pool_ost.ostpool_id)?;

            let addr: Address = vec![
                Step::FsCollection,
                Step::Fs(ost_pool.filesystem_id),
                Step::OstPoolCollection,
            ]
            .into();

            model.remove_item(&addr, ost_pool.id);

            orders.send_msg(Msg::RemoveNode(addr.extend(Step::OstPool(ost_pool.id))));
        }
        RecordId::Target(id) => {
            let target = cache.target.get(&id)?;

            let ids = get_target_fs_ids(cache, target);

            for fs_id in ids {
                let addr: Address = vec![Step::FsCollection, Step::Fs(fs_id)].into();

                model.remove_item(&addr.extend(target.get_kind()), id);

                model.remove_item(&addr.extend(Step::OstPoolCollection).extend(Step::OstCollection), id);
            }
        }
        _ => {}
    };

    Some(())
}

#[derive(Clone, Debug)]
pub enum Msg {
    Add(RecordId),
    Remove(RecordId),
    Reset,
    Toggle(Address, bool),
    AddEmptyNode(Address),
    RemoveNode(Address),
    Page(Address, paging::Msg),
}

pub fn update(cache: &ArcCache, msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Reset => {
            model.reset();

            // Add hosts
            model.insert(
                vec![Step::HostCollection].into(),
                TreeNode::from_items(sorted_cache(&cache.host)),
            );

            // Add fs
            model.insert(
                vec![Step::FsCollection].into(),
                TreeNode::from_items(sorted_cache(&cache.filesystem)),
            );
        }
        Msg::Add(id) => {
            add_item(id, cache, model, orders);
        }
        Msg::Remove(id) => {
            remove_item(id, cache, model, orders);
        }
        Msg::Toggle(address, open) => {
            let tree_node = match model.get_mut(&address) {
                Some(x) => x,
                None => return,
            };

            tree_node.open = open;

            let paging: Vec<_> = tree_node.items.iter().copied().collect();

            match address.as_vec().as_slice() {
                [Step::HostCollection] => {
                    paging.into_iter().for_each(|x| {
                        model
                            .entry(address.extend(Step::Host(x)))
                            .or_insert_with(TreeNode::default);
                    });
                }
                [Step::HostCollection, Step::Host(id)] => {
                    model.entry(address.extend(Step::VolumeCollection)).or_insert_with(|| {
                        let mut xs = get_volume_nodes_by_host_id(&cache.volume_node, *id);

                        sort_by_label(&mut xs);

                        TreeNode::from_items(xs.into_iter().map(|x| x.id))
                    });
                }
                [Step::FsCollection] => {
                    paging.into_iter().for_each(|x| {
                        model
                            .entry(address.extend(Step::Fs(x)))
                            .or_insert_with(TreeNode::default);
                    });
                }
                [Step::FsCollection, Step::Fs(id)] => {
                    model.entry(address.extend(Step::MgtCollection)).or_insert_with(|| {
                        let mut xs = get_targets_by_fs_id(cache, *id, TargetKind::Mgt);

                        sort_by_label(&mut xs);

                        TreeNode::from_items(xs.into_iter().map(|x| x.id))
                    });

                    model.entry(address.extend(Step::MdtCollection)).or_insert_with(|| {
                        let mut xs = get_targets_by_fs_id(cache, *id, TargetKind::Mdt);

                        sort_by_label(&mut xs);

                        TreeNode::from_items(xs.into_iter().map(|x| x.id))
                    });

                    model.entry(address.extend(Step::OstCollection)).or_insert_with(|| {
                        let mut xs = get_targets_by_fs_id(cache, *id, TargetKind::Ost);

                        sort_by_label(&mut xs);

                        TreeNode::from_items(xs.into_iter().map(|x| x.id))
                    });

                    model.entry(address.extend(Step::OstPoolCollection)).or_insert_with(|| {
                        let mut xs = get_ost_pools_by_fs_id(&cache.ost_pool, *id);

                        sort_by_label(&mut xs);

                        TreeNode::from_items(xs.into_iter().map(|x| x.id))
                    });
                }
                [Step::FsCollection, Step::Fs(_), Step::OstPoolCollection] => {
                    paging.into_iter().for_each(|x| {
                        model
                            .entry(address.extend(Step::OstPool(x)))
                            .or_insert_with(TreeNode::default);
                    });
                }
                [Step::FsCollection, Step::Fs(_), Step::OstPoolCollection, Step::OstPool(pool_id)] => {
                    model.entry(address.extend(Step::OstCollection)).or_insert_with(|| {
                        let mut xs =
                            get_targets_by_parent_resource(cache, RecordId::OstPool(*pool_id), TargetKind::Ost);

                        sort_by_label(&mut xs);

                        TreeNode::from_items(xs.into_iter().map(|x| x.id))
                    });
                }
                _ => {}
            };
        }
        Msg::AddEmptyNode(addr) => {
            model.insert(addr, TreeNode::default());
        }
        Msg::RemoveNode(id) => {
            model.remove(&id);
        }
        Msg::Page(id, msg) => {
            if let Some(x) = model.get_mut(&id) {
                paging::update(msg, &mut x.paging, &mut orders.proxy(|msg| Msg::Page(id, msg)))
            }
        }
    }
}

// View
fn toggle_view(address: Address, is_open: bool) -> Node<Msg> {
    let mut toggle = font_awesome(
        class![
            C.select_none,
            C.hover__text_gray_300,
            C.cursor_pointer,
            C.w_5,
            C.h_4,
            C.inline,
            C.mr_1,
            C._mt_1
        ],
        "chevron-right",
    );

    toggle.add_listener(mouse_ev(Ev::Click, move |_| Msg::Toggle(address, !is_open)));

    if is_open {
        toggle.add_style(St::Transform, "rotate(90deg)");
    }

    toggle
}

fn item_view(icon: &str, label: &str, route: Route) -> Node<Msg> {
    a![
        class![C.hover__underline, C.hover__text_gray_300, C.mr_1, C.break_all],
        attrs! {
            At::Href => route.to_href()
        },
        font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], icon),
        label
    ]
}

fn item_label_view(icon: &str, label: &str, _: Route) -> Node<Msg> {
    span![
        class![C.mr_1, C.break_all],
        font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], icon),
        label
    ]
}

fn tree_host_item_view(cache: &ArcCache, model: &Model, host: &Host) -> Option<Node<Msg>> {
    let address = Address::new(vec![Step::HostCollection, Step::Host(host.id)]);

    let tree_node = model.get(&address)?;

    Some(li![
        class![C.py_1],
        toggle_view(address.clone(), tree_node.open),
        item_view("server", &host.label, Route::Server(host.id.into())),
        a![
            class![C.hover__underline, C.text_blue_500, C.hover__text_blue_400, C.mr_1],
            attrs! {
                At::Href => Route::ServerDashboard(host.nodename.to_string().into()).to_href()
            },
            attrs::container(),
            tooltip::view(&"View statistics", Placement::Bottom),
            font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], "chart-bar"),
        ],
        alert_indicator(&cache.active_alert, &host, true, Placement::Top),
        if tree_node.open {
            tree_volume_collection_view(cache, model, &address, host)
        } else {
            empty![]
        }
    ])
}

fn tree_pool_item_view(cache: &ArcCache, model: &Model, address: &Address, pool: &OstPoolRecord) -> Option<Node<Msg>> {
    let address = address.extend(Step::OstPool(pool.id));

    let tree_node = model.get(&address)?;

    Some(li![
        class![C.py_1],
        toggle_view(address.clone(), tree_node.open),
        item_label_view("swimming-pool", pool.label(), Route::OstPool(pool.id.into())),
        if tree_node.open {
            tree_target_collection_view(cache, model, &address, TargetKind::Ost)
        } else {
            empty![]
        }
    ])
}

fn tree_fs_item_view(cache: &ArcCache, model: &Model, fs: &Filesystem) -> Option<Node<Msg>> {
    let address = Address::new(vec![Step::FsCollection, Step::Fs(fs.id)]);

    let tree_node = model.get(&address)?;

    Some(li![
        class![C.py_1],
        toggle_view(address.clone(), tree_node.open),
        item_view("server", &fs.label, Route::Filesystem(fs.id.into())),
        a![
            class![C.hover__underline, C.text_blue_500, C.hover__text_blue_400, C.mr_1],
            attrs! {
                At::Href => Route::FsDashboard(fs.name.to_string().into()).to_href()
            },
            attrs::container(),
            tooltip::view(&"View statistics", Placement::Bottom),
            font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], "chart-bar"),
        ],
        alert_indicator(&cache.active_alert, &fs, true, Placement::Bottom),
        if tree_node.open {
            vec![
                tree_target_collection_view(cache, model, &address, TargetKind::Mgt),
                tree_target_collection_view(cache, model, &address, TargetKind::Mdt),
                tree_target_collection_view(cache, model, &address, TargetKind::Ost),
                tree_pools_collection_view(cache, model, &address),
            ]
        } else {
            vec![]
        }
    ])
}

fn tree_collection_view(
    model: &Model,
    address: Address,
    item: impl FnOnce(&TreeNode) -> Node<Msg>,
    on_open: impl FnOnce(&TreeNode) -> Vec<Node<Msg>>,
) -> Option<Node<Msg>> {
    let x = model.get(&address)?;

    let el = ul![
        class![C.px_6, C.mt_2],
        toggle_view(address.clone(), x.open),
        item(x),
        if x.open {
            ul![
                class![C.px_6, C.mt_2],
                on_open(x),
                li![
                    class![C.py_1],
                    paging::next_prev_view(&x.paging).map_msg(move |msg| { Msg::Page(address, msg) })
                ]
            ]
        } else {
            empty![]
        }
    ];

    Some(el)
}

fn tree_fs_collection_view(cache: &ArcCache, model: &Model) -> Node<Msg> {
    tree_collection_view(
        model,
        Address::new(vec![Step::FsCollection]),
        |x| {
            item_view(
                "folder",
                &format!("Filesystems ({})", x.paging.total()),
                Route::Filesystems,
            )
        },
        |x| {
            slice_page(&x.paging, &x.items)
                .filter_map(|x| cache.filesystem.get(x))
                .filter_map(|x| tree_fs_item_view(cache, model, x))
                .collect()
        },
    )
    .unwrap_or(empty![])
}

fn tree_host_collection_view(cache: &ArcCache, model: &Model) -> Node<Msg> {
    tree_collection_view(
        model,
        Address::new(vec![Step::HostCollection]),
        |x| item_view("folder", &format!("Servers ({})", x.paging.total()), Route::Servers),
        |x| {
            slice_page(&x.paging, &x.items)
                .filter_map(|x| cache.host.get(x))
                .filter_map(|x| tree_host_item_view(cache, model, x))
                .collect()
        },
    )
    .unwrap_or(empty![])
}

fn tree_pools_collection_view(cache: &ArcCache, model: &Model, parent_address: &Address) -> Node<Msg> {
    let addr = parent_address.extend(Step::OstPoolCollection);

    tree_collection_view(
        model,
        addr.clone(),
        |x| item_label_view("folder", &format!("OST Pools ({})", x.paging.total()), Route::OstPools),
        |x| {
            slice_page(&x.paging, &x.items)
                .filter_map(|x| cache.ost_pool.get(x))
                .filter_map(|x| tree_pool_item_view(cache, model, &addr, x))
                .collect()
        },
    )
    .unwrap_or(empty![])
}

fn tree_volume_collection_view(cache: &ArcCache, model: &Model, parent_address: &Address, host: &Host) -> Node<Msg> {
    tree_collection_view(
        model,
        parent_address.extend(Step::VolumeCollection),
        |x| {
            item_view(
                "folder",
                &format!("Volumes ({})", x.paging.total()),
                Route::ServerVolumes(RouteId::from(&host.id)),
            )
        },
        |x| {
            slice_page(&x.paging, &x.items)
                .filter_map(|x| cache.volume_node.get(x))
                .map(|x| {
                    let v = cache.volume.values().find(|v| v.id == x.volume_id).unwrap();

                    let size = match v.size {
                        Some(x) => format!(" ({})", number_formatter::format_bytes(x as f64, None)),
                        None => "".into(),
                    };

                    li![
                        class![C.py_1],
                        item_label_view("hdd", &format!("{}{}", x.label(), size), Route::Volume(v.id.into())),
                    ]
                })
                .collect()
        },
    )
    .unwrap_or(empty![])
}

fn tree_target_collection_view(
    cache: &ArcCache,
    model: &Model,
    parent_address: &Address,
    kind: TargetKind,
) -> Node<Msg> {
    let label = match kind {
        TargetKind::Mgt => "MGTs",
        TargetKind::Mdt => "MDTs",
        TargetKind::Ost => "OSTs",
    };

    tree_collection_view(
        model,
        parent_address.extend(kind),
        |x| {
            if kind == TargetKind::Mgt {
                item_view("folder", &format!("{} ({})", label, x.paging.total()), Route::Mgt)
            } else {
                item_label_view("folder", &format!("{} ({})", label, x.paging.total()), Route::Targets)
            }
        },
        |x| {
            slice_page(&x.paging, &x.items)
                .filter_map(|x| cache.target.get(x))
                .map(|x| {
                    li![
                        class![C.py_1],
                        item_view("bullseye", x.label(), Route::Target(x.id.into())),
                        a![
                            class![C.hover__underline, C.text_blue_500, C.hover__text_blue_400, C.mr_1],
                            attrs! {
                                At::Href => Route::TargetDashboard(x.label().into()).to_href()
                            },
                            attrs::container(),
                            tooltip::view(&"View statistics", Placement::Bottom),
                            font_awesome(class![C.w_5, C.h_4, C.inline, C.mr_1, C._mt_1], "chart-bar"),
                        ],
                        alert_indicator(&cache.active_alert, &x, true, Placement::Bottom),
                    ]
                })
                .collect()
        },
    )
    .unwrap_or(empty![])
}

pub fn view(cache: &ArcCache, model: &Model) -> Node<Msg> {
    div![
        class![C.py_5, C.text_gray_500],
        tree_host_collection_view(cache, model),
        tree_fs_collection_view(cache, model),
    ]
}

#[cfg(test)]
mod tests {
    use super::{update, Address, GMsg, Model, Msg, Step};
    use crate::test_utils::{create_app_simple, fixtures};
    use iml_wire_types::warp_drive::ArcCache;
    use seed::virtual_dom::Node;
    use wasm_bindgen_test::*;

    wasm_bindgen_test_configure!(run_in_browser);

    fn create_app() -> seed::App<Msg, Model, Node<Msg>, GMsg> {
        create_app_simple(
            |msg, model, orders| {
                let cache: ArcCache = (&fixtures::get_cache()).into();
                update(&cache, msg, model, orders);
            },
            |_| seed::empty(),
        )
    }

    #[wasm_bindgen_test]
    fn test_default_model() {
        let app = create_app();

        let model = app.data.model.borrow();

        assert_eq!(model.as_ref(), Some(&Model::default()));
    }

    #[wasm_bindgen_test]
    fn test_model_reset() {
        let app = create_app();

        app.update(Msg::Reset);

        let model = app.data.model.borrow();

        let mut expected = vec![
            Address::new(vec![Step::HostCollection]),
            Address::new(vec![Step::FsCollection]),
        ];
        expected.sort();

        // note: keys() returns elements in arbitrary order
        let mut actual: Vec<_> = model.as_ref().unwrap().keys().cloned().collect();
        actual.sort();

        assert_eq!(actual, expected);
    }
}
