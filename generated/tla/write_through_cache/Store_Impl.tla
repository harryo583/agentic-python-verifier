---- MODULE Store_Impl ----
EXTENDS Naturals, TLC, FiniteSets
CONSTANTS Keys, Vals, NoVal

EmptyFn == [x \in {} |-> 0]
IsPartialFn(f, Dom, Rng) == \E K \in SUBSET Dom : f \in [K -> Rng]

(* --algorithm Store
variables store = [x \in {} |-> 0];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          store := [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]];
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "a4082779" /\ chksum(tla) = "597c849a")
VARIABLE store

vars == << store >>

Init == (* Global variables *)
        /\ store = [x \in {} |-> 0]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]
        \/ /\ TRUE
           /\ store' = store

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv == IsPartialFn(store, Keys, Vals)

Property == IsPartialFn(store, Keys, Vals)
====
