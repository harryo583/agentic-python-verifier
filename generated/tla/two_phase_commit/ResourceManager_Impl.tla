---- MODULE ResourceManager_Impl ----
EXTENDS Naturals, Sequences, FiniteSets, TLC
CONSTANTS RMs

States == {"working", "prepared", "committed", "aborted"}
PCs == {"Loop", "Finish", "Done"}

(* --algorithm ResourceManager
variables rmState = [r \in RMs |-> "working"];
begin
  Loop:
    while TRUE do
      with r \in RMs do
        either
          await rmState[r] = "working";
          rmState[r] := "prepared";
        or
          await rmState[r] = "working";
          rmState[r] := "aborted";
        or
          await rmState[r] = "prepared";
          rmState[r] := "committed";
        or
          await rmState[r] \in {"working", "prepared"};
          rmState[r] := "aborted";
        end either;
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "825e84af" /\ chksum(tla) = "893ed23b")
VARIABLES rmState, pc

vars == << rmState, pc >>

Init == (* Global variables *)
        /\ rmState = [r \in RMs |-> "working"]
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E r \in RMs:
             \/ /\ rmState[r] = "working"
                /\ rmState' = [rmState EXCEPT ![r] = "prepared"]
             \/ /\ rmState[r] = "working"
                /\ rmState' = [rmState EXCEPT ![r] = "aborted"]
             \/ /\ rmState[r] = "prepared"
                /\ rmState' = [rmState EXCEPT ![r] = "committed"]
             \/ /\ rmState[r] \in {"working", "prepared"}
                /\ rmState' = [rmState EXCEPT ![r] = "aborted"]
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED rmState

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ pc \in PCs
  /\ rmState \in [RMs -> States]

Property == Inv
====
