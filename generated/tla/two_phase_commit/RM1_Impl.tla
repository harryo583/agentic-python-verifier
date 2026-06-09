---- MODULE RM1_Impl ----
EXTENDS Naturals, TLC

CONSTANTS States

(* --algorithm RM1
variables rm1State = "working";
begin
  RMLoop:
    while TRUE do
      either
        await rm1State = "working";
        rm1State := "prepared";
      or
        await rm1State = "prepared";
        rm1State := "committed";
      or
        await rm1State \in {"working","prepared"};
        rm1State := "aborted";
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "4a5bb363" /\ chksum(tla) = "1ee93c6b")
VARIABLES rm1State, pc

vars == << rm1State, pc >>

Init == (* Global variables *)
        /\ rm1State = "working"
        /\ pc = "RMLoop"

RMLoop == /\ pc = "RMLoop"
          /\ \/ /\ rm1State = "working"
                /\ rm1State' = "prepared"
             \/ /\ rm1State = "prepared"
                /\ rm1State' = "committed"
             \/ /\ rm1State \in {"working","prepared"}
                /\ rm1State' = "aborted"
          /\ pc' = "RMLoop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED rm1State

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == RMLoop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ rm1State \in States
  /\ pc \in {"RMLoop", "Finish", "Done"}

Property == rm1State \in States
====
