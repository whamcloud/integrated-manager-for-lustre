use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::fmt::Write;
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
pub struct DependencyForest<T> {
    pub roots: Vec<Arc<T>>,
    pub deps: HashMap<u32, Vec<Arc<T>>>,
}

#[derive(Debug, Copy, Clone)]
pub struct DependencyForestRef<'a, T> {
    pub roots: &'a Vec<Arc<T>>,
    pub deps: &'a HashMap<u32, Vec<Arc<T>>>,
}

#[derive(Debug, Clone)]
pub struct Context {
    pub visited: HashSet<u32>,
    pub indent: usize,
    pub is_new: bool,
}

pub fn build_direct_dag<T>(ts: &[T]) -> DependencyForest<T>
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
    build_forest(ts, &roots, &dag)
}

pub fn build_inverse_dag<T>(ts: &[T]) -> DependencyForest<T>
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
    build_forest(ts, &roots, &dag)
}

pub fn build_forest<T>(objs: &[T], int_roots: &[u32], int_deps: &[(u32, Vec<u32>)]) -> DependencyForest<T>
    where
        T: Deps + Clone + Debug,
{
    let roots: Vec<Arc<T>> = convert_ids_to_arcs(&objs, &int_roots);
    let deps: HashMap<u32, Vec<Arc<T>>> = int_deps
        .iter()
        .map(|(id, ids)| (*id, convert_ids_to_arcs(&objs, ids)))
        .collect();
    DependencyForest { roots, deps }
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

pub fn write_tree<T, F>(tree: &DependencyForestRef<T>, node_to_str: &F) -> String
    where
        T: Deps,
        F: Fn(Arc<T>, &mut Context) -> String,
{
    fn write_subtree<T, F>(tree: &DependencyForestRef<T>, node_to_str: &F, ctx: &mut Context) -> String
        where
            T: Deps,
            F: Fn(Arc<T>, &mut Context) -> String,
    {
        let mut res = String::new();
        for r in tree.roots {
            if let Some(deps) = tree.deps.get(&r.id()) {
                for d in deps {
                    res.write_str(&write_node(tree, node_to_str, Arc::clone(d), ctx));
                }
            }
        }
        res
    }
    fn write_node<T, F>(tree: &DependencyForestRef<T>, node_to_str: &F, node: Arc<T>, ctx: &mut Context) -> String
        where
            T: Deps,
            F: Fn(Arc<T>, &mut Context) -> String,
    {
        let mut res = String::new();
        let is_new = ctx.visited.insert(node.id());
        ctx.is_new = is_new;
        res.write_str(&node_to_str(Arc::clone(&node), ctx));
        if is_new {
            ctx.indent += 1;
            let sub_tree = DependencyForestRef {
                deps: &tree.deps,
                roots: &vec![node.clone()],
            };
            res.write_str(&write_subtree(&sub_tree, node_to_str, ctx));
            ctx.indent -= 1;
        }
        res
    }
    let mut ctx = Context {
        visited: HashSet::new(),
        indent: 0,
        is_new: false,
    };
    let mut res = String::new();
    for r in tree.roots {
        let _ = res.write_str(&write_node(tree, node_to_str, Arc::clone(r), &mut ctx));
    }
    res
}

#[cfg(test)]
mod tests {
    use super::*;
    use iml_wire_types::{ApiList, Job};

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

    #[test]
    fn build_tree_test() {
        let x_list: Vec<X> = vec![
            X::new(39, &[], "Install packages on server oss2.local"),
            X::new(40, &[39], "Configure NTP on oss2.local"),
            X::new(41, &[39], "Enable LNet on oss2.local"),
            X::new(42, &[39], "Configure Corosync on oss2.local."),
            X::new(43, &[42], "Start Corosync on oss2.local"),
            X::new(44, &[41], "Load the LNet kernel modules."),
            X::new(45, &[44], "Start the LNet networking layer."),
            X::new(46, &[39, 43], "Configure Pacemaker on oss2.local."),
            X::new(47, &[43, 46], "Start Pacemaker on oss2.local"),
            X::new(48, &[39, 40, 41, 42, 45, 46, 47], "Setup managed host oss2.local"),
        ];

        // build direct dag
        let forest = build_direct_dag(&x_list);
        let forest_ref = DependencyForestRef {
            roots: &forest.roots,
            deps: &forest.deps,
        };
        let node_to_string_f = |node: Arc<X>, ctx: &mut Context| {
            let ellipsis = if ctx.is_new { "" } else { "..." };
            let indent = "  ".repeat(ctx.indent);
            format!(
                "{}{}: {}{}\n",
                indent,
                node.id,
                node.description,
                ellipsis,
            )
        };
        let result = write_tree(&forest_ref, &node_to_string_f);
        assert_eq!(result, TREE_DIRECT);

        let forest = build_inverse_dag(&x_list);
        let forest_ref = DependencyForestRef {
            roots: &forest.roots,
            deps: &forest.deps,
        };
        let result = write_tree(&forest_ref, &node_to_string_f);
        assert_eq!(result, TREE_INVERSE);
    }

    const TREE_DIRECT: &'static str = r#"48: Setup managed host oss2.local
  39: Install packages on server oss2.local
  40: Configure NTP on oss2.local
    39: Install packages on server oss2.local...
  41: Enable LNet on oss2.local
    39: Install packages on server oss2.local...
  42: Configure Corosync on oss2.local.
    39: Install packages on server oss2.local...
  45: Start the LNet networking layer.
    44: Load the LNet kernel modules.
      41: Enable LNet on oss2.local...
  46: Configure Pacemaker on oss2.local.
    39: Install packages on server oss2.local...
    43: Start Corosync on oss2.local
      42: Configure Corosync on oss2.local....
  47: Start Pacemaker on oss2.local
    43: Start Corosync on oss2.local...
    46: Configure Pacemaker on oss2.local....
"#;

    const TREE_INVERSE: &'static str = r#"39: Install packages on server oss2.local
  40: Configure NTP on oss2.local
    48: Setup managed host oss2.local
  41: Enable LNet on oss2.local
    44: Load the LNet kernel modules.
      45: Start the LNet networking layer.
        48: Setup managed host oss2.local...
    48: Setup managed host oss2.local...
  42: Configure Corosync on oss2.local.
    43: Start Corosync on oss2.local
      46: Configure Pacemaker on oss2.local.
        47: Start Pacemaker on oss2.local
          48: Setup managed host oss2.local...
        48: Setup managed host oss2.local...
      47: Start Pacemaker on oss2.local...
    48: Setup managed host oss2.local...
  46: Configure Pacemaker on oss2.local....
  48: Setup managed host oss2.local...
"#;

}
