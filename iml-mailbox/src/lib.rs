// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bytes::buf::FromBuf;
use futures::Stream;
use warp::{body::BodyStream, Filter};

pub trait LineStream: Stream<Item = String, Error = warp::Rejection> {}
impl<T: Stream<Item = String, Error = warp::Rejection>> LineStream for T {}

fn streamer(s: BodyStream) -> impl LineStream {
    let s = s.map(|c| Vec::from_buf(c)).map_err(warp::reject::custom);

    stream_lines::Lines::new(s, |xs| String::from_utf8(xs).map_err(warp::reject::custom))
}

pub fn line_stream() -> impl Filter<Extract = (impl LineStream,), Error = warp::Rejection> + Copy {
    warp::body::stream().map(streamer)
}

#[cfg(test)]
mod tests {
    use super::*;
    use futures::Async;

    #[test]
    fn test_line_stream() {
        let mut stream = warp::test::request()
            .body("foo\nbar\nbaz")
            .filter(&line_stream())
            .unwrap();

        assert_eq!(stream.poll().unwrap(), Async::Ready(Some("foo".into())));
        assert_eq!(stream.poll().unwrap(), Async::Ready(Some("bar".into())));
        assert_eq!(stream.poll().unwrap(), Async::Ready(Some("baz".into())));
        assert_eq!(stream.poll().unwrap(), Async::Ready(None));
    }
}
