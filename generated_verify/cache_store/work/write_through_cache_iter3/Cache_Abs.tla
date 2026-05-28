---- MODULE Cache_Abs ----
EXTENDS Integers, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES cache

vars == << cache >>

Domain == Vals \cup {Missing}

Init == cache = [k \in Keys |-> Missing]

CacheSet(k, v) ==
  /\ k \in Keys
  /\ v \in Domain
  /\ cache' = [cache EXCEPT ![k] = v]

Stutter == UNCHANGED cache

Next ==
  \/ \E k \in Keys, v \in Domain : CacheSet(k, v)
  \/ Stutter

Spec == Init /\ [][Next]_vars

Inv == cache \in [Keys -> Domain]

Property == cache \in [Keys -> Domain]
====
