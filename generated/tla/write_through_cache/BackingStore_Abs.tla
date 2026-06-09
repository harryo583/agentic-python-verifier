---- MODULE BackingStore_Abs ----
EXTENDS Naturals, FiniteSets
CONSTANTS Keys, Values
VARIABLES store

IsEntry(e) == e \in SUBSET Values /\ Cardinality(e) <= 1

TypeOK == /\ store \in [Keys -> SUBSET Values]
          /\ \A k \in Keys : IsEntry(store[k])

Init == store = [k \in Keys |-> {}]

StorePut(k, v) == /\ k \in Keys
                  /\ v \in Values
                  /\ store' = [store EXCEPT ![k] = {v}]

StoreNoop == store' = store

Next == \/ \E k \in Keys, v \in Values : StorePut(k, v)
        \/ StoreNoop

vars == << store >>
Spec == Init /\ [][Next]_vars

Inv == TypeOK
Property == TypeOK
====
