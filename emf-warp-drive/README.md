# EMF Warp Drive

## Overview

The `emf-warp-drive` crate is responsible for providing a [Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) endpoint. It is accessible at `/messaging` on a running manager instance.

The endpoint provides near-realtime data to consumers based off of changes to the EMF database via [LISTEN / NOTIFY](https://www.postgresql.org/docs/9.6/sql-notify.html).

Internally, the crate uses [warp](https://github.com/seanmonstar/warp) to handle SSE connections.
