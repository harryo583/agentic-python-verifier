---- MODULE Cache_Impl ----
EXTENDS Naturals, TLC

CONSTANTS Keys, Vals, Missing

(* --algorithm Cache
variables
  cache = [k \in Keys |-> Missing];

begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          cache[k] := v;
        end with;
      or
        with k \in Keys do
          cache[k] := Missing;
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "9313f44f" /\ chksum(tla) = "ef21c57")
VARIABLE cache

vars == << cache >>

Init == (* Global variables *)
        /\ cache = [k \in Keys |-> Missing]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  cache' = [cache EXCEPT ![k] = v]
        \/ /\ \E k \in Keys:
                cache' = [cache EXCEPT ![k] = Missing]
        \/ /\ TRUE
           /\ cache' = cache

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

ValidCache(c) == \A k \in Keys : c[k] \in (Vals \cup {Missing})

Inv == ValidCache(cache)

Property == ValidCache(cache)
====
