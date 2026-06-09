---- MODULE BackingStore_Abs ----
EXTENDS Integers, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store

vars == << store >>

Domain == Vals \cup {Missing}

Init == store = [k \in Keys |-> Missing]

StoreWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ store' = [store EXCEPT ![k] = v]

Stutter == UNCHANGED store

Next ==
  \/ \E k \in Keys, v \in Vals : StoreWrite(k, v)
  \/ Stutter

Spec == Init /\ [][Next]_vars

Inv == store \in [Keys -> Domain]

Property == store \in [Keys -> Domain]
====
