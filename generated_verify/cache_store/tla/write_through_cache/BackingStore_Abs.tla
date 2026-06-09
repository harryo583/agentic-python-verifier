---- MODULE BackingStore_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Keys, Vals, Missing

VARIABLES store

vars == <<store>>

TypeOK ==
  \E D \in SUBSET Keys : store \in [D -> Vals]

Init == store = [k \in {} |-> 0]

StoreWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ store' = [x \in (DOMAIN store) \cup {k} |-> IF x = k THEN v ELSE store[x]]

StoreReadStep ==
  UNCHANGED store

Next ==
  \/ \E k \in Keys, v \in Vals : StoreWrite(k, v)
  \/ StoreReadStep

Spec == Init /\ [][Next]_vars

Inv == TypeOK
Property == TypeOK

====
