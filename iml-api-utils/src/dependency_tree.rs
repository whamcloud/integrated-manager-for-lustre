use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::hash::Hash;
use std::iter::Iterator;
use std::ops::Deref;
use std::sync::Arc;

/// There are two hierarchies that this trait is used for:
/// * commands -> jobs -> steps form the tree structure, using `Command::jobs` and `Job<_>::steps` fields
/// * jobs interdependencies via `Job<_>::wait_for`
pub trait Deps<K> {
    fn id(&self) -> K;
    fn deps(&self) -> &[K];
}

impl<K, T: Deps<K>> Deps<K> for Arc<T> {
    fn id(&self) -> K {
        (**self).id()
    }
    fn deps(&self) -> &[K] {
        (**self).deps()
    }
}

#[derive(Clone, Eq, PartialEq, Debug)]
pub struct Rich<K: Hash + Eq, T> {
    pub id: K,
    pub deps: Vec<K>,
    pub inner: T,
}

impl<K, T> Rich<K, T>
where
    K: Hash + Ord + Copy,
    T: Clone,
{
    pub fn new<F>(inner: T, extract: F) -> Self
    where
        F: Fn(&T) -> (K, Vec<K>),
    {
        let (id, deps) = extract(&inner);
        Self { id, deps, inner }
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

#[derive(Clone, Eq, PartialEq, Debug)]
pub struct DependencyDAG<K: Hash + Eq + Debug, T> {
    pub roots: Vec<Arc<T>>,
    pub links: HashMap<K, Vec<Arc<T>>>,
}

impl<K: Hash + Eq + Debug, T> Default for DependencyDAG<K, T> {
    fn default() -> Self {
        Self {
            roots: Vec::new(),
            links: HashMap::new(),
        }
    }
}

impl<K: Hash + Eq + Debug, T> DependencyDAG<K, T> {
    pub fn clear(&mut self) {
        self.roots.clear();
        self.links.clear();
    }
    pub fn is_empty(&self) -> bool {
        self.roots.is_empty()
    }
}

pub fn build_direct_dag<K, T>(ts: &[T]) -> DependencyDAG<K, T>
where
    K: Hash + Eq + Copy + Debug,
    T: Deps<K> + Clone + Debug,
{
    let mut roots: Vec<K> = Vec::new();
    let mut dag: Vec<(K, Vec<K>)> = Vec::with_capacity(ts.len());

    for t in ts {
        // isolated vertices will remain to be roots after we traverse all the arcs
        roots.push(t.id());
    }
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
    enrich_dag(ts, &roots, &dag)
}

pub fn build_inverse_dag<K, T>(ts: &[T]) -> DependencyDAG<K, T>
where
    K: Hash + Ord + Copy + Debug,
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
    let mut roots = roots.into_iter().collect::<Vec<K>>();
    roots.sort();
    enrich_dag(ts, &roots, &dag)
}

pub fn enrich_dag<K, T>(objs: &[T], int_roots: &[K], int_deps: &[(K, Vec<K>)]) -> DependencyDAG<K, T>
where
    K: Hash + Eq + Copy + Debug,
    T: Deps<K> + Clone + Debug,
{
    let roots: Vec<Arc<T>> = convert_ids_to_arcs(objs, int_roots);
    let links: HashMap<K, Vec<Arc<T>>> = int_deps
        .iter()
        .map(|(id, ids)| (*id, convert_ids_to_arcs(objs, ids)))
        .collect();
    DependencyDAG { roots, links }
}

pub fn convert_ids_to_arcs<K, T>(objs: &[T], ids: &[K]) -> Vec<Arc<T>>
where
    K: Hash + Eq + Debug,
    T: Deps<K> + Clone + Debug,
{
    ids.iter()
        .filter_map(|id| objs.iter().find(|o| o.id() == *id))
        .map(|o| Arc::new(o.clone()))
        .collect()
}

/// The function to traverse the graph and build the result after the full traversal.
/// - `apply_node` is called each time a node is visited;
/// - `combine_nodes` is called each time when the current node and all nodes, reachable from the current;
/// - `context` is a custom context, no restrictions placed on its type.
pub fn traverse_graph<K, T, U, C, F1, F2>(
    graph: &DependencyDAG<K, T>,
    apply_node: &F1,
    combine_nodes: &F2,
    context: &mut C,
) -> Vec<U>
where
    K: Hash + Eq + Debug,
    T: Deps<K>,
    F1: Fn(Arc<T>, bool, &mut C) -> U,
    F2: Fn(U, Vec<U>, &mut C) -> U,
{
    struct Env<'a, K: Hash + Eq + Debug, T: Deps<K>, F1, F2, C> {
        graph: &'a DependencyDAG<K, T>,
        apply_node: &'a F1,
        combine_nodes: &'a F2,
        context: &'a mut C,
        visited: &'a mut HashSet<K>,
    }

    fn traverse_node<K, T, U, F1, F2, C>(env: &mut Env<K, T, F1, F2, C>, n: Arc<T>) -> U
    where
        K: Hash + Eq + Debug,
        T: Deps<K>,
        F1: Fn(Arc<T>, bool, &mut C) -> U,
        F2: Fn(U, Vec<U>, &mut C) -> U,
    {
        let is_new = env.visited.insert(n.id());
        let parent: U = (env.apply_node)(Arc::clone(&n), is_new, env.context);
        let mut acc: Vec<U> = Vec::new();
        if let Some(deps) = env.graph.links.get(&n.id()) {
            if is_new {
                for d in deps {
                    let rec_node = traverse_node(env, Arc::clone(d));
                    acc.push(rec_node);
                }
            }
        }
        (env.combine_nodes)(parent, acc, env.context)
    }
    let mut visited = HashSet::<K>::new();
    let mut env = Env {
        graph,
        apply_node,
        combine_nodes,
        context,
        visited: &mut visited,
    };
    let mut acc: Vec<U> = Vec::with_capacity(graph.roots.len());
    for r in &graph.roots {
        acc.push(traverse_node(&mut env, Arc::clone(r)));
    }
    acc
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand_core::{RngCore, SeedableRng};
    use rand_xoshiro::Xoroshiro64Star;

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
    struct Context {
        level: usize,
    }

    #[test]
    fn build_dependency_tree_test() {
        let xs: Vec<X> = vec![
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
        let dag = build_direct_dag(&xs);
        let mut ctx = Context { level: 0 };
        let result = traverse_graph(&dag, &x_to_string, &combine_strings, &mut ctx).join("");
        assert_eq!(result, TREE_DIRECT);

        let dag = build_inverse_dag(&xs);
        let mut ctx = Context { level: 0 };
        let result = traverse_graph(&dag, &x_to_string, &combine_strings, &mut ctx).join("");
        assert_eq!(result, TREE_INVERSE);
    }

    #[test]
    fn cyclic_dependency() {
        // it shouldn't be stack overflow anyway even if there is an invariant violation
        let xs: Vec<X> = vec![X::new(1, &[2], "One"), X::new(2, &[3], "Two"), X::new(3, &[2], "Three")];

        let dag = build_direct_dag(&xs);
        let mut ctx = Context { level: 0 };
        let result = traverse_graph(&dag, &x_to_string, &combine_strings, &mut ctx).join("");
        assert_eq!(result, "1: One\n  2: Two\n    3: Three\n");

        let dag = build_inverse_dag(&xs);
        let mut ctx = Context { level: 0 };
        let result = traverse_graph(&dag, &x_to_string, &combine_strings, &mut ctx).join("");
        assert_eq!(result, "");
    }

    #[test]
    fn isolated_nodes() {
        let xs: Vec<X> = vec![X::new(1, &[], "One"), X::new(2, &[], "Two"), X::new(3, &[], "Three")];

        let dag = build_direct_dag(&xs);
        let mut ctx = Context { level: 0 };
        let result = traverse_graph(&dag, &x_to_string, &combine_strings, &mut ctx).join("");
        assert_eq!(result, "1: One\n2: Two\n3: Three\n");

        let dag = build_inverse_dag(&xs);
        let mut ctx = Context { level: 0 };
        let result = traverse_graph(&dag, &x_to_string, &combine_strings, &mut ctx).join("");
        assert_eq!(result, "1: One\n2: Two\n3: Three\n");
    }

    #[test]
    fn test_rich_wrapper() {
        fn extract_from_y(y: &Y) -> (u32, Vec<u32>) {
            let mut deps = y.deps.iter().map(|s| s.parse::<u32>().unwrap()).collect::<Vec<u32>>();
            deps.sort();
            (y.id, deps)
        }
        // the DAG built over RichDeps<_, _> must be always the same, no matter how dependencies are sorted
        let mut rng = Xoroshiro64Star::seed_from_u64(485369);
        let mut ys: Vec<Y> = vec![
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
            for y in ys.iter_mut() {
                shuffle(&mut y.deps, &mut rng);
            }
            let rich_ys: Vec<Rich<u32, Y>> = ys.clone().into_iter().map(|t| Rich::new(t, extract_from_y)).collect();
            let dag = build_direct_dag(&rich_ys);
            let mut ctx = Context { level: 0 };
            let result = traverse_graph(&dag, &rich_y_to_string, &combine_strings, &mut ctx).join("");
            assert_eq!(result, SMALL_TREE);
        }
    }

    fn rich_y_to_string(node: Arc<Rich<u32, Y>>, is_new: bool, ctx: &mut Context) -> String {
        ctx.level += 1;
        let ellipsis = if is_new { "" } else { "..." };
        format!("{}: {}{}", node.id(), node.description, ellipsis)
    }

    fn x_to_string(node: Arc<X>, is_new: bool, ctx: &mut Context) -> String {
        ctx.level += 1;
        if is_new {
            format!("{}: {}\n", node.id, node.description)
        } else {
            String::new()
        }
    }

    fn combine_strings(node: String, nodes: Vec<String>, ctx: &mut Context) -> String {
        if ctx.level > 0 {
            ctx.level -= 1;
        }
        let space = if ctx.level > 0 { "  " } else { "" };
        let mut result = String::with_capacity(100);
        for line in node.lines() {
            result.push_str(space);
            result.push_str(line);
            result.push('\n');
        }
        for n in nodes.iter() {
            for line in n.lines() {
                result.push_str(space);
                result.push_str(line);
                result.push('\n');
            }
        }
        result
    }

    pub fn shuffle<R: RngCore, T>(slice: &mut [T], rng: &mut R) {
        for i in (1..slice.len()).rev() {
            let j = (rng.next_u64() as usize) % (i + 1);
            slice.swap(i, j);
        }
    }

    const SMALL_TREE: &'static str = r#"48: Setup managed host oss2.local
  39: Install packages on server oss2.local
  40: Configure NTP on oss2.local
    39: Install packages on server oss2.local...
  46: Configure Pacemaker on oss2.local
    46: Configure Pacemaker on oss2.local...
"#;

    const TREE_DIRECT: &'static str = r#"48: Setup managed host oss2.local.
  39: Install packages on server oss2.local.
  40: Configure NTP on oss2.local.
  41: Enable LNet on oss2.local.
  42: Configure Corosync on oss2.local.
  45: Start the LNet networking layer.
    44: Load the LNet kernel modules.
  46: Configure Pacemaker on oss2.local.
    43: Start Corosync on oss2.local
  47: Start Pacemaker on oss2.local.
"#;

    const TREE_INVERSE: &'static str = r#"39: Install packages on server oss2.local.
  40: Configure NTP on oss2.local.
    48: Setup managed host oss2.local.
  41: Enable LNet on oss2.local.
    44: Load the LNet kernel modules.
      45: Start the LNet networking layer.
  42: Configure Corosync on oss2.local.
    43: Start Corosync on oss2.local
      46: Configure Pacemaker on oss2.local.
        47: Start Pacemaker on oss2.local.
"#;
}
