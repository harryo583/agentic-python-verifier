---- MODULE Cache_Abs ----
EXTENDS Integers, FiniteSets

CONSTANTS Keys, Values, Missing

VARIABLES cache

vars == << cache >>

Init == cache = [k \in Keys |-> Missing]

Put(k, v) ==
  /\ k \in Keys
  /\ v \in Values
  /\ cache' = [cache EXCEPT ![k] = v]

Evict(k) ==
  /\ k \in Keys
  /\ cache' = [cache EXCEPT ![k] = Missing]

Noop == UNCHANGED cache

Next ==
  \/ Noop
  \/ \E k \in Keys, v \in Values : Put(k, v)
  \/ \E k \in Keys : Evict(k)

Spec == Init /\ [][Next]_vars

Inv == cache \in [Keys -> Values \cup {Missing}]

Property == Inv

====
