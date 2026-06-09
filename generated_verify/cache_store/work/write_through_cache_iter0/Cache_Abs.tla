---- MODULE Cache_Abs ----
EXTENDS Naturals, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES cache

vars == << cache >>

ValidCache(c) == \A k \in Keys : c[k] \in (Vals \cup {Missing})

Init == cache = [k \in Keys |-> Missing]

CacheUpdate(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ cache' = [cache EXCEPT ![k] = v]

CachePopulate(k, v) ==
  /\ k \in Keys
  /\ v \in (Vals \cup {Missing})
  /\ cache' = [cache EXCEPT ![k] = v]

CacheLookupStep ==
  /\ UNCHANGED cache

Next ==
  \/ \E k \in Keys, v \in Vals : CacheUpdate(k, v)
  \/ \E k \in Keys, v \in (Vals \cup {Missing}) : CachePopulate(k, v)
  \/ CacheLookupStep

Spec == Init /\ [][Next]_vars

Inv == ValidCache(cache)

Property == ValidCache(cache)
====
