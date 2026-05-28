---- MODULE Cache_Abs ----
EXTENDS Naturals, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES cache

vars == << cache >>

ValidCache(c) == \A k \in Keys : c[k] \in (Vals \cup {Missing})

Init == cache = [k \in Keys |-> Missing]

CacheSet(k, v) ==
  /\ k \in Keys
  /\ v \in (Vals \cup {Missing})
  /\ cache' = [cache EXCEPT ![k] = v]

Stutter == UNCHANGED cache

Next ==
  \/ \E k \in Keys : \E v \in (Vals \cup {Missing}) : CacheSet(k, v)
  \/ Stutter

Spec == Init /\ [][Next]_vars

Inv == ValidCache(cache)

Property == ValidCache(cache)
====
