use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::hash::Hash;
use std::iter::FromIterator;
use std::iter::Iterator;
use std::ops::Deref;
use std::sync::Arc;

/// There are two hierarchies that this trait is used for:
/// * commands -> jobs -> steps form the tree structure, using `Command::jobs` and `Job<_>::steps` fields
/// * jobs interdependencies via `Job<_>::wait_for`
pub trait Deps<K> {
    fn id(&self) -> K;
    fn deps(&self) -> &[K];
    fn has(&self, k: &K) -> bool;
}

impl<K, T: Deps<K>> Deps<K> for Arc<T> {
    fn id(&self) -> K {
        (**self).id()
    }
    fn deps(&self) -> &[K] {
        (**self).deps()
    }
    fn has(&self, k: &K) -> bool {
        (**self).has(k)
    }
}

/// `deps` is to iterate through in the fixed order
/// `dset` is to check the membership
///
/// Please note that the contents of `deps` and `dset` should be always equal, i.e.
/// ```norun
/// let set1 = HashSet::from_iter(self.deps.iter().cloned();
/// let set2 = self.deps;
/// asssert_eq!()
/// ```
#[derive(Clone, Debug)]
pub struct Rich<K: Hash + Eq, T> {
    pub id: K,
    pub deps: Vec<K>,
    pub dset: HashSet<K>,
    pub inner: T,
}

impl<K, T> Rich<K, T>
where
    K: Hash + Ord + Copy,
    T: Clone,
{
    pub fn new(t: T, extract: impl FnOnce(&T) -> (K, Vec<K>)) -> Self {
        let (id, mut deps) = extract(&t);
        deps.sort();
        Self {
            id,
            dset: HashSet::from_iter(deps.iter().cloned()),
            deps,
            inner: t,
        }
    }
}

impl<K, T> Deps<K> for Rich<K, T>
where
    K: Hash + Ord + Copy,
{
    fn id(&self) -> K {
        self.id
    }
    fn deps(&self) -> &[K] {
        &self.deps
    }
    fn has(&self, k: &K) -> bool {
        self.dset.contains(k)
    }
}

impl<K, T> Deref for Rich<K, T>
where
    K: Hash + Ord + Copy,
{
    type Target = T;

    fn deref(&self) -> &Self::Target {
        &self.inner
    }
}

#[derive(Clone, Debug)]
pub struct DependencyDAG<K: Hash + Eq + Debug, T> {
    pub roots: Vec<Arc<T>>,
    pub deps: HashMap<K, Vec<Arc<T>>>,
}

impl<K: Hash + Eq + Debug, T> Default for DependencyDAG<K, T> {
    fn default() -> Self {
        Self {
            roots: Vec::new(),
            deps: HashMap::new(),
        }
    }
}

impl<K: Hash + Eq + Debug, T> DependencyDAG<K, T> {
    pub fn clear(&mut self) {
        self.roots.clear();
        self.deps.clear();
    }
}

pub fn build_direct_dag<K, T>(ts: &[Arc<T>]) -> DependencyDAG<K, T>
where
    K: Hash + Eq + Copy + Debug,
    T: Deps<K> + Clone + Debug,
{
    let mut roots: Vec<K> = Vec::new();
    let mut dag: Vec<(K, Vec<K>)> = Vec::with_capacity(ts.len());
    if ts.len() == 1 {
        // special case, when there is no any arc `x -> y`,
        // then the only vertex becomes the root
        roots.push(ts[0].id());
    } else {
        for t in ts {
            let x = t.id();
            let ys = t.deps();
            if !ys.is_empty() {
                // push the arcs `x -> y` for all `y \in xs` into the graph
                dag.push((x, ys.to_vec()));
                if !roots.contains(&x) {
                    roots.push(x);
                }
                // remove any of the destinations from the roots
                for y in ys {
                    if let Some(i) = roots.iter().position(|r| *r == *y) {
                        roots.remove(i);
                    }
                }
            }
        }
    }
    enrich_dag(ts, &roots, &dag)
}

pub fn build_inverse_dag<K, T>(ts: &[Arc<T>]) -> DependencyDAG<K, T>
where
    K: Hash + Eq + Copy + Debug,
    T: Deps<K> + Clone + Debug,
{
    let mut roots: HashSet<K> = ts.iter().map(|t| t.id()).collect();
    let mut dag: Vec<(K, Vec<K>)> = Vec::with_capacity(ts.len());
    for t in ts {
        let y = t.id();
        let xs = t.deps();
        for x in xs {
            // push the arc `x -> y` into the graph
            if let Some((_, ref mut ys)) = dag.iter_mut().find(|(y, _)| *y == *x) {
                ys.push(y);
            } else {
                dag.push((*x, vec![y]));
            }
            // any destination cannot be a root, so we need to remove any of these roots
            roots.remove(&y);
        }
    }
    let roots = roots.into_iter().collect::<Vec<K>>();
    enrich_dag(ts, &roots, &dag)
}

