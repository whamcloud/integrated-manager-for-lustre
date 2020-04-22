use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::hash::Hash;
use std::iter::FromIterator;
use std::iter::Iterator;
use std::sync::Arc;

pub trait Deps<K> {
    fn id(&self) -> K;
    fn deps(&self) -> Vec<K>;
}

impl<K, T: Deps<K>> Deps<K> for Arc<T> {
    fn id(&self) -> K {
        (**self).id()
    }
    fn deps(&self) -> Vec<K> {
        (**self).deps()
    }
}

#[derive(Clone, Debug)]
pub struct RichDeps<K: Hash + Eq, T> {
    pub id: K,
    pub dset: HashSet<K>,
    pub inner: T,
}

impl<K, T> RichDeps<K, T>
where
    K: Hash + Eq + Copy,
    T: Deps<K> + Clone,
{
    pub fn new(t: T) -> Self {
        Self {
            id: t.id(),
            dset: t.deps().into_iter().collect(),
            inner: t,
        }
    }
    pub fn from_ref(t: &T) -> Self {
        Self {
            id: t.id(),
            dset: t.deps().into_iter().collect(),
            inner: t.clone(),
        }
    }
    pub fn contains(&self, k: &K) -> bool {
        self.dset.contains(k)
    }
}

impl<K, T> Deps<K> for RichDeps<K, T>
where
    K: Hash + Eq + Ord + Copy,
    T: Deps<K>,
{
    fn id(&self) -> K {
        self.id
    }
    fn deps(&self) -> Vec<K> {
        let mut v = Vec::from_iter(self.dset.iter().copied());
        v.sort();
        v
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
                    if let Some(i) = roots.iter().position(|r| *r == y) {
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
            if let Some((_, ref mut ys)) = dag.iter_mut().find(|(y, _)| *y == x) {
                ys.push(y);
            } else {
                dag.push((x, vec![y]));
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
        .map(|a| Arc::clone(a))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::hash::Hash;
    use rand_xoshiro::Xoroshiro64Star;
    use rand_core::{SeedableRng, RngCore};
    use wasm_bindgen::__rt::core::cmp::Ordering;

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
        fn deps(&self) -> Vec<u32> {
            self.deps.clone()
        }
    }

    #[derive(Debug, Clone)]
    struct Context<K: Hash + Eq + Debug> {
        visited: HashSet<K>,
        indent: usize,
        is_new: bool,
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
        let x_arcs: Vec<Arc<X>> = x_list.into_iter().map(|x| Arc::new(x)).collect();

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
        let x_arcs: Vec<Arc<X>> = x_list.into_iter().map(|x| Arc::new(x)).collect();

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
        let x_arcs: Vec<Arc<X>> = x_list.into_iter().map(|x| Arc::new(x)).collect();
        let dag = build_direct_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, "1: One");
        let dag = build_inverse_dag(&x_arcs);
        let result = build_dag_str(&dag, &x_to_string).join("\n");
        assert_eq!(result, "1: One");
    }

    #[test]
    fn test_rich_wrapper() {
        let x_list: Vec<X> = vec![
            X::new(39, &[], "Install packages on server oss2.local"),
            X::new(40, &[39], "Configure NTP on oss2.local"),
            X::new(46, &[43, 45, 46], "Configure Pacemaker on oss2.local"),
            X::new(48, &[39, 40, 41, 42, 45, 46, 47], "Setup managed host oss2.local"),
        ];
        // dependencies should always come in the stable order
        for _ in 0..10 {
            let x_arcs: Vec<Arc<RichDeps<u32, X>>> =
                x_list.clone().into_iter().map(|x| Arc::new(RichDeps::new(x))).collect();
            let dag = build_direct_dag(&x_arcs);
            let result = build_dag_str(&dag, &richx_to_string).join("\n");
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
        format!("{}{}: {}{}", indent, node.id, node.description, ellipsis,)
    }

    fn richx_to_string(node: Arc<RichDeps<u32, X>>, ctx: &mut Context<u32>) -> String {
        x_to_string(Arc::new(node.inner.clone()), ctx)
    }

    #[derive(Debug, Clone)]
    struct A(X);

    impl Deps<u32> for A {
        fn id(&self) -> u32 {
            self.0.id
        }
        fn deps(&self) -> Vec<u32> {
            self.0.deps.clone()
        }
    }

    #[derive(Debug, Clone)]
    struct B(X);

    impl Deps<u32> for B {
        fn id(&self) -> u32 {
            self.0.id
        }
        fn deps(&self) -> Vec<u32> {
            self.0.deps.clone()
        }
    }

    #[derive(Debug, Clone)]
    struct C(X);

    impl Deps<u32> for C {
        fn id(&self) -> u32 {
            self.0.id
        }
        fn deps(&self) -> Vec<u32> {
            self.0.deps.clone()
        }
    }

    #[derive(Debug, Default, Clone)]
    struct Db {
        all_a: Vec<A>,
        all_b: Vec<B>,
        all_c: Vec<C>,
    }

    impl Db {
        fn select_a(&self, is: &[u32]) -> Vec<A> {
            self.all_a.iter().filter(|a| is.contains(&a.id())).map(|a| a.clone()).collect::<Vec<A>>()
        }
        fn select_b(&self, is: &[u32]) -> Vec<B> {
            self.all_b.iter().filter(|b| is.contains(&b.id())).map(|b| b.clone()).collect::<Vec<B>>()
        }
        fn select_c(&self, is: &[u32]) -> Vec<C> {
            self.all_c.iter().filter(|c| is.contains(&c.id())).map(|c| c.clone()).collect::<Vec<C>>()
        }
    }

    #[derive(Debug, Default, Clone)]
    struct Model {
        aa: Vec<Arc<A>>,
        bb: Vec<Arc<B>>,
        cc: Vec<Arc<C>>,

        bb_view: Vec<Arc<A>>,
        aa_view: Vec<Arc<A>>,
        cc_view: Vec<Arc<A>>,

        select: Select,
    }

    #[derive(Debug, Clone)]
    enum Select {
        None,
        SelectA(u32),
        SelectB(u32, u32),
        SelectC(u32, u32, u32),
    }
    impl Default for Select {
        fn default() -> Self {
            Self::None
        }
    }

    impl Model {
        fn assign_a(&mut self, aa: &[A]) {
            let mut aas = aa.to_vec();
            aas.sort_by_key(|a| a.id());
            self.aa = aas.into_iter().map(|a| Arc::new(a.clone())).collect();
            self.aa_view = self.aa.clone();
        }
        fn assign_b(&mut self, bb: &[B]) {
            let mut bbs = bb.to_vec();
            bbs.sort_by_key(|b| b.id());
            self.bb = bbs.into_iter().map(|b| Arc::new(b.clone())).collect();
        }

        fn assign_c(&mut self, cc: &[C]) {
            let mut ccs = cc.to_vec();
            ccs.sort_by_key(|c| c.id());
            self.cc = ccs.into_iter().map(|c| Arc::new(c.clone())).collect();
        }

        fn consistency_level(&self, select: &Select) -> (bool, bool, bool) {
            let mut ls = [false; 3];
            match *select {
                Select::None => {},
                Select::SelectA(i) => {
                    let ao = self.aa.iter().find(|a| a.id() == i);
                    match ao {
                        Some(_) => {
                            ls[0] = true;
                        },
                        _ => {
                            ls[0] = false;
                        },
                    }
                },
                Select::SelectB(i, j) => {
                    let ao = self.aa.iter().find(|a| a.id() == i);
                    let bo = self.bb.iter().find(|b| b.id() == j);
                    match (ao, bo) {
                        (Some(a), Some(b)) => {
                            ls[0] = true;
                            ls[1] = a.deps().contains(&j);
                        }
                        (Some(_), _) => {
                            ls[0] = true;
                            ls[1] = false;
                        }
                        (_, _) => {
                            ls[0] = false;
                            ls[0] = false;
                        }
                    }
                },
                Select::SelectC(i, j, k) => {
                    let ao = self.aa.iter().find(|a| a.id() == i);
                    let bo = self.bb.iter().find(|b| b.id() == j);
                    let co = self.cc.iter().find(|c| c.id() == k);
                    println!("ijk = {:?} / {:?} / {:?}", i, j, k);
                    println!("{:?} / {:?} / {:?}", ao, bo, co);
                    match (ao, bo, co) {
                        (Some(a), Some(b), Some(c)) => {
                            ls[0] = true;
                            ls[1] = a.deps().contains(&j);
                            ls[2] = b.deps().contains(&k);
                        }
                        (Some(a), Some(_), _) => {
                            ls[0] = true;
                            ls[1] = a.deps().contains(&j);
                            ls[2] = false;
                        }
                        (Some(_), _, _) => {
                            ls[0] = true;
                            ls[1] = false;
                            ls[2] = false;
                        }
                        (_, _, _) => {
                            ls[0] = false;
                            ls[1] = false;
                            ls[2] = false;
                        }
                    }
                },
            }
            (ls[0], ls[1], ls[2])
        }
    }

    fn recalc_view(model: &mut Model) {
        match &model.select {
            Select::None => {},
            Select::SelectA(_) => {},
            Select::SelectB(_, _) => {},
            Select::SelectC(_, _, _) => {},
        }
    }

    #[test]
    fn test_async_handlers() {
        // TBD all the packets come in random order, the model should be always consistent
        // 1 -> [10, 11] -> [20, 21, 22, 23]
        let mut rng = Xoroshiro64Star::seed_from_u64(485369);
        let db = build_db();
        let mut model = Model::default();
        let (a, b, c) = prepare_abc(&db, 1);
        model.assign_a(&db.select_a(&vec![1, 2]));
        model.assign_b(&db.select_b(&vec![10, 12, 13, 14]));
        model.assign_c(&db.select_c(&vec![20, 23, 14]));
        println!("a = {:?}", model.aa);
        println!("b = {:?}", model.bb);
        println!("c = {:?}", model.cc);
        println!("{:?}", model.consistency_level(&Select::SelectC(2, 12, 23)));
        println!("{:?}", model.consistency_level(&Select::SelectC(2, 13, 23)));
        println!("{:?}", model.consistency_level(&Select::SelectC(2, 12, 22)));
        println!("{:?}", model.consistency_level(&Select::SelectC(2, 14, 22)));

    }

    fn build_db() -> Db {
        let all_a = vec![
            A(X::new(1, &[10, 11], "One")),
            A(X::new(2, &[12, 13], "Two")),
            A(X::new(3, &[14, 15], "Three")),
            A(X::new(4, &[16, 17], "Four")),
        ];
        let all_b = vec![
            B(X::new(10, &[20, 21], "Ten")),
            B(X::new(11, &[21, 26], "Eleven")),
            B(X::new(12, &[22, 23], "Twelve")),
            B(X::new(13, &[23, 28], "Thirteen")),
            B(X::new(14, &[24, 15], "Ten")),
            B(X::new(15, &[25, 20], "Eleven")),
            B(X::new(16, &[26, 27], "Twelve")),
            B(X::new(17, &[27, 22], "Thirteen")),
        ];
        let all_c = vec![
            C(X::new(20, &[], "Twenty and zero")),
            C(X::new(21, &[], "Twenty and one")),
            C(X::new(22, &[], "Twenty and two")),
            C(X::new(23, &[], "Twenty and three")),
            C(X::new(24, &[], "Twenty and four")),
            C(X::new(25, &[], "Twenty and five")),
            C(X::new(26, &[], "Twenty and siz")),
            C(X::new(27, &[], "Twenty and seven")),
            C(X::new(28, &[], "Twenty and eight")),
            C(X::new(29, &[], "Twenty and nine")),
        ];
        Db { all_a, all_b, all_c }
    }

    fn prepare_abc(db: &Db, id: u32) -> (Vec<A>, Vec<B>, Vec<C>) {
        let ai = db.select_a(&vec![id]);
        let aix = ai.iter().map(|a| a.deps()).flatten().collect::<Vec<u32>>();
        let bi = db.select_b(&aix);
        let bix = bi.iter().map(|b| b.deps()).flatten().collect::<Vec<u32>>();
        let ci = db.select_c(&bix);
        let ai = db.all_a.clone(); // use all roots
        (ai, bi, ci)
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
