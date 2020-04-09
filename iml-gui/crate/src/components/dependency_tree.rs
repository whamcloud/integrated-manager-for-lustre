use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::iter::Iterator;
use std::sync::Arc;

pub trait Deps {
    fn id(&self) -> u32;
    fn deps(&self) -> Vec<u32>;
}

impl<T: Deps> Deps for Arc<T> {
    fn id(&self) -> u32 {
        (**self).id()
    }
    fn deps(&self) -> Vec<u32> {
        (**self).deps()
    }
}

#[derive(Debug, Clone)]
pub struct DependencyDAG<T> {
    pub roots: Vec<Arc<T>>,
    pub deps: HashMap<u32, Vec<Arc<T>>>,
}

pub fn build_direct_dag<T>(ts: &[T]) -> DependencyDAG<T>
where
    T: Deps + Clone + Debug,
{
    let mut roots: Vec<u32> = Vec::new();
    let mut dag: Vec<(u32, Vec<u32>)> = Vec::with_capacity(ts.len());
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
    enrich_dag(ts, &roots, &dag)
}

pub fn build_inverse_dag<T>(ts: &[T]) -> DependencyDAG<T>
where
    T: Deps + Clone + Debug,
{
    let mut roots: HashSet<u32> = ts.iter().map(|t| t.id()).collect();
    let mut dag: Vec<(u32, Vec<u32>)> = Vec::with_capacity(ts.len());
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
    let roots: Vec<u32> = roots.into_iter().collect();
    enrich_dag(ts, &roots, &dag)
}

pub fn enrich_dag<T>(objs: &[T], int_roots: &[u32], int_deps: &[(u32, Vec<u32>)]) -> DependencyDAG<T>
where
    T: Deps + Clone + Debug,
{
    let roots: Vec<Arc<T>> = convert_ids_to_arcs(&objs, &int_roots);
    let deps: HashMap<u32, Vec<Arc<T>>> = int_deps
        .iter()
        .map(|(id, ids)| (*id, convert_ids_to_arcs(&objs, ids)))
        .collect();
    DependencyDAG { roots, deps }
}

pub fn convert_ids_to_arcs<T>(objs: &[T], ids: &[u32]) -> Vec<Arc<T>>
where
    T: Deps + Clone + Debug,
{
    ids.iter()
        .filter_map(|id| objs.iter().find(|o| o.id() == *id))
        .map(|o| Arc::new(o.clone()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

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

    impl Deps for X {
        fn id(&self) -> u32 {
            self.id
        }
        fn deps(&self) -> Vec<u32> {
            self.deps.clone()
        }
    }

    #[derive(Debug, Clone)]
    struct Context {
        visited: HashSet<u32>,
        indent: usize,
        is_new: bool,
    }

    fn build_dag_str<T, U, F>(dag: &DependencyDAG<T>, node_to_str: &F) -> Vec<U>
    where
        T: Deps,
        F: Fn(Arc<T>, &mut Context) -> U,
    {
        fn build_node_str<T, U, F>(
            dag: &DependencyDAG<T>,
            node_to_str: &F,
            n: Arc<T>,
            ctx: &mut Context,
            res: &mut Vec<U>,
        ) where
            T: Deps,
            F: Fn(Arc<T>, &mut Context) -> U,
        {
            ctx.is_new = ctx.visited.insert(n.id());
            res.push(node_to_str(Arc::clone(&n), ctx));
            if let Some(deps) = dag.deps.get(&n.id()) {
                ctx.indent += 1;
                if ctx.is_new {
                    for d in deps {
                        build_node_str(dag, node_to_str, Arc::clone(d), ctx, res);
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
        let mut res: Vec<U> = Vec::new();
        for r in &dag.roots {
            build_node_str(dag, node_to_str, Arc::clone(r), &mut ctx, &mut res);
        }
        res
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

        let dag = build_direct_dag(&x_list);
        let result = build_dag_str(&dag, &node_to_string).join("\n");
        assert_eq!(result, TREE_DIRECT);

        let dag = build_inverse_dag(&x_list);
        let result = build_dag_str(&dag, &node_to_string).join("\n");
        assert_eq!(result, TREE_INVERSE);
    }

    #[test]
    fn cyclic_dependency() {
        // it shouldn't be stack overflow anyway even if there is an invariant violation
        let x_list: Vec<X> = vec![X::new(1, &[2], "One"), X::new(2, &[3], "Two"), X::new(3, &[2], "Three")];

        let dag = build_direct_dag(&x_list);
        let result = build_dag_str(&dag, &node_to_string).join("\n");
        assert_eq!(result, "1: One\n  2: Two\n    3: Three\n      2: Two...\n3: Three...");

        let dag = build_inverse_dag(&x_list);
        let result = build_dag_str(&dag, &node_to_string).join("\n");
        assert_eq!(result, "");
    }

    fn node_to_string(node: Arc<X>, ctx: &mut Context) -> String {
        let ellipsis = if ctx.is_new { "" } else { "..." };
        let indent = "  ".repeat(ctx.indent);
        format!("{}{}: {}{}", indent, node.id, node.description, ellipsis,)
    }

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
