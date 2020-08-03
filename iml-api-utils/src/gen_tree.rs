use crate::diff::{AlignmentOp, Keyed, Side};
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

// Used to set upper limit in calculating path to the root
// to avoid infinite walk when going from parent to parent in the tree.
const MAX_LEVEL: usize = 256;

pub trait HasState {
    type State: Clone + Default + Display + Ord;
    fn state(&self) -> Self::State;
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Node<K, T> {
    pub key: K,
    pub parent: Option<K>,
    pub collapsed: bool,
    pub deps: Vec<K>,
    pub value: T,
}

#[derive(Clone, Debug)]
pub struct Item<K, U, B> {
    pub id: K,
    pub indent: String,
    pub value: U,
    pub indicator: Option<B>,
}

impl<K: Copy + PartialEq, U: PartialEq, B> Keyed for Item<K, U, B> {
    type Key = K;
    fn key(&self) -> Self::Key {
        self.id
    }
}

impl<K: Copy + PartialEq, U: PartialEq, B> PartialEq for Item<K, U, B> {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id && self.indent == other.indent && self.value == other.value
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

    pub fn with_nodes(roots: Vec<K>, pool: HashMap<K, Node<K, T>>) -> Tree<K, T> {
        Tree { roots, pool }
    }

    pub fn add_child_node(&mut self, parent: Option<K>, mut node: Node<K, T>) -> K {
        // we must use the externally setup key
        let k = node.key;
        node.parent = parent;
        if let Some(p) = parent {
            if let Some(nr) = self.get_node_mut(p) {
                if !nr.deps.contains(&k) {
                    nr.deps.push(k);
                }
            }
        } else {
            self.roots.push(k);
        }
        self.pool.insert(k, node);
        k
    }

    pub fn merge_in(&mut self, other: &mut Self) {
        self.roots.append(&mut other.roots);
        // TODO make it without the clone()
        let pool = other.pool.clone();
        self.pool.extend(pool);
    }

    pub fn contains_key(&self, k: K) -> bool {
        self.pool.contains_key(&k)
    }

    pub fn get_node_mut(&mut self, k: K) -> Option<&mut Node<K, T>> {
        self.pool.get_mut(&k)
    }

    pub fn get_node(&self, k: K) -> Option<&Node<K, T>> {
        self.pool.get(&k)
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
        let mut path = Vec::with_capacity(MAX_LEVEL);
        let mut cur = r;
        for _ in 0..MAX_LEVEL {
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
            state = node.value.state().max(state);
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
                id: node.key,
                indent: format!("{}{}{}", indent, shift, term),
                value: node.value.clone().into(),
                indicator: None,
            });
            if !node.collapsed {
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
                        } else if child.collapsed {
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
            let term = if root.deps.is_empty() || !root.collapsed {
                INIT_EXPANDED
            } else {
                INIT_COLLAPSED
            };
            calc_inner(self, root, "", "", term, &mut result);
        }
        result
    }
}

pub fn apply_diff<K: Clone, U: Clone, B: Clone>(
    xs: &mut Vec<Item<K, U, B>>,
    ys: &mut Vec<Item<K, U, B>>,
    diff: &[AlignmentOp],
    mut create_indi: impl FnMut(usize, &Item<K, U, B>) -> B,
    mut update_indi: impl FnMut(usize, &B, &Item<K, U, B>),
    mut remove_indi: impl FnMut(usize, &B),
) {
    let mut di = 0i32;
    let mut dj = 0i32;
    for d in diff {
        match d {
            AlignmentOp::Insert(Side::Left, i, j) => {
                let i0 = (*i as i32 + di) as usize;
                let j0 = (*j as i32 + dj) as usize;
                let mut y = ys[j0].clone();
                let indi = create_indi(i0, &y);
                y.indicator = Some(indi);
                xs.insert(i0, y);
                di += 1;
            }
            AlignmentOp::Replace(Side::Left, i, j) => {
                let i0 = (*i as i32 + di) as usize;
                let j0 = (*j as i32 + dj) as usize;
                let y = ys[j0].clone();
                if let Some(indi) = &xs[i0].indicator {
                    update_indi(i0, &indi, &y)
                }
                xs[i0].id = y.id;
                xs[i0].indent = y.indent;
                xs[i0].value = y.value;
            }
            AlignmentOp::Delete(Side::Left, i) => {
                let i0 = (*i as i32 + di) as usize;
                if let Some(indi) = &xs[i0].indicator {
                    remove_indi(i0, indi)
                }
                xs.remove(i0);
                di -= 1;
            }
            AlignmentOp::Insert(Side::Right, i, j) => {
                let i0 = (*i as i32 + di) as usize;
                let j0 = (*j as i32 + dj) as usize;
                ys.insert(j0, xs[i0].clone());
                dj += 1;
            }
            AlignmentOp::Replace(Side::Right, i, j) => {
                let i0 = (*i as i32 + di) as usize;
                let j0 = (*j as i32 + dj) as usize;
                ys[j0] = xs[i0].clone();
            }
            AlignmentOp::Delete(Side::Right, j) => {
                let j0 = (*j as i32 + dj) as usize;
                ys.remove(j0);
                dj -= 1;
            }
        }
    }
}

