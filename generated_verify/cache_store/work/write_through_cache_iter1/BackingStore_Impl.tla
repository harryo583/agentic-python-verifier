---- MODULE BackingStore_Impl ----
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Keys, Vals, Missing

(* --algorithm BackingStore
variables
  store = [k \in {} |-> 0];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          store := [x \in (DOMAIN store) \cup {k} |-> IF x = k THEN v ELSE store[x]];
        end with;
      or
        skip;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "505938f8" /\ chksum(tla) = "f25622f1")
VARIABLE store

vars == << store >>

Init == (* Global variables *)
        /\ store = [k \in {} |-> 0]

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  store' = [x \in (DOMAIN store) \cup {k} |-> IF x = k THEN v ELSE store[x]]
        \/ /\ TRUE
           /\ store' = store

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

TypeOK ==
  /\ DOMAIN store \subseteq Keys
  /\ \A k \in DOMAIN store : store[k] \in Vals

Inv == TypeOK
Property == TypeOK

====
