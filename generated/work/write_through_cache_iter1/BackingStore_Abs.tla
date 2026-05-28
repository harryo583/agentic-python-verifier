---- MODULE BackingStore_Abs ----
EXTENDS Naturals

CONSTANTS Keys, Vals, Missing

VARIABLES store

vars == <<store>>

Init == store = [k \in Keys |-> Missing]

StoreWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ store' = [store EXCEPT ![k] = v]

StoreRead(k) ==
  /\ k \in Keys
  /\ UNCHANGED store

Next ==
  \/ \E k \in Keys, v \in Vals : StoreWrite(k, v)
  \/ \E k \in Keys : StoreRead(k)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ DOMAIN store = Keys
  /\ \A k \in Keys : store[k] \in (Vals \cup {Missing})

Property == Inv
====
