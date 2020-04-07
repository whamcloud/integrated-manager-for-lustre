use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::fmt::Write;
use std::iter::Iterator;
use std::sync::Arc;

pub trait Deps {
    fn id(&self) -> u32;
    fn deps(&self) -> Vec<u32>;
    fn description(&self) -> String;
}

impl<T: Deps> Deps for Arc<T> {
    fn id(&self) -> u32 {
        (**self).id()
    }
    fn deps(&self) -> Vec<u32> {
        (**self).deps()
    }
    fn description(&self) -> String {
        (**self).description()
    }
}

#[derive(Debug, Clone)]
pub struct DependencyForest<T> {
    roots: Vec<Arc<T>>,
    deps: HashMap<u32, Vec<Arc<T>>>,
}

#[derive(Debug, Copy, Clone)]
pub struct DependencyForestRef<'a, T> {
    roots: &'a Vec<Arc<T>>,
    deps: &'a HashMap<u32, Vec<Arc<T>>>,
}

#[derive(Debug, Clone)]
pub struct Context {
    visited: HashSet<u32>,
    indent: usize,
}

fn build_direct_dag<T>(ts: &[T]) -> (Vec<u32>, Vec<(u32, Vec<u32>)>)
    where
        T: Deps + Clone + Debug,
{
    let mut roots: Vec<u32> = Vec::new();
    let mut rdag: Vec<(u32, Vec<u32>)> = Vec::with_capacity(ts.len());
    for t in ts {
        let x = t.id();
        let ys = t.deps();
        if !ys.is_empty() {
            // push the arcs `x -> y` for all `y \in xs` into the graph
            rdag.push((x, ys.to_vec()));
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
    (roots, rdag)
}

fn build_inverse_dag<T>(ts: &[T]) -> (Vec<u32>, Vec<(u32, Vec<u32>)>)
    where
        T: Deps + Clone + Debug,
{
    let mut roots: HashSet<u32> = ts.iter().map(|t| t.id()).collect();
    let mut rdag: Vec<(u32, Vec<u32>)> = Vec::with_capacity(ts.len());
    for t in ts {
        let y = t.id();
        let xs = t.deps();
        for x in xs {
            // push the arc `x -> y` into the graph
            if let Some((_, ref mut ys)) = rdag.iter_mut().find(|(y, ys)| *y == x) {
                ys.push(y);
            } else {
                rdag.push((x, vec![y]));
            }
            // any destination cannot be a root, so we need to remove any of these roots
            roots.remove(&y);
        }
    }
    let roots = roots.into_iter().collect();
    (roots, rdag)
}

fn write_tree<T: Deps>(tree: &DependencyForestRef<T>) -> String {
    fn write_subtree<T: Deps>(tree: &DependencyForestRef<T>, ctx: &mut Context) -> String {
        let mut res = String::new();
        for r in tree.roots {
            if let Some(deps) = tree.deps.get(&r.id()) {
                for d in deps {
                    res.write_str(&write_node(tree, Arc::clone(d), ctx));
                }
            }
        }
        res
    }
    fn write_node<T: Deps>(tree: &DependencyForestRef<T>, node: Arc<T>, ctx: &mut Context) -> String {
        let mut res = String::new();
        let is_new = ctx.visited.insert(node.id());
        let ellipsis = if is_new { "" } else { "..." };
        let indent = "  ".repeat(ctx.indent);
        res.write_str(&format!(
            "{}{}: {}{}\n",
            indent,
            node.id(),
            node.description(),
            ellipsis
        ));
        if is_new {
            ctx.indent += 1;
            let sub_tree = DependencyForestRef {
                deps: &tree.deps,
                roots: &vec![node.clone()],
            };
            res.write_str(&write_subtree(&sub_tree, ctx));
            ctx.indent -= 1;
        }
        res
    }
    let mut ctx = Context {
        visited: HashSet::new(),
        indent: 0,
    };
    let mut res = String::new();
    for r in tree.roots {
        res.write_str(&write_node(tree, Arc::clone(r), &mut ctx));
    }
    res
}

fn build_forest<T>(objs: &[T], int_roots: &[u32], int_deps: &[(u32, Vec<u32>)]) -> DependencyForest<T>
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

fn convert_ids_to_arcs<T>(objs: &[T], ids: &[u32]) -> Vec<Arc<T>>
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
        fn description(&self) -> String {
            self.description.clone()
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
        let (roots, deps) = build_direct_dag(&x_list);
        let forest = build_forest(&x_list, &roots, &deps);
        let forest_ref = DependencyForestRef {
            roots: &forest.roots,
            deps: &forest.deps,
        };
        let result = write_tree(&forest_ref);
        assert_eq!(result, TREE_DIRECT);

        let (roots, deps) = build_inverse_dag(&x_list);
        let forest = build_forest(&x_list, &roots, &deps);
        let forest_ref = DependencyForestRef {
            roots: &forest.roots,
            deps: &forest.deps,
        };
        let result = write_tree(&forest_ref);
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
