pub trait Keyed {
    type Key: Eq;
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

pub fn calculate_diff<T: Keyed + Eq>(left_xs: &[T], right_xs: &[T]) -> Vec<AlignmentOp> {
    // Ad-hoc version of sequence alignment, left biased.
    // More solid approach is the https://en.wikipedia.org/wiki/Hirschberg%27s_algorithm
    let m = left_xs.len();
    let n = right_xs.len();
    let mut i = 0; // i ∈ (0..m)
    let mut j = 0; // j ∈ (0..n)
    let mut result = Vec::with_capacity(m + n);
    loop {
        if i >= m && j >= n {
            // both arrays exhausted
            return result;
        } else if j >= n {
            // right array exhausted
            (i..m).for_each(|i| result.push(AlignmentOp::Insert(Side::Right, i, j)));
            return result;
        } else if i >= m {
            // left array exhausted
            (j..n).for_each(|j| result.push(AlignmentOp::Insert(Side::Left, i, j)));
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
            } else if let Some((_, _)) = right_xs[0..j]
                .iter()
                .enumerate()
                .rfind(|(_, r)| r.key() == l.key())
            {
                result.push(AlignmentOp::Delete(Side::Left, i));
                i += 1;
            } else {
                result.push(AlignmentOp::Insert(Side::Right, i, j));
                i += 1;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
    use std::collections::HashMap;
    use std::sync::Arc;
    use std::thread;

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

    #[test]
    fn test_calculate_diff() {
        let mut xs = vec![t(1), t(2), t(3), t(10), t(11)];
        let mut ys = vec![t(1), t(3), t(2), t(10), t(11), t(12), t(20), t(30)];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
    }

    #[test]
    fn test_empty() {
        let mut xs: Vec<T> = vec![];
        let mut ys: Vec<T> = vec![];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
    }

    #[test]
    fn test_empty_left() {
        let mut xs = vec![];
        let mut ys = vec![t(1), t(2), t(3), t(10), t(11)];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
    }

    #[test]
    fn test_empty_right() {
        let mut xs = vec![t(1), t(2), t(3), t(4), t(5)];
        let mut ys = vec![];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
    }

    #[test]
    fn test_grow_left() {
        let mut xs = vec![t(1), t(2), t(3)];
        let mut ys = vec![t(10), t(1), t(11), t(20), t(2), t(22), t(30), t(3), t(33)];
        let exp = ys.clone();
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
    }

    #[test]
    fn test_grow_right() {
        let mut xs = vec![t(10), t(1), t(11), t(20), t(2), t(22), t(30), t(3), t(34)];
        let mut ys = vec![t(1), t(2), t(3)];
        let exp = xs.clone();
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
    }

    #[test]
    fn test_repeated_items() {
        let mut xs = vec![t(1), t(2), t(1), t(2)];
        let mut ys = vec![t(1), t(2), t(3), t(1), t(2), t(3)];
        let exp = ys.clone();
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
    }

    #[test]
    fn test_replace() {
        let mut xs = vec![t(1), t(2), t(3), t(4)];
        let mut ys = vec![t(0), t(2), t(3), t(5)];
        ys[1].msg = "modified".to_string();
        ys[2].msg = "modified".to_string();
        let exp = vec![t(1), t(0), tm(2, "modified"), tm(3, "modified"), t(4), t(5)];
        let diff = calculate_diff(&xs, &ys);
        apply_diff(&mut xs, &mut ys, &diff);
        assert_eq!(xs, ys);
        assert_eq!(xs, exp);
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

    fn apply_diff<T: Clone>(xs: &mut Vec<T>, ys: &mut Vec<T>, diff: &[AlignmentOp]) {
        let mut di = 0;
        let mut dj = 0;
        for d in diff {
            match d {
                AlignmentOp::Insert(Side::Left, i, j) => {
                    xs.insert(i + di, ys[j + dj].clone());
                    di += 1;
                }
                AlignmentOp::Insert(Side::Right, i, j) => {
                    ys.insert(j + dj, xs[i + di].clone());
                    dj += 1;
                }
                AlignmentOp::Replace(Side::Left, i, j) => {
                    xs[i + di] = ys[j + dj].clone();
                }
                AlignmentOp::Replace(Side::Right, i, j) => {
                    ys[j + dj] = xs[i + di].clone();
                }
                AlignmentOp::Delete(Side::Left, i) => {
                    xs.remove(i + di);
                    di -= 1;
                }
                AlignmentOp::Delete(Side::Right, j) => {
                    ys.remove(j + dj);
                    dj -= 1;
                }
            }
        }
    }
}