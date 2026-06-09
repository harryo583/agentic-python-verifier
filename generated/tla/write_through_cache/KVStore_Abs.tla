---- MODULE KVStore_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Keys, Values, Missing

VARIABLES store

vars == << store >>

StoreBounded == \E S \in SUBSET Keys : store \in [S -> Values]

Init == store = [k \in {} |-> 0]

Put(k, v) == store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]

Get(k) == IF k \in DOMAIN store THEN store[k] ELSE Missing

Next == \E k \in Keys, v \in Values : Put(k, v)

Spec == Init /\ [][Next]_vars

Inv == StoreBounded

Property == StoreBounded

====
