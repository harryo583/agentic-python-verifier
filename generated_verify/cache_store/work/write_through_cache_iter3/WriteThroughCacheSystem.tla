---- MODULE WriteThroughCacheSystem ----
EXTENDS Integers, FiniteSets, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache, lastOp, lastKey, lastVal, lastReadResult

vars == << store, cache, lastOp, lastKey, lastVal, lastReadResult >>

Domain == Vals \cup {Missing}

CacheAgreesWithStore ==
  \A k \in Keys : (cache[k] # Missing) => (cache[k] = store[k])

Ops == {"None", "Read", "Write", "ReadAfterWrite"}

ReadAfterWrite ==
  (lastOp = "ReadAfterWrite") => (lastReadResult = lastVal)

Init ==
  /\ store = [k \in Keys |-> Missing]
  /\ cache = [k \in Keys |-> Missing]
  /\ lastOp = "None"
  /\ lastKey = CHOOSE k \in Keys : TRUE
  /\ lastVal = CHOOSE v \in Vals : TRUE
  /\ lastReadResult = Missing

Write(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ store' = [store EXCEPT ![k] = v]
  /\ cache' = [cache EXCEPT ![k] = v]
  /\ lastOp' = "Write"
  /\ lastKey' = k
  /\ lastVal' = v
  /\ lastReadResult' = Missing

ReadHit(k) ==
  /\ k \in Keys
  /\ cache[k] # Missing
  /\ lastReadResult' = cache[k]
  /\ lastOp' = IF lastOp = "Write" /\ lastKey = k THEN "ReadAfterWrite" ELSE "Read"
  /\ lastKey' = k
  /\ lastVal' = cache[k]
  /\ UNCHANGED << store, cache >>

ReadMiss(k) ==
  /\ k \in Keys
  /\ cache[k] = Missing
  /\ store[k] # Missing
  /\ lastReadResult' = store[k]
  /\ cache' = [cache EXCEPT ![k] = store[k]]
  /\ lastOp' = IF lastOp = "Write" /\ lastKey = k THEN "ReadAfterWrite" ELSE "Read"
  /\ lastKey' = k
  /\ lastVal' = store[k]
  /\ UNCHANGED store

Next ==
  \/ \E k \in Keys, v \in Vals : Write(k, v)
  \/ \E k \in Keys : ReadHit(k)
  \/ \E k \in Keys : ReadMiss(k)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ store \in [Keys -> Domain]
  /\ cache \in [Keys -> Domain]
  /\ lastOp \in Ops
  /\ lastKey \in Keys
  /\ lastVal \in Vals
  /\ lastReadResult \in Domain
  /\ CacheAgreesWithStore
  /\ ReadAfterWrite

Property ==
  /\ CacheAgreesWithStore
  /\ ReadAfterWrite
====
