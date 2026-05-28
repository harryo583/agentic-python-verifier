---- MODULE BackingStore_Abs ----
EXTENDS Naturals

CONSTANTS Keys, Vals

VARIABLES storePresent, storeVal

vars == <<storePresent, storeVal>>

Zero == CHOOSE v \in Vals : \A w \in Vals : v <= w

Init ==
  /\ storePresent = [k \in Keys |-> FALSE]
  /\ storeVal = [k \in Keys |-> Zero]

StoreWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ storePresent' = [storePresent EXCEPT ![k] = TRUE]
  /\ storeVal' = [storeVal EXCEPT ![k] = v]

StoreRead(k) ==
  /\ k \in Keys
  /\ UNCHANGED <<storePresent, storeVal>>

Next ==
  \/ \E k \in Keys, v \in Vals : StoreWrite(k, v)
  \/ \E k \in Keys : StoreRead(k)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ storePresent \in [Keys -> BOOLEAN]
  /\ storeVal \in [Keys -> Vals]

Property == Inv
====
