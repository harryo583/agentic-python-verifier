---- MODULE KVStore_Impl ----
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Keys, Values, Missing

(* --algorithm KVStore
variables store = [k \in {} |-> 0];
begin
  Loop:
    while TRUE do
      with k \in Keys, v \in Values do
        store := [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]];
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "88316037" /\ chksum(tla) = "fbdc9d6d")
VARIABLES store, pc

vars == << store, pc >>

Init == (* Global variables *)
        /\ store = [k \in {} |-> 0]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E k \in Keys:
             \E v \in Values:
               store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ store' = store

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

StoreBounded == \E S \in SUBSET Keys : store \in [S -> Values]

Inv == StoreBounded /\ pc \in {"Loop", "Finish", "Done"}

Property == StoreBounded

====
