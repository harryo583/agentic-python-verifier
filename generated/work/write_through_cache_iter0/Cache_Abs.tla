---- MODULE Cache_Abs ----
EXTENDS Naturals

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache, lastRead

vars == <<store, cache, lastRead>>

Init ==
  /\ store = [k \in Keys |-> Missing]
  /\ cache = [k \in Keys |-> Missing]
  /\ lastRead = Missing

CacheWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ cache' = [cache EXCEPT ![k] = v]
  /\ store' = [store EXCEPT ![k] = v]
  /\ lastRead' = Missing

CacheRead(k) ==
  /\ k \in Keys
  /\ IF cache[k] # Missing
     THEN /\ lastRead' = [key |-> k, val |-> cache[k]]
          /\ UNCHANGED <<store, cache>>
     ELSE /\ cache' = [cache EXCEPT ![k] = store[k]]
          /\ lastRead' = [key |-> k, val |-> store[k]]
          /\ UNCHANGED store

Invalidate(k) ==
  /\ k \in Keys
  /\ cache' = [cache EXCEPT ![k] = Missing]
  /\ UNCHANGED <<store, lastRead>>

Next ==
  \/ \E k \in Keys, v \in Vals : CacheWrite(k, v)
  \/ \E k \in Keys : CacheRead(k)
  \/ \E k \in Keys : Invalidate(k)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ \A k \in Keys : (cache[k] # Missing) => (cache[k] = store[k])
  /\ (lastRead # Missing) => (lastRead.val = store[lastRead.key])

Property == Inv
====
