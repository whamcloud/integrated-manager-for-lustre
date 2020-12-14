use crate::diff::Keyed;
use std::collections::HashMap;
use std::fmt::Display;
use std::hash::Hash;

const CROSS: &'_ str = " ├─";
const CORNER: &'_ str = " └─";
const VERTICAL: &'_ str = " │ ";
const SPACE: &'_ str = "   ";

const INIT_COLLAPSED: &'_ str = " ●";
const INIT_EXPANDED: &'_ str = " ○";
const END_COLLAPSED: &'_ str = "─●"; // ⊕
const END_EXPANDED: &'_ str = "─○"; // ⊙
const END_LEAF: &'_ str = "──";

pub trait HasState {
    type State: Clone + Default + Display + Ord;
    fn state(&self) -> Self::State;
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Node<K, T> {
    pub key: K,
    pub parent: Option<K>,
    pub deps: Vec<K>,
    pub custom: Custom<T>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Custom<T> {
    pub collapsed: bool,
    pub payload: T,
}

#[derive(Clone, Debug)]
pub struct Item<K, U, B> {
    pub key: K,
    pub indent: String,
    pub payload: U,
    pub indicator: Option<B>,
}

impl<K: Copy + PartialEq, U: PartialEq, B> Keyed for Item<K, U, B> {
    type Key = K;
    fn key(&self) -> Self::Key {
        self.key
    }
}

impl<K: Copy + PartialEq, U: PartialEq, B> PartialEq for Item<K, U, B> {
    fn eq(&self, other: &Self) -> bool {
        self.key == other.key && self.indent == other.indent && self.payload == other.payload
        // We do ignore self.indicator
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Tree<K: Eq + Hash, T> {
    pub roots: Vec<K>,
    pub pool: HashMap<K, Node<K, T>>,
}

impl<K: Copy + Eq + Hash, T: Clone + Eq + HasState> Default for Tree<K, T> {
    fn default() -> Self {
        Tree::new()
    }
}

impl<K: Copy + Eq + Hash, T: Clone + Eq + HasState> Tree<K, T> {
    pub fn new() -> Tree<K, T> {
        Tree {
            roots: Vec::new(),
            pool: HashMap::new(),
        }
    }

    pub fn add_child_node(&mut self, key: K, parent: Option<K>, custom: Custom<T>) -> K {
        // we must use the externally setup key
        let node = Node {
            key,
            parent,
            deps: Vec::new(),
            custom,
        };
        if let Some(p) = parent {
            if let Some(nr) = self.get_node_mut(p) {
                if !nr.deps.contains(&key) {
                    nr.deps.push(key);
                }
            }
        } else {
            self.roots.push(key);
        }
        self.pool.insert(key, node);
        key
    }

    pub fn merge_in(&mut self, mut other: Self) -> bool {
        // if there is any intersection, then ignore other
        if other.pool.keys().all(|k| !self.pool.contains_key(k)) {
            // roots are guaranteed to not intersect too
            self.roots.append(&mut other.roots);
            self.pool.extend(other.pool);
            true
        } else {
            false
        }
    }

    pub fn contains_key(&self, k: K) -> bool {
        self.pool.contains_key(&k)
    }

    fn get_node_mut(&mut self, k: K) -> Option<&mut Node<K, T>> {
        self.pool.get_mut(&k)
    }

    pub fn get_node(&self, k: K) -> Option<&Node<K, T>> {
        self.pool.get(&k)
    }

    pub fn get_custom_data_mut(&mut self, k: K) -> Option<&mut Custom<T>> {
        self.pool.get_mut(&k).map(|n| &mut n.custom)
    }

    pub fn len(&self) -> usize {
        self.pool.len()
    }

    pub fn is_empty(&self) -> bool {
        self.pool.is_empty()
    }

    pub fn get_roots(&self) -> Vec<&Node<K, T>> {
        self.roots
            .iter()
            .filter_map(|r| self.get_node(*r))
            .collect::<Vec<_>>()
    }

    pub fn get_path_from_root(&self, r: K) -> Vec<K> {
        let mut path = Vec::with_capacity(8);
        let mut cur = r;
        loop {
            if let Some(node) = self.get_node(cur) {
                path.push(cur);
                if let Some(pid) = node.parent {
                    cur = pid;
                    continue;
                }
            }
            break;
        }
        path.reverse();
        path
    }

    pub fn count_node_keys(&self, mut f: impl FnMut(&Node<K, T>) -> bool) -> usize {
        self.pool.values().filter(|n| f(*n)).map(|_| 1).sum()
    }

    pub fn keys_on_level(&self, level: i32) -> Vec<(K, <T as HasState>::State)> {
        fn calc_inner<K: Copy + Eq + Hash, T: Clone + Eq + HasState>(
            tree: &Tree<K, T>,
            node: &Node<K, T>,
            level: i32,
            pairs: &mut Vec<(K, <T as HasState>::State)>,
        ) -> (Option<K>, <T as HasState>::State) {
            let mut deps = Vec::with_capacity(if level > 0 { node.deps.len() } else { 0 });
            let mut state: <T as HasState>::State = Default::default();
            for cid in &node.deps {
                if let Some(child) = tree.get_node(*cid) {
                    let (child_id_opt, child_state) = calc_inner(tree, child, level - 1, pairs);
                    state = state.max(child_state);
                    if let Some(child_id) = child_id_opt {
                        deps.push(child_id);
                    }
                }
            }
            state = node.custom.payload.state().max(state);
            if level == 0 {
                pairs.push((node.key, state.clone()));
                (Some(node.key), state)
            } else {
                (None, state)
            }
        }
        let mut pairs = Vec::with_capacity(self.len());
        for root in self.get_roots() {
            calc_inner(self, root, level, &mut pairs);
        }
        pairs
    }

    pub fn render<U: From<T>, B>(&self) -> Vec<Item<K, U, B>> {
        fn calc_inner<K: Copy + Eq + Hash, T: Clone + Eq + HasState, U: From<T>, B>(
            tree: &Tree<K, T>,
            node: &Node<K, T>,
            indent: &str,
            shift: &str,
            term: &str,
            items: &mut Vec<Item<K, U, B>>,
        ) {
            items.push(Item {
                key: node.key,
                indent: format!("{}{}{}", indent, shift, term),
                payload: node.custom.payload.clone().into(),
                indicator: None,
            });
            if !node.custom.collapsed {
                for i in 0..node.deps.len() {
                    if let Some(child) = tree.get_node(node.deps[i]) {
                        let new_indent = match shift {
                            CROSS => format!("{}{}", indent, VERTICAL),
                            CORNER => format!("{}{}", indent, SPACE),
                            _ => "".into(),
                        };
                        let is_last = i == node.deps.len() - 1;
                        let new_shift = if is_last { CORNER } else { CROSS };
                        let new_term = if child.deps.is_empty() {
                            END_LEAF
                        } else if child.custom.collapsed {
                            END_COLLAPSED
                        } else {
                            END_EXPANDED
                        };
                        calc_inner(tree, child, &new_indent, &new_shift, &new_term, items);
                    }
                }
            }
        }
        let mut result = Vec::with_capacity(self.len());
        for root in self.get_roots() {
            let term = if root.deps.is_empty() || !root.custom.collapsed {
                INIT_EXPANDED
            } else {
                INIT_COLLAPSED
            };
            calc_inner(self, root, "", "", term, &mut result);
        }
        result
    }
}

pub fn iterate_items<K, U: Display + HasState, B>(
    items: &[Item<K, U, B>],
    mut call: impl FnMut(usize, String),
) {
    for (i, e) in items.iter().enumerate() {
        let s = format!("{} {} {}", e.indent, e.payload.state(), e.payload);
        call(i, s);
    }
}

pub fn print_items<K, U: Display + HasState, B>(items: &[Item<K, U, B>]) {
    iterate_items(items, |i, s| println!("{: <2}{}", i, s));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gen_tree::tests::State::*;
    use std::cmp::Ordering;
    use std::collections::HashSet;
    use std::fmt;
    use std::sync::atomic::AtomicI32;

    #[test]
    fn test_insert_nodes() {
        let mut tree = Tree::new();
        tree.add_child_node(
            1,
            None,
            Custom {
                collapsed: false,
                payload: Specific {
                    state: Progressing,
                    name: "a0".to_string(),
                },
            },
        );
        tree.add_child_node(
            2,
            Some(1),
            Custom {
                collapsed: false,
                payload: Specific {
                    state: Progressing,
                    name: "a00".to_string(),
                },
            },
        );
        tree.add_child_node(
            3,
            Some(1),
            Custom {
                collapsed: false,
                payload: Specific {
                    state: Progressing,
                    name: "a01".to_string(),
                },
            },
        );
        tree.add_child_node(
            4,
            None,
            Custom {
                collapsed: false,
                payload: Specific {
                    state: Progressing,
                    name: "a1".to_string(),
                },
            },
        );
        tree.add_child_node(
            5,
            Some(4),
            Custom {
                collapsed: false,
                payload: Specific {
                    state: Progressing,
                    name: "a10".to_string(),
                },
            },
        );
        tree.add_child_node(
            6,
            Some(4),
            Custom {
                collapsed: false,
                payload: Specific {
                    state: Progressing,
                    name: "a11".to_string(),
                },
            },
        );
        let f = NodeFactory::new(1);
        assert_eq!(
            tree,
            f.trees(vec![
                f.tree("a0", &[f.leaf("a00"), f.leaf("a01"),]).build(),
                f.tree("a1", &[f.leaf("a10"), f.leaf("a11"),]).build(),
            ])
        );
    }

    #[test]
    fn test_merge_in() {
        let f = NodeFactory::new(1);
        let tree0 = f.tree("a", &[f.leaf("a0"), f.leaf("a1")]).build();
        let tree1 = {
            let mut tree = f.tree("b", &[f.leaf("b0"), f.leaf("b1")]).build();
            tree.roots = vec![10];
            tree.replace_node_by_name("b", |n| {
                n.key = 10;
                n.parent = None;
                n.deps = vec![2, 3];
            });
            tree.replace_node_by_name("b0", |n| {
                n.key = 2;
                n.parent = Some(10);
                n.deps = vec![];
            });
            tree.replace_node_by_name("b1", |n| {
                n.key = 3;
                n.parent = Some(10);
                n.deps = vec![];
            });
            tree
        };
        let tree2 = {
            let mut tree = f.tree("c", &[f.leaf("c0"), f.leaf("c1")]).build();
            tree.roots = vec![1];
            tree.replace_node_by_name("c", |n| {
                n.key = 1;
                n.parent = None;
                n.deps = vec![2, 13];
            });
            tree.replace_node_by_name("c0", |n| {
                n.key = 2;
                n.parent = Some(1);
                n.deps = vec![];
            });
            tree.replace_node_by_name("c1", |n| {
                n.key = 13;
                n.parent = Some(1);
                n.deps = vec![];
            });
            tree
        };
        let tree3 = {
            let mut tree = f.tree("d", &[f.leaf("d0"), f.leaf("d1")]).build();
            tree.roots = vec![4];
            tree.replace_node_by_name("d", |n| {
                n.key = 4;
                n.parent = None;
                n.deps = vec![5, 6];
            });
            tree.replace_node_by_name("d0", |n| {
                n.key = 5;
                n.parent = Some(4);
                n.deps = vec![];
            });
            tree.replace_node_by_name("d1", |n| {
                n.key = 6;
                n.parent = Some(4);
                n.deps = vec![];
            });
            tree
        };
        assert!(tree0.is_valid());
        assert!(tree1.is_valid());
        assert!(tree2.is_valid());
        assert!(tree3.is_valid());

        let mut full_tree = Tree::new();
        full_tree.merge_in(tree0);
        full_tree.merge_in(tree1);
        full_tree.merge_in(tree2);
        full_tree.merge_in(tree3);
        assert!(full_tree.is_valid());
        // other trees have intersections with the current, so ignored
        let f = NodeFactory::new(1);
        assert_eq!(
            full_tree,
            f.trees(vec![
                f.tree("a", &[f.leaf("a0"), f.leaf("a1"),]).build(),
                f.tree("d", &[f.leaf("d0"), f.leaf("d1"),]).build(),
            ])
        );
    }

    #[test]
    fn test_reduce_to_level() {
        let nf = NodeFactory::new(1);
        let mut tree = nf
            .tree(
                "a",
                &[
                    nf.tree(
                        "b0",
                        &[
                            nf.tree(
                                "c00",
                                &[
                                    nf.leaf("d000"),
                                    nf.leaf("d001"),
                                    nf.leaf("d002"),
                                    nf.leaf("d003"),
                                ],
                            ),
                            nf.leaf("c01"),
                            nf.leaf("c02"),
                        ],
                    ),
                    nf.tree(
                        "b1",
                        &[
                            nf.leaf("c10"),
                            nf.leaf("c11"),
                            nf.tree(
                                "c12",
                                &[
                                    nf.leaf("d120"),
                                    nf.leaf("d121"),
                                    nf.leaf("d122"),
                                    nf.leaf("d123"),
                                ],
                            ),
                        ],
                    ),
                    nf.leaf("b3"),
                ],
            )
            .build();
        debug_assert!(tree.is_valid(), "tree should be valid");

        tree.get_node_mut_by_name("d001")
            .map(|n| n.custom.payload.state = Errored);

        let level0 = tree
            .keys_on_level(0)
            .into_iter()
            .map(|(k, s)| {
                (
                    tree.get_node(k)
                        .map(|n| &n.custom.payload.name[..])
                        .unwrap_or(""),
                    s,
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(level0, vec![("a", Errored)]);

        let level1 = tree
            .keys_on_level(1)
            .into_iter()
            .map(|(k, s)| {
                (
                    tree.get_node(k)
                        .map(|n| &n.custom.payload.name[..])
                        .unwrap_or(""),
                    s,
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            level1,
            vec![("b0", Errored), ("b1", Progressing), ("b3", Progressing)]
        );

        let level2 = tree
            .keys_on_level(2)
            .into_iter()
            .map(|(k, s)| {
                (
                    tree.get_node(k)
                        .map(|n| &n.custom.payload.name[..])
                        .unwrap_or(""),
                    s,
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            level2,
            vec![
                ("c00", Errored),
                ("c01", Progressing),
                ("c02", Progressing),
                ("c10", Progressing),
                ("c11", Progressing),
                ("c12", Progressing)
            ]
        );

        let level3 = tree
            .keys_on_level(3)
            .into_iter()
            .map(|(k, s)| {
                (
                    tree.get_node(k)
                        .map(|n| &n.custom.payload.name[..])
                        .unwrap_or(""),
                    s,
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            level3,
            vec![
                ("d000", Progressing),
                ("d001", Errored),
                ("d002", Progressing),
                ("d003", Progressing),
                ("d120", Progressing),
                ("d121", Progressing),
                ("d122", Progressing),
                ("d123", Progressing)
            ]
        );

        let level4 = tree
            .keys_on_level(4)
            .into_iter()
            .map(|(k, s)| {
                (
                    tree.get_node(k)
                        .map(|n| &n.custom.payload.name[..])
                        .unwrap_or(""),
                    s,
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(level4, vec![]);
    }

    impl Tree<i32, Specific> {
        fn get_node_mut_by_name(&mut self, name: &str) -> Option<&mut Node<i32, Specific>> {
            self.pool
                .values_mut()
                .find(|n| n.custom.payload.name == name)
        }

        fn replace_node_by_name(
            &mut self,
            name: &str,
            mut f: impl FnMut(&mut Node<i32, Specific>),
        ) {
            if let Some(k) = self
                .pool
                .values()
                .find(|n| n.custom.payload.name == name)
                .map(|n| n.key)
            {
                if let Some(mut n) = self.pool.remove(&k) {
                    f(&mut n);
                    self.pool.insert(n.key, n);
                }
            }
        }

        /// check if the tree is properly formed
        fn is_valid(&self) -> bool {
            fn unseen_ref<K: Copy + Eq + Hash>(seen: &mut HashSet<K>, r: K) -> Option<()> {
                if !seen.contains(&r) {
                    seen.insert(r);
                    Some(())
                } else {
                    None
                }
            }
            fn seen_ref<K: Copy + Eq + Hash>(seen: &mut HashSet<K>, r: K) -> Option<()> {
                if seen.contains(&r) {
                    Some(())
                } else {
                    None
                }
            }
            fn in_pool<K: Copy + Eq + Hash, T: Clone + Eq + HasState>(
                tree: &Tree<K, T>,
                r: K,
            ) -> Option<()> {
                if let Some(n) = tree.pool.get(&r) {
                    if n.key == r {
                        return Some(());
                    }
                }
                None
            }
            fn calc_inner<K: Copy + Eq + Hash, T: Clone + Eq + HasState>(
                tree: &Tree<K, T>,
                node: &Node<K, T>,
                seen: &mut HashSet<K>,
            ) -> Option<()> {
                unseen_ref(seen, node.key)?;
                in_pool(tree, node.key)?;
                if let Some(p) = node.parent {
                    seen_ref(seen, p)?;
                }
                for d in &node.deps {
                    if let Some(n) = tree.get_node(*d) {
                        calc_inner(tree, n, seen)?;
                    } else {
                        return None;
                    }
                }
                Some(())
            }
            let mut seen = HashSet::new();
            self.get_roots()
                .into_iter()
                .all(|root| calc_inner(self, root, &mut seen) == Some(()))
        }
    }

    // region Specific struct and State enum
    #[derive(Copy, Clone, Debug, Eq, PartialEq)]
    pub enum State {
        Progressing,
        Errored,
    }
    impl Default for State {
        fn default() -> Self {
            Self::Progressing
        }
    }

    impl Display for State {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            match self {
                Progressing => write!(f, "⠶"),
                Errored => write!(f, "✗"),
            }
        }
    }

    impl PartialOrd for State {
        fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
            Some(self.cmp(other))
        }
    }

    impl Ord for State {
        fn cmp(&self, other: &Self) -> Ordering {
            fn order(s: &State) -> u32 {
                match s {
                    State::Progressing => 0,
                    State::Errored => 3,
                }
            }
            Ord::cmp(&order(self), &order(other))
        }
    }

    #[derive(Clone, Debug, Eq, PartialEq)]
    struct Specific {
        state: State,
        name: String,
    }

    impl HasState for Specific {
        type State = State;

        fn state(&self) -> Self::State {
            self.state
        }
    }
    // endregion

    // region structs NodeFactory and NodeF
    #[derive(Debug)]
    pub struct NodeFactory {
        counter: AtomicI32,
    }

    impl Clone for NodeFactory {
        fn clone(&self) -> Self {
            Self {
                counter: AtomicI32::new(self.counter.load(std::sync::atomic::Ordering::SeqCst)),
            }
        }
    }

    impl NodeFactory {
        fn new(initial_id: i32) -> Self {
            Self {
                counter: AtomicI32::new(initial_id),
            }
        }
        fn leaf(&self, name: &str) -> NodeF {
            NodeF {
                counter: &self.counter,
                name: name.to_string(),
                deps: vec![],
            }
        }
        fn tree<'a>(&'a self, name: &str, deps: &[NodeF<'a>]) -> NodeF<'a> {
            NodeF {
                counter: &self.counter,
                name: name.to_string(),
                deps: deps.to_vec(),
            }
        }
        fn trees(&self, trees: Vec<Tree<i32, Specific>>) -> Tree<i32, Specific> {
            let mut full_tree = Tree::new();
            for tree in trees.into_iter() {
                full_tree.merge_in(tree);
            }
            full_tree
        }
    }

    #[derive(Clone, Debug)]
    struct NodeF<'a> {
        counter: &'a AtomicI32,
        name: String,
        deps: Vec<NodeF<'a>>,
    }

    impl<'a> NodeF<'a> {
        fn build(&self) -> Tree<i32, Specific> {
            fn build_node(nf: &NodeF, parent: Option<i32>, tree: &mut Tree<i32, Specific>) {
                let custom = Custom {
                    collapsed: false,
                    payload: Specific {
                        state: State::Progressing,
                        name: nf.name.to_string(),
                    },
                };
                let key = nf.counter.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                let new_parent = Some(key);
                tree.add_child_node(key, parent, custom);
                for child_node_f in nf.deps.iter() {
                    build_node(child_node_f, new_parent, tree);
                }
            }
            let mut tree = Tree::new();
            build_node(self, None, &mut tree);
            tree
        }
    }
    // endregion
}