pub fn enrich_dag<K, T>(objs: &[Arc<T>], int_roots: &[K], int_deps: &[(K, Vec<K>)]) -> DependencyDAG<K, T>
where
    K: Hash + Eq + Copy + Debug,
    T: Deps<K> + Clone + Debug,
{
    let roots: Vec<Arc<T>> = convert_ids_to_arcs(objs, int_roots);
    let deps: HashMap<K, Vec<Arc<T>>> = int_deps
        .iter()
        .map(|(id, ids)| (*id, convert_ids_to_arcs(objs, ids)))
        .collect();
    DependencyDAG { roots, deps }
}

pub fn convert_ids_to_arcs<K, T>(objs: &[Arc<T>], ids: &[K]) -> Vec<Arc<T>>
where
    K: Hash + Eq + Debug,
    T: Deps<K> + Clone + Debug,
{
    ids.iter()
        .filter_map(|id| objs.iter().find(|o| o.id() == *id))
        .map(Arc::clone)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand_core::{RngCore, SeedableRng};
    use rand_xoshiro::Xoroshiro64Star;
    use std::hash::Hash;

    #[derive(Debug, Clone)]
    struct X {
        id: u32,
        deps: Vec<u32>,
        description: String,
    }

    impl X {
        fn new(id: u32, deps: &[u32], desc: &str) -> Self {
            Self {
                id,
                deps: deps.to_vec(),
                description: desc.to_string(),
            }
        }
    }

    impl Deps<u32> for X {
        fn id(&self) -> u32 {
            self.id
        }
        fn deps(&self) -> &[u32] {
            &self.deps
        }
        fn has(&self, k: &u32) -> bool {
            self.deps.contains(k)
        }
    }

    // Note: Y cannot be Deps by itself, because Deps::deps() returns slice
    #[derive(Debug, Clone)]
    struct Y {
        id: u32,
        deps: Vec<String>,
        description: String,
    }

    impl Y {
        fn new(id: u32, str_deps: &[&str], desc: &str) -> Self {
            Self {
                id,
                deps: str_deps.iter().map(|s| s.to_string()).collect(),
                description: desc.to_string(),
            }
        }
    }

    #[derive(Debug, Clone)]
    struct Context<K: Hash + Eq + Debug> {
        visited: HashSet<K>,
        indent: usize,
        is_new: bool,
    }

    fn shuffle<R: RngCore, T>(slice: &mut [T], rng: &mut R) {
        for i in (1..slice.len()).rev() {
            let j = (rng.next_u64() as usize) % (i + 1);
            slice.swap(i, j);
        }
    }

    #[test]
    fn build_dependency_tree_test() {
        let x_list: Vec<X> = vec![
            X::new(39, &[], "Install packages on server oss2.local."),
            X::new(40, &[39], "Configure NTP on oss2.local."),
            X::new(41, &[39], "Enable LNet on oss2.local."),
            X::new(42, &[39], "Configure Corosync on oss2.local."),
            X::new(43, &[42], "Start Corosync on oss2.local"),
            X::new(44, &[41], "Load the LNet kernel modules."),
            X::new(45, &[44], "Start the LNet networking layer."),
            X::new(46, &[39, 43], "Configure Pacemaker on oss2.local."),
            X::new(47, &[43, 46], "Start Pacemaker on oss2.local."),
            X::new(48, &[39, 40, 41, 42, 45, 46, 47], "Setup managed host oss2.local."),
        ];
        let x_arcs: Vec<Arc<X>> = x_list.into_iter().map(Arc::new).collect();

        let dag = build_direct_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, TREE_DIRECT);

        let dag = build_inverse_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, TREE_INVERSE);
    }

    #[test]
    fn cyclic_dependency() {
        // it shouldn't be stack overflow anyway even if there is an invariant violation
        let x_list: Vec<X> = vec![X::new(1, &[2], "One"), X::new(2, &[3], "Two"), X::new(3, &[2], "Three")];
        let x_arcs: Vec<Arc<X>> = x_list.into_iter().map(Arc::new).collect();

        let dag = build_direct_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, "1: One\n  2: Two\n    3: Three\n      2: Two...\n3: Three...");

        let dag = build_inverse_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, "");
    }

    #[test]
    fn single_node() {
        let x_list: Vec<X> = vec![X::new(1, &[], "One")];
        let x_arcs: Vec<Arc<X>> = x_list.into_iter().map(Arc::new).collect();
        let dag = build_direct_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, "1: One");
        let dag = build_inverse_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, "1: One");
    }

    #[test]
    fn test_rich_wrapper() {
        fn extract_from_y(y: &Y) -> (u32, Vec<u32>) {
            let deps = y.deps.iter().map(|s| s.parse::<u32>().unwrap()).collect();
            (y.id, deps)
        }
        // the DAG built over RichDeps<_, _> must be always the same, no matter how dependencies are sorted
        let mut rng = Xoroshiro64Star::seed_from_u64(485369);
        let mut y_list: Vec<Y> = vec![
            Y::new(39, &[], "Install packages on server oss2.local"),
            Y::new(40, &["39"], "Configure NTP on oss2.local"),
            Y::new(46, &["43", "45", "46"], "Configure Pacemaker on oss2.local"),
            Y::new(
                48,
                &["39", "40", "41", "42", "45", "46", "47"],
                "Setup managed host oss2.local",
            ),
        ];
        for _ in 0..10 {
            for y in y_list.iter_mut() {
                shuffle(&mut y.deps, &mut rng);
            }
            let y_arcs: Vec<Arc<Rich<u32, Y>>> = y_list
                .clone()
                .into_iter()
                .map(|t| Arc::new(Rich::new(t, extract_from_y)))
                .collect();
            let dag = build_direct_dag(&y_arcs);
            let result = build_dag_str(&dag, &rich_y_to_string).join("\n");
            assert_eq!(result, SMALL_TREE);
        }
    }

    fn build_dag_str<K, T, U, F>(dag: &DependencyDAG<K, T>, node_to_str: &F) -> Vec<U>
    where
        K: Hash + Eq + Debug,
        T: Deps<K>,
        F: Fn(Arc<T>, &mut Context<K>) -> U,
    {
        fn build_dag_str_inner<K, T, U, F>(
            dag: &DependencyDAG<K, T>,
            node_to_str: &F,
            n: Arc<T>,
            ctx: &mut Context<K>,
            acc: &mut Vec<U>,
        ) where
            K: Hash + Eq + Debug,
            T: Deps<K>,
            F: Fn(Arc<T>, &mut Context<K>) -> U,
        {
            ctx.is_new = ctx.visited.insert(n.id());
            acc.push(node_to_str(Arc::clone(&n), ctx));
            if let Some(deps) = dag.deps.get(&n.id()) {
                ctx.indent += 1;
                if ctx.is_new {
                    for d in deps {
                        build_dag_str_inner(dag, node_to_str, Arc::clone(d), ctx, acc);
                    }
                }
                ctx.indent -= 1;
            }
        }
        let mut ctx = Context {
            visited: HashSet::new(),
            indent: 0,
            is_new: false,
        };
        let mut acc: Vec<U> = Vec::new();
        for r in &dag.roots {
            build_dag_str_inner(dag, node_to_str, Arc::clone(r), &mut ctx, &mut acc);
        }
        acc
    }

    fn x_to_string(node: Arc<X>, ctx: &mut Context<u32>) -> String {
        let ellipsis = if ctx.is_new { "" } else { "..." };
        let indent = "  ".repeat(ctx.indent);
        format!("{}{}: {}{}", indent, node.id, node.description, ellipsis)
    }

    fn rich_y_to_string(node: Arc<Rich<u32, Y>>, ctx: &mut Context<u32>) -> String {
        let ellipsis = if ctx.is_new { "" } else { "..." };
        let indent = "  ".repeat(ctx.indent);
        format!("{}{}: {}{}", indent, node.id(), node.description, ellipsis)
    }

    const SMALL_TREE: &'static str = r#"48: Setup managed host oss2.local
  39: Install packages on server oss2.local
  40: Configure NTP on oss2.local
    39: Install packages on server oss2.local...
  46: Configure Pacemaker on oss2.local
    46: Configure Pacemaker on oss2.local..."#;

    const TREE_DIRECT: &'static str = r#"48: Setup managed host oss2.local.
  39: Install packages on server oss2.local.
  40: Configure NTP on oss2.local.
    39: Install packages on server oss2.local....
  41: Enable LNet on oss2.local.
    39: Install packages on server oss2.local....
  42: Configure Corosync on oss2.local.
    39: Install packages on server oss2.local....
  45: Start the LNet networking layer.
    44: Load the LNet kernel modules.
      41: Enable LNet on oss2.local....
  46: Configure Pacemaker on oss2.local.
    39: Install packages on server oss2.local....
    43: Start Corosync on oss2.local
      42: Configure Corosync on oss2.local....
  47: Start Pacemaker on oss2.local.
    43: Start Corosync on oss2.local...
    46: Configure Pacemaker on oss2.local...."#;

    const TREE_INVERSE: &'static str = r#"39: Install packages on server oss2.local.
  40: Configure NTP on oss2.local.
    48: Setup managed host oss2.local.
  41: Enable LNet on oss2.local.
    44: Load the LNet kernel modules.
      45: Start the LNet networking layer.
        48: Setup managed host oss2.local....
    48: Setup managed host oss2.local....
  42: Configure Corosync on oss2.local.
    43: Start Corosync on oss2.local
      46: Configure Pacemaker on oss2.local.
        47: Start Pacemaker on oss2.local.
          48: Setup managed host oss2.local....
        48: Setup managed host oss2.local....
      47: Start Pacemaker on oss2.local....
    48: Setup managed host oss2.local....
  46: Configure Pacemaker on oss2.local....
  48: Setup managed host oss2.local...."#;
}
