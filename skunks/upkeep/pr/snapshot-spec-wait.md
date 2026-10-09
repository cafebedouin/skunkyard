# SnapshotFallbackSpec: allow 20 s for the first save, as the other actor specs do

## What

One line of test configuration: `SnapshotFallbackSpec`'s actor system gets
`akka.test.single-expect-default = 20s`, the allowance the other actor specs in `test/state` already use,
with a comment saying why.

## Why

The actor under test opens a LevelDB in a fresh temp directory on its first save. On a loaded host (the
whole suite running, other JVMs on the box) that open can take longer than TestKit's default 3-second
expectation, and the spec times out before the actor answers. Eight of its cases then fail together with no
change to the code under test: "keep a generation whose header could not be read", "restore a generation the
node confirms", "fall past a disproved generation to an older confirmed one", "report no canonical snapshot
only when every generation was checked", "terminate a restore request on restart and ignore its stale
validation completion", "refuse a byte-valid generation whose fields contradict each other", "refuse a
generation whose retained cursors do not reach its own", and "refuse retained cursor identity from a
same-height fork". Run alone, the spec passes.

## Testing

`sbt "testOnly state.persistence.SnapshotFallbackSpec"` and the full suite on Java 17, under load, with the
eight cases passing. The spec's assertions are unchanged.
