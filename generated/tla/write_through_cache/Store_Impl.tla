---- MODULE Store_Impl ----
EXTENDS Integers, FiniteSets, Sequences, TLC

CONSTANTS Keys, Values, Missing

(* --algorithm Store
variables store = [k \in Keys |-> Missing];
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Values do
          store := [store EXCEPT ![k] = v];
        end with;
      or
        skip;
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "44c1c1ba" /\ chksum(tla) = "b8925f26")
VARIABLES store, pc

vars == << store, pc >>

Init == (* Global variables *)
        /\ store = [k \in Keys |-> Missing]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ \E k \in Keys:
                   \E v \in Values:
                     store' = [store EXCEPT ![k] = v]
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

Inv ==
  /\ store \in [Keys -> Values \cup {Missing}]
  /\ pc \in {"Loop", "Finish", "Done"}

Property == store \in [Keys -> Values \cup {Missing}]

====
