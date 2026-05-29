---- MODULE Store_Abs ----
EXTENDS Integers, FiniteSets

CONSTANTS Keys, Values, Missing

VARIABLES store

vars == << store >>

Init == store = [k \in Keys |-> Missing]

Write(k, v) ==
  /\ k \in Keys
  /\ v \in Values
  /\ store' = [store EXCEPT ![k] = v]

ReadNoop == UNCHANGED store

Next == ReadNoop \/ \E k \in Keys, v \in Values : Write(k, v)

Spec == Init /\ [][Next]_vars

Inv == store \in [Keys -> Values \cup {Missing}]

Property == Inv

====
