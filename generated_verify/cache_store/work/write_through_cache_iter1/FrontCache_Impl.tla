---- MODULE FrontCache_Impl ----
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Keys, Vals, Missing

(* --algorithm FrontCache
variables
  cache = [k \in {} |-> 0];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          cache := [x \in (DOMAIN cache) \cup {k} |-> IF x = k THEN v ELSE cache[x]];
        end with;
      or
        with k \in Keys do
          cache := [x \in (DOMAIN cache) \ {k} |-> cache[x]];
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "2bffb46f" /\ chksum(tla) = "a1947aab")
VARIABLE cache

vars == << cache >>

Init == (* Global variables *)
        /\ cache = [k \in {} |-> 0]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  cache' = [x \in (DOMAIN cache) \cup {k} |-> IF x = k THEN v ELSE cache[x]]
        \/ /\ \E k \in Keys:
                cache' = [x \in (DOMAIN cache) \ {k} |-> cache[x]]
        \/ /\ TRUE
           /\ cache' = cache

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

TypeOK ==
  /\ DOMAIN cache \subseteq Keys
  /\ \A k \in DOMAIN cache : cache[k] \in Vals

Inv == TypeOK
Property == TypeOK

====
