---- MODULE BackingStore_Impl ----
EXTENDS Naturals, Sequences, FiniteSets
CONSTANTS Keys, Values

(* --algorithm BackingStore
variables store = [k \in Keys |-> {}];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Values do
          store := [store EXCEPT ![k] = {v}];
        end with;
      or
        skip;
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "abb19729" /\ chksum(tla) = "cc0c9a09")
VARIABLES store, pc

vars == << store, pc >>

Init == (* Global variables *)
        /\ store = [k \in Keys |-> {}]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ \E k \in Keys:
                   \E v \in Values:
                     store' = [store EXCEPT ![k] = {v}]
           \/ /\ TRUE
              /\ store' = store
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

IsEntry(e) == e \in SUBSET Values /\ Cardinality(e) <= 1

TypeOK == /\ store \in [Keys -> SUBSET Values]
          /\ \A k \in Keys : IsEntry(store[k])

Inv == /\ TypeOK
       /\ pc \in {"Loop", "Finish", "Done"}

Property == TypeOK
====
