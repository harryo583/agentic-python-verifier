---- MODULE Store_Abs ----
EXTENDS Naturals, FiniteSets
CONSTANTS Keys, Vals, NoVal
VARIABLES store
vars == << store >>

EmptyFn == [x \in {} |-> 0]

IsPartialFn(f, Dom, Rng) == \E K \in SUBSET Dom : f \in [K -> Rng]

Init == store = EmptyFn
WriteStore(k, v) == store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]
ReadStore == UNCHANGED store
Next == ReadStore \/ (\E k \in Keys, v \in Vals : WriteStore(k, v))
Spec == Init /\ [][Next]_vars

Inv == IsPartialFn(store, Keys, Vals)
Property == Inv
====
