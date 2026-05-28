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
        with k \in Keys, v \in (Vals \cup {Missing}) do
          cache[k] := v;
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "18228edf" /\ chksum(tla) = "f96a28aa")
VARIABLE cache

vars == << cache >>

Init == (* Global variables *)
        /\ cache = [k \in Keys |-> Missing]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  cache' = [cache EXCEPT ![k] = v]
        \/ /\ \E k \in Keys:
                \E v \in (Vals \cup {Missing}):
                  cache' = [cache EXCEPT ![k] = v]
        \/ /\ TRUE
           /\ cache' = cache

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

ValidCache(c) == \A k \in Keys : c[k] \in (Vals \cup {Missing})

Inv ==
  /\ ValidCache(cache)
  /\ pc \in {"Loop"}

Property == ValidCache(cache)
====
