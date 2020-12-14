pub trait Keyed {
    type Key: PartialEq;
    fn key(&self) -> Self::Key;
}

#[derive(Debug, Clone, Eq, PartialEq)]
pub enum Side {
    Left,
    Right,
}

#[derive(Debug, Clone, Eq, PartialEq)]
pub enum AlignmentOp {
    Insert(Side, usize, usize),
    Delete(Side, usize),
    Replace(Side, usize, usize),
}

pub fn calculate_diff<T: Keyed + PartialEq>(left_xs: &[T], right_xs: &[T]) -> Vec<AlignmentOp> {
    // Ad-hoc version of sequence alignment, left biased.
    // More solid approach is the https://en.wikipedia.org/wiki/Hirschberg%27s_algorithm
    let nl = left_xs.len();
    let nr = right_xs.len();
    let mut i = 0; // i ∈ (0..m)
    let mut j = 0; // j ∈ (0..n)
    let mut result = Vec::with_capacity(nl + nr);
    loop {
        if i >= nl && j >= nr {
            // both arrays exhausted
            return result;
        } else if j >= nr {
            // right array exhausted
            (i..nl).for_each(|i| result.push(AlignmentOp::Delete(Side::Left, i)));
            return result;
        } else if i >= nl {
            // left array exhausted
            (j..nr).for_each(|j| result.push(AlignmentOp::Insert(Side::Left, i, j)));
            return result;
        } else if left_xs[i] == right_xs[j] {
            // both elements are the same, skip
            i += 1;
            j += 1;
        } else if left_xs[i].key() == right_xs[j].key() {
            result.push(AlignmentOp::Replace(Side::Left, i, j));
            i += 1;
            j += 1;
        } else {
            let l = &left_xs[i];
            if let Some((j1, _)) = right_xs[j..]
                .iter()
                .enumerate()
                .find(|(_, r)| r.key() == l.key())
            {
                (0..j1).for_each(|ix| result.push(AlignmentOp::Insert(Side::Left, i, j + ix)));
                j += j1;
            } else {
                result.push(AlignmentOp::Delete(Side::Left, i));
                i += 1;
            }
        }
    }
}