pub fn iterate_items<K, U: Display + HasState, B>(
    items: &[Item<K, U, B>],
    mut call: impl FnMut(usize, String),
) {
    for (i, e) in items.iter().enumerate() {
        let s = format!("{} {} {}", e.indent, e.value.state(), e.value);
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
    use std::fmt;
    use std::sync::atomic::AtomicI32;
    use std::collections::HashSet;

    #[test]
    fn test_insert_nodes() {
        let mut tree = Tree::new();
        tree.add_child_node(
            None,
            Node {
                key: 1,
                parent: None,
                collapsed: false,
                deps: vec![],
                value: Specific {
                    state: Progressing,
                    name: "a0".to_string(),
                },
            },
        );
        tree.add_child_node(
            Some(1),
            Node {
                key: 2,
                parent: None,
                collapsed: false,
                deps: vec![],
                value: Specific {
                    state: Progressing,
                    name: "a00".to_string(),
                },
            },
        );
        tree.add_child_node(
            Some(1),
            Node {
                key: 3,
                parent: None,
                collapsed: false,
                deps: vec![],
                value: Specific {
                    state: Progressing,
                    name: "a01".to_string(),
                },
            },
        );
        tree.add_child_node(
            None,
            Node {
                key: 4,
                parent: None,
                collapsed: false,
                deps: vec![],
                value: Specific {
                    state: Progressing,
                    name: "a1".to_string(),
                },
            },
        );
        tree.add_child_node(
            Some(4),
            Node {
                key: 5,
                parent: None,
                collapsed: false,
                deps: vec![],
                value: Specific {
                    state: Progressing,
                    name: "a10".to_string(),
                },
            },
        );
        tree.add_child_node(
            Some(4),
            Node {
                key: 6,
                parent: None,
                collapsed: false,
                deps: vec![],
                value: Specific {
                    state: Progressing,
                    name: "a11".to_string(),
                },
            },
        );
        let f = NodeFactory::new(1);
        assert_eq!(
            tree,
            f.trees(&[
                f.tree("a0", &[f.leaf("a00"), f.leaf("a01"),]).build(),
                f.tree("a1", &[f.leaf("a10"), f.leaf("a11"),]).build(),
            ])
        );
    }

    #[test]
    fn test_merge_trees() {
        let f = NodeFactory::new(1);
        let mut base_tree = f.tree("a", &[f.leaf("a-0"), f.leaf("a-1")]).build();
        let mut piece = f.tree("b", &[f.leaf("b-0"), f.leaf("b-1")]).build();

        base_tree.merge_in(&mut piece);

        let f = NodeFactory::new(1);
        assert_eq!(
            base_tree,
            f.trees(&[
                f.tree("a", &[f.leaf("a-0"), f.leaf("a-1"),]).build(),
                f.tree("b", &[f.leaf("b-0"), f.leaf("b-1"),]).build(),
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
                        "b-0",
                        &[
                            nf.tree(
                                "c-00",
                                &[
                                    nf.leaf("d-000"),
                                    nf.leaf("d-001"),
                                    nf.leaf("d-002"),
                                    nf.leaf("d-003"),
                                ],
                            ),
                            nf.leaf("c-01"),
                            nf.leaf("c-02"),
                        ],
                    ),
                    nf.tree(
                        "b-1",
                        &[
                            nf.leaf("c-10"),
                            nf.leaf("c-11"),
                            nf.tree(
                                "c-12",
                                &[
                                    nf.leaf("d-120"),
                                    nf.leaf("d-121"),
                                    nf.leaf("d-122"),
                                    nf.leaf("d-123"),
                                ],
                            ),
                        ],
                    ),
                    nf.leaf("b-3"),
                ],
            )
            .build();
        debug_assert!(is_valid(&tree), "tree should be valid");

        get_node_by_name(&mut tree, "d-001").map(|n| n.value.state = Errored);

        let level0 = tree
            .keys_on_level(0)
            .into_iter()
            .map(|(k, s)| (tree.get_node(k).map(|n| &n.value.name[..]).unwrap_or(""), s))
            .collect::<Vec<_>>();
        assert_eq!(level0, vec![("a", Errored)]);

        let level1 = tree
            .keys_on_level(1)
            .into_iter()
            .map(|(k, s)| (tree.get_node(k).map(|n| &n.value.name[..]).unwrap_or(""), s))
            .collect::<Vec<_>>();
        assert_eq!(
            level1,
            vec![("b-0", Errored), ("b-1", Progressing), ("b-3", Progressing)]
        );

        let level2 = tree
            .keys_on_level(2)
            .into_iter()
            .map(|(k, s)| (tree.get_node(k).map(|n| &n.value.name[..]).unwrap_or(""), s))
            .collect::<Vec<_>>();
        assert_eq!(
            level2,
            vec![
                ("c-00", Errored),
                ("c-01", Progressing),
                ("c-02", Progressing),
                ("c-10", Progressing),
                ("c-11", Progressing),
                ("c-12", Progressing)
            ]
        );

        let level3 = tree
            .keys_on_level(3)
            .into_iter()
            .map(|(k, s)| (tree.get_node(k).map(|n| &n.value.name[..]).unwrap_or(""), s))
            .collect::<Vec<_>>();
        assert_eq!(
            level3,
            vec![
                ("d-000", Progressing),
                ("d-001", Errored),
                ("d-002", Progressing),
                ("d-003", Progressing),
                ("d-120", Progressing),
                ("d-121", Progressing),
                ("d-122", Progressing),
                ("d-123", Progressing)
            ]
        );

        let level4 = tree
            .keys_on_level(4)
            .into_iter()
            .map(|(k, s)| (tree.get_node(k).map(|n| &n.value.name[..]).unwrap_or(""), s))
            .collect::<Vec<_>>();
        assert_eq!(level4, vec![]);
    }

    /// check if the tree is properly formed
    pub fn is_valid<K: Copy + Eq + Hash, T: Clone + Eq + HasState>(tree: &Tree<K, T>) -> bool {
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
        fn in_pool<K: Copy + Eq + Hash, T: Clone + Eq + HasState>(tree: &Tree<K, T>, r: K) -> Option<()> {
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
        tree.get_roots().into_iter().all(|root| {
            calc_inner(tree, root, &mut seen) == Some(())
        })
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

    fn get_node_by_name<'a>(
        tree: &'a mut Tree<i32, Specific>,
        name: &str,
    ) -> Option<&'a mut Node<i32, Specific>> {
        tree.pool.values_mut().find(|n| n.value.name == name)
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
        fn trees(&self, trees: &[Tree<i32, Specific>]) -> Tree<i32, Specific> {
            let mut full_tree = Tree::new();
            for tree in trees {
                full_tree.merge_in(&mut tree.clone());
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
                let node = Node {
                    key: nf.counter.fetch_add(1, std::sync::atomic::Ordering::SeqCst),
                    parent,
                    deps: Vec::with_capacity(nf.deps.len()),
                    collapsed: false,
                    value: Specific {
                        state: State::Progressing,
                        name: nf.name.to_string(),
                    },
                };
                let new_parent = Some(node.key);
                tree.add_child_node(parent, node);
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
