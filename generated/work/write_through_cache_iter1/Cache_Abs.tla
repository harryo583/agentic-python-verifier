---- MODULE Cache_Abs ----
EXTENDS Naturals

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache, lastReadValid, lastReadKey, lastReadVal

vars == <<store, cache, lastReadValid, lastReadKey, lastReadVal>>

Init ==
  /\ store = [k \in Keys |-> Missing]
  /\ cache = [k \in Keys |-> Missing]
  /\ lastReadValid = FALSE
  /\ lastReadKey \in Keys
  /\ lastReadVal = Missing

CacheWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ cache' = [cache EXCEPT ![k] = v]
  /\ store' = [store EXCEPT ![k] = v]
  /\ lastReadValid' = FALSE
  /\ lastReadKey' = lastReadKey
  /\ lastReadVal' = Missing

CacheRead(k) ==
  /\ k \in Keys
  /\ IF cache[k] # Missing
     THEN /\ lastReadValid' = TRUE
          /\ lastReadKey' = k
          /\ lastReadVal' = cache[k]
          /\ UNCHANGED <<store, cache>>
     ELSE /\ cache' = [cache EXCEPT ![k] = store[k]]
          /\ lastReadValid' = TRUE
          /\ lastReadKey' = k
          /\ lastReadVal' = store[k]
          /\ UNCHANGED store

Invalidate(k) ==
  /\ k \in Keys
  /\ cache' = [cache EXCEPT ![k] = Missing]
  /\ UNCHANGED <<store, lastReadValid, lastReadKey, lastReadVal>>

Next ==
  \/ \E k \in Keys, v \in Vals : CacheWrite(k, v)
  \/ \E k \in Keys : CacheRead(k)
  \/ \E k \in Keys : Invalidate(k)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ \A k \in Keys : (cache[k] # Missing) => (cache[k] = store[k])
  /\ lastReadValid => (lastReadVal = store[lastReadKey])

Property == Inv
====
