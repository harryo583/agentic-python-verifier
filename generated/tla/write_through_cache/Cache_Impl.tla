---- MODULE Cache_Impl ----
EXTENDS Naturals, TLC, FiniteSets
CONSTANTS Keys, Vals, NoVal

EmptyFn == [x \in {} |-> 0]
IsPartialFn(f, Dom, Rng) == \E K \in SUBSET Dom : f \in [K -> Rng]

(* --algorithm Cache
variables cache = [x \in {} |-> 0];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          cache := [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN v ELSE cache[j]];
        end with;
      or
        with k \in Keys do
          cache := [j \in (DOMAIN cache) \ {k} |-> cache[j]];
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "3c2787c4" /\ chksum(tla) = "7d11e476")
VARIABLE cache

vars == << cache >>

Init == (* Global variables *)
        /\ cache = [x \in {} |-> 0]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN v ELSE cache[j]]
        \/ /\ \E k \in Keys:
                cache' = [j \in (DOMAIN cache) \ {k} |-> cache[j]]
        \/ /\ TRUE
           /\ cache' = cache

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv == IsPartialFn(cache, Keys, Vals)

Property == IsPartialFn(cache, Keys, Vals)
====
