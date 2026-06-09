---- MODULE Cache_Abs ----
EXTENDS Naturals, FiniteSets
CONSTANTS Keys, Vals, NoVal
VARIABLES cache
vars == << cache >>

EmptyFn == [x \in {} |-> 0]
IsPartialFn(f, Dom, Rng) == \E K \in SUBSET Dom : f \in [K -> Rng]

Init == cache = EmptyFn
Fill(k, v) == cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN v ELSE cache[j]]
Update(k, v) == cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN v ELSE cache[j]]
Invalidate(k) == cache' = [j \in (DOMAIN cache) \ {k} |-> cache[j]]
Lookup == UNCHANGED cache
Next == Lookup
     \/ (\E k \in Keys, v \in Vals : Fill(k, v))
     \/ (\E k \in Keys, v \in Vals : Update(k, v))
     \/ (\E k \in Keys : Invalidate(k))
Spec == Init /\ [][Next]_vars

Inv == IsPartialFn(cache, Keys, Vals)
Property == Inv
====