pub fn apply_diff<T: Clone>(
    xs: &mut Vec<T>,
    ys: &mut Vec<T>,
    diff: &[AlignmentOp],
    mut on_create: impl FnMut(usize, usize, &T) -> (usize, T),
    mut on_update: impl FnMut(usize, usize, &T, &T) -> (usize, T),
    mut on_remove: impl FnMut(usize, &T) -> usize,
) {
    let mut di = 0i32;
    let mut dj = 0i32;
    for d in diff {
        match d {
            AlignmentOp::Insert(Side::Left, i, j) => {
                let i0 = (*i as i32 + di) as usize;
                let j0 = (*j as i32 + dj) as usize;
                // the most trivial implementation is `(i0, ys[j0].clone())`
                let (i, y) = on_create(i0, j0, &ys[j0]);
                xs.insert(i, y);
                di += 1;
            }
            AlignmentOp::Replace(Side::Left, i, j) => {
                let i0 = (*i as i32 + di) as usize;
                let j0 = (*j as i32 + dj) as usize;
                // the most trivial implementation is `(i0, ys[j0].clone())`
                let (i, y) = on_update(i0, j0, &xs[i0], &ys[j0]);
                xs[i] = y;
            }
            AlignmentOp::Delete(Side::Left, i) => {
                let i0 = (*i as i32 + di) as usize;
                // the most trivial implementation is `i0`
                let i = on_remove(i0, &xs[i0]);
                xs.remove(i);
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

#[cfg(test)]
mod tests {
    use super::AlignmentOp::*;
    use super::Side::*;
    use super::*;

    #[derive(Debug, Copy, Clone, PartialEq, Eq, Hash)]
    struct Id(i32);

    #[derive(Debug, Clone, PartialEq, Eq)]
    struct T {
        id: Id,
        msg: String,
    }

    impl Keyed for T {
        type Key = Id;

        fn key(&self) -> Self::Key {
            self.id
        }
    }

    fn on_create(i: usize, _j: usize, y: &T) -> (usize, T) {
        (i, y.clone())
    }

    fn on_update(i: usize, _j: usize, _x: &T, y: &T) -> (usize, T) {
        (i, y.clone())
    }

    fn on_remove(i: usize, _x: &T) -> usize {
        i
    }

    #[test]
    fn test_calculate_diff() {
        let mut xs = vec![t(1), t(2), t(3), t(10), t(11)];
        let mut ys = vec![t(1), t(3), t(2), t(10), t(11), t(12), t(20), t(30)];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        let exp_diff = vec![
            Insert(Left, 1, 1),
            Delete(Left, 2),
            Insert(Left, 5, 5),
            Insert(Left, 5, 6),
            Insert(Left, 5, 7),
        ];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_empty() {
        let mut xs: Vec<T> = vec![];
        let mut ys: Vec<T> = vec![];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        let exp_diff: Vec<AlignmentOp> = vec![];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_empty_left() {
        let mut xs = vec![];
        let mut ys = vec![t(1), t(2), t(3), t(10), t(11)];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        let exp_diff = vec![
            Insert(Left, 0, 0),
            Insert(Left, 0, 1),
            Insert(Left, 0, 2),
            Insert(Left, 0, 3),
            Insert(Left, 0, 4),
        ];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_empty_right() {
        let mut xs = vec![t(1), t(2), t(3), t(4), t(5)];
        let mut ys = vec![];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        let exp_diff = vec![
            Delete(Left, 0),
            Delete(Left, 1),
            Delete(Left, 2),
            Delete(Left, 3),
            Delete(Left, 4),
        ];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_grow_left() {
        let mut xs = vec![t(1), t(2), t(3)];
        let mut ys = vec![t(10), t(1), t(11), t(20), t(2), t(22), t(30), t(3), t(33)];
        let exp = ys.clone();
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
        let exp_diff = vec![
            Insert(Left, 0, 0),
            Insert(Left, 1, 2),
            Insert(Left, 1, 3),
            Insert(Left, 2, 5),
            Insert(Left, 2, 6),
            Insert(Left, 3, 8),
        ];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_grow_right() {
        let mut xs = vec![t(10), t(1), t(11), t(20), t(2), t(22), t(30), t(3), t(34)];
        let mut ys = vec![t(1), t(2), t(3)];
        let exp = ys.clone();
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
        let exp_diff = vec![
            Delete(Left, 0),
            Delete(Left, 2),
            Delete(Left, 3),
            Delete(Left, 5),
            Delete(Left, 6),
            Delete(Left, 8),
        ];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_repeated_items() {
        let mut xs = vec![t(1), t(2), t(1), t(2)];
        let mut ys = vec![t(1), t(2), t(3), t(1), t(2), t(3)];
        let exp = ys.clone();
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
        let exp_diff = vec![Insert(Left, 2, 2), Insert(Left, 4, 5)];
        assert_eq!(diff, exp_diff);
    }

    #[test]
    fn test_replace() {
        let mut xs = vec![t(1), t(2), t(3), t(4)];
        let mut ys = vec![t(0), t(2), t(3), t(5)];
        ys[1].msg = "modified".to_string();
        ys[2].msg = "modified".to_string();
        let exp = vec![t(0), tm(2, "modified"), tm(3, "modified"), t(5)];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff, on_create, on_update, on_remove);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
        let exp_diff = vec![
            Delete(Left, 0),
            Insert(Left, 1, 0),
            Replace(Left, 1, 1),
            Replace(Left, 2, 2),
            Delete(Left, 3),
            Insert(Left, 4, 3),
        ];
        assert_eq!(diff, exp_diff);
    }

    fn t(id: i32) -> T {
        T {
            id: Id(id),
            msg: format!("item {:?}", id),
        }
    }

    fn tm(id: i32, msg: &str) -> T {
        T {
            id: Id(id),
            msg: msg.to_string(),
        }
    }
}
